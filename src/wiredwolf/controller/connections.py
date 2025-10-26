import abc
from collections.abc import Callable
import logging
import select
import socket
import threading
from enum import Enum
from typing import Any
import pickle

from wiredwolf.controller import TIMEOUT
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.messages import BaseMessage

SELECT_TIMEOUT: float = 1.0  # Timeout for select calls in seconds

class ConnectionClosedError(Exception):
    """Exception raised when a connection is closed."""
    pass


class Serializer(abc.ABC):
    """Base class for serializing and deserializing objects"""

    @abc.abstractmethod
    def serialize(self, data: Any) -> bytes:
        """Serializes a given object into a byte stream

        Args:
            data (Any): the object to serialize

        Returns:
            bytes: the serialized byte stream
        """

    @abc.abstractmethod
    def deserialize(self, data: bytes) -> Any:
        """Deserializes a byte stream into an object

        Args:
            data (bytes): the byte stream to deserialize

        Returns:
            Any: the deserialized object
        """


class PickleSerializer(Serializer):
    """Serializer implementation using Python's pickle module"""

    def __init__(self):
        pass

    def serialize(self, data: Any) -> bytes:
        return pickle.dumps(data)

    def deserialize(self, data: bytes) -> Any:
        return pickle.loads(data)


class TCPMessageHandler:
    PREFIX_LEN: int = 4

    def __init__(self, serializer: Serializer):
        self._serializer = serializer

    def add_length_prefix(self, data: bytes) -> bytes:
        if len(data) < int("9" * self.PREFIX_LEN):
            # Ensure the data length is within the limit
            bytes_len = format(len(data), "0" + str(self.PREFIX_LEN) + "d").encode(
                "utf-8"
            )
            return bytes_len + data
        else:
            raise ValueError("Data too long")

    def send(self, endpoint: socket.socket, data: bytes) -> None:
        endpoint.sendall(self.add_length_prefix(data))

    def send_msg(self, endpoint: socket.socket, msg: str) -> None:
        data = msg.encode("utf-8")
        self.send(endpoint, data)

    def send_obj(self, endpoint: socket.socket, obj: Any) -> None:
        data = self._serializer.serialize(obj)
        self.send(endpoint, data)

    def receive(self, endpoint: socket.socket) -> bytes:
        data_len = endpoint.recv(self.PREFIX_LEN)
        if not data_len:
            raise ConnectionClosedError("Connection closed by the other side.")
        data_len = int(data_len.decode("utf-8").strip())
        return endpoint.recv(data_len)

    def receive_msg(self, endpoint: socket.socket) -> str:
        data = self.receive(endpoint)
        return data.decode("utf-8")

    def receive_obj(self, endpoint: socket.socket) -> Any:
        data = self.receive(endpoint)
        return self._serializer.deserialize(data)


class MessageHandlerFactory:
    @staticmethod
    def getDefaultSerializer() -> Serializer:
        return PickleSerializer()

    @staticmethod
    def getDefault() -> TCPMessageHandler:
        return TCPMessageHandler(PickleSerializer())


class ConnectionStatus(Enum):
    CONNECTING = 1
    CONNECTED = 2
    RECOVERING = 3


class ServerConnectionHandler(abc.ABC):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        self._message_handler: TCPMessageHandler = MessageHandlerFactory.getDefault()

    @abc.abstractmethod
    def send_obj(self, receiver: Peer, obj: Any) -> None:
        pass

    @abc.abstractmethod
    def receive_obj(self, sender: Peer) -> Any:
        pass

    @abc.abstractmethod
    def stop_new_connections(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass


class TCPServerConnectionHandler(ServerConnectionHandler):
    """ServerConnectionHandler implementation based on TCP connections"""

    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        on_new_peer: Callable[[Peer], None],
        on_new_message: Callable[[BaseMessage], None],
        bind_address: tuple[str, int] = ("", 0),
        server_socket: socket.socket | None = None,
    ):
        super().__init__()
        self._endpoints: dict[Peer, socket.socket] = {}
        self._status: dict[Peer, ConnectionStatus] = {}
        self._closed_new_conn: threading.Event = threading.Event()
        self._closed: threading.Event = threading.Event()
        self._endpoints_lock = threading.Lock()
        self._empty_endpoints_condition = threading.Condition(self._endpoints_lock)
        self._on_new_peer: Callable[[Peer], None] = on_new_peer
        self._on_new_message: Callable[[BaseMessage], None] = on_new_message
        self._new_conn_socket: socket.socket = (
            server_socket if server_socket else socket.create_server(bind_address)
        )
        # Starts the thread to handle new incoming connections
        self._new_conn_thread: threading.Thread = threading.Thread(
            target=self._handle_connections, name="TCPServerConnectionHandlerThread"
        )
        self._receiver_thread: threading.Thread = threading.Thread(
            target=self._handle_messages, name="TCPServerMessageReceiverThread"
        )

        self._new_conn_thread.start()
        self._receiver_thread.start()
        self._logger.info("Server listening on %s", self._new_conn_socket.getsockname())

    def send_obj(self, receiver: Peer, obj: Any) -> None:
        endpoint = self._endpoints.get(receiver)
        if endpoint:
            self._message_handler.send_obj(endpoint, obj)
        else:
            raise ValueError("No such peer connected.")

    def receive_obj(self, sender: Peer) -> Any:
        endpoint = self._endpoints.get(sender)
        if endpoint:
            return self._message_handler.receive_obj(endpoint)
        else:
            raise ValueError("No such peer connected.")

    def stop_new_connections(self):
        if not self._closed_new_conn.is_set():
            self._closed_new_conn.set()
            self._new_conn_socket.shutdown(socket.SHUT_RDWR)
            self._new_conn_thread.join()
            self._new_conn_socket.close()

    def get_receiver_socket(self) -> socket.socket:
        """Returns the socket that handles new connections for this handler

        Returns:
            socket.socket: The receiver socket
        """
        return self._new_conn_socket

    def _handle_connections(self):
        while not self._closed_new_conn.is_set():
            try:
                self._logger.debug("Waiting for new connections...")
                client_socket, client_address = self._new_conn_socket.accept()
                self._logger.info("Accepted connection from %s", client_address)
                client_socket.settimeout(TIMEOUT)
                try:
                    # First thing peer sends is their identification (serialized peer object)
                    # TODO: If this receive obj takes too long the system doesn't accept new connections, this should be made asynchronous
                    peer: Peer = self._message_handler.receive_obj(client_socket)
                    try:
                        with self._endpoints_lock:
                            # Add the endpoint
                            self._endpoints[peer] = client_socket
                            self._status[peer] = ConnectionStatus.CONNECTING
                            # Try to handle the new peer connection
                        self._on_new_peer(peer)
                        with self._endpoints_lock:
                            self._status[peer] = ConnectionStatus.CONNECTED
                            self._empty_endpoints_condition.notify_all()  # Wake up the receiver thread if it's waiting
                    except Exception as e:
                        # If handling the new peer fails, remove the endpoint
                        client_socket.close()
                        with self._endpoints_lock:
                            self._endpoints.pop(peer)
                        self._logger.error("Error handling new peer %s: %s", peer, e)
                except TimeoutError:
                    continue
            except Exception as e:
                if self._closed_new_conn.is_set():
                    self._logger.info("Server stopped accepting new connections")
                else:
                    self._logger.error("Error handling connections: %s", e)

    def _handle_messages(self):
        while not self._closed.is_set():
            ready_sockets: list[socket.socket] = []
            # Wait until there is at least one endpoint
            with self._endpoints_lock:
                if not self._endpoints:
                    self._empty_endpoints_condition.wait()
                ready_sockets, _, _ = select.select(
                    self._endpoints.values(), [], [], SELECT_TIMEOUT
                )
                    # Release the lock to allow modifications to endpoints before processing messages
            if ready_sockets:
                for sock in ready_sockets:
                    try:
                        # Find the peer associated with the ready to receive socket
                        peer = next(
                            (p for p, s in self._endpoints.items() if s == sock), None
                        )
                        if peer and self._status.get(peer) == ConnectionStatus.CONNECTED:
                            msg = self._message_handler.receive_obj(sock)
                            self._logger.info("Received message from %s: %s", peer, msg)
                            self._on_new_message(msg)
                    except ConnectionClosedError:
                        # Remove endpoint and close socket on connection closed
                        self._logger.info("Connection closed by remote peer.")
                        with self._endpoints_lock:
                            self._endpoints = {
                                p: s for p, s in self._endpoints.items() if s != sock
                            }
                        sock.close()
                    except Exception as e:
                        # Remove endpoint and close socket on error
                        self._logger.error("Error receiving message: %s", e)
                        with self._endpoints_lock:
                            self._endpoints = {
                                p: s for p, s in self._endpoints.items() if s != sock
                            }
                        sock.close()

    def close(self):
        """Closes the server connection handler and all associated sockets."""
        self.stop_new_connections()
        if not self._closed.is_set():
            self._closed.set() # Set the closed event to stop the receiver thread
            with self._endpoints_lock:
                self._empty_endpoints_condition.notify_all() # Wake up the receiver thread if it's waiting
            self._receiver_thread.join() # Wait for the receiver thread to finish (waits on select for SELECT_TIMEOUT)
            with self._endpoints_lock:
                # Shutdown all sockets
                for sock in self._endpoints.values():
                    try:
                        sock.shutdown(socket.SHUT_RDWR)
                    except Exception as e:
                        self._logger.warning(
                            "Error shutting down socket: %s \n Maybe it was already closed?",
                            e,
                        )
            for sock in self._endpoints.values():
                sock.close()


class ClientConnectionHandler(abc.ABC):
    """Abstract base class for client connection handlers."""

    _logger = logging.getLogger(__name__)

    def __init__(self):
        """Initialize the client connection handler."""
        self._on_message: Callable[[Any], None] | None = None
        self._on_message_lock = threading.Lock()

    def set_on_message(self, on_message: Callable[[Any], None]) -> None:
        """Set the callback function to handle incoming messages.

        Args:
            on_message (Callable[[Any], None]): The callback function.
        """
        with self._on_message_lock:
            self._on_message = on_message

    @abc.abstractmethod
    def send_obj(self, obj: Any) -> None:
        """Send an object to the server.

        Args:
            obj (Any): The object to send.
        """

    @abc.abstractmethod
    def start_receiving(self):
        """Start receiving messages from the server."""
        pass

    @abc.abstractmethod
    def close(self):
        """Close the client connection handler."""
        pass


class TCPClientConnectionHandler(ClientConnectionHandler):
    """TCP implementation of a client connection handler."""

    _logger = logging.getLogger(__name__)

    def __init__(self, my_self: Peer, conn_socket: socket.socket):
        """Initialize the TCP client connection handler.

        Args:
            my_self (Peer): The local peer object.
            conn_socket (socket.socket): The socket connected to the server.
            on_message (Callable[[Any], None]): Callback function to handle incoming messages.
        """
        super().__init__()
        self._message_handler: TCPMessageHandler = MessageHandlerFactory.getDefault()
        self._my_self: Peer = my_self
        self._socket: socket.socket = conn_socket
        self._receiver_thread: threading.Thread | None = None
        self._exit_event: threading.Event = threading.Event()

    def send_obj(self, obj: Any) -> None:
        if self._socket:
            self._message_handler.send_obj(self._socket, obj)
        else:
            raise RuntimeError("Not connected to server.")

    def start_receiving(self):
        """Start the thread to handle incoming messages."""
        self._receiver_thread = threading.Thread(
            target=self._handle_incoming_messages,
            name="TCPClientMessageReceiverThread",
            daemon=False,
        )
        self._receiver_thread.start()

    def close(self):
        """Close the TCP client connection handler."""
        if self._socket:
            try:
                self._exit_event.set()
                self._socket.shutdown(socket.SHUT_RDWR)
            except Exception as e:
                self._logger.warning(
                    "Error shutting down socket: %s \n Maybe it was already closed?", e
                )
        if self._receiver_thread:
            self._receiver_thread.join()
        self._socket.close()

    def _handle_incoming_messages(self):
        while not self._exit_event.is_set():
            try:
                msg = self._message_handler.receive_obj(self._socket)
                with self._on_message_lock:
                    if self._on_message:
                        self._on_message(msg)
            except TimeoutError:
                # Just a timeout, loop again
                continue
            except ConnectionClosedError:
                #TODO: Handle reconnection logic here
                self._logger.info("Connection closed by server.")
            except Exception as e:
                self._logger.error("Error receiving message: %s", e)


class ConnectionHandlerFactory:
    """Factory class for creating connection handlers."""

    @staticmethod
    def get_default_server_handler(
        on_new_peer: Callable[[Peer], None],
        on_new_message: Callable[[BaseMessage], None],
    ) -> TCPServerConnectionHandler:
        """Get the default server connection handler.

        Args:
            on_new_peer (Callable[[Peer], None]): Callback function to call on new peer connections.

        Returns:
            ServerConnectionHandler: The default server connection handler.
        """
        # TODO: Make this generic implementing ServerConnectionHandler interface
        return TCPServerConnectionHandler(on_new_peer, on_new_message)
