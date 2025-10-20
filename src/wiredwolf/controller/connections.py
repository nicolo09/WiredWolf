import abc
from collections.abc import Callable
import logging
from math import log
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
            raise ConnectionError("Connection closed by the other side.")
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
    _message_handler: TCPMessageHandler

    def __init__(self):
        self._message_handler = MessageHandlerFactory.getDefault()

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

    _on_new_peer: Callable[[Peer], None]
    _on_new_message: Callable[[BaseMessage], None]
    _new_conn_socket: socket.socket
    _new_conn_thread: threading.Thread
    _receiver_thread: threading.Thread
    _endpoints: dict[Peer, socket.socket] = {}
    _status: dict[Peer, ConnectionStatus] = {}
    _receive_conn: bool = True
    _closed: bool = False

    def __init__(
        self,
        on_new_peer: Callable[[Peer], None],
        on_new_message: Callable[[BaseMessage], None],
        bind_address: tuple[str, int] = ("", 0),
        server_socket: socket.socket | None = None,
    ):
        super().__init__()
        self._on_new_peer = on_new_peer
        self._on_new_message = on_new_message
        self._new_conn_socket = (
            server_socket if server_socket else socket.create_server(bind_address)
        )
        # Starts the thread to handle new incoming connections
        self._new_conn_thread = threading.Thread(
            target=self._handle_connections, name="TCPServerConnectionHandlerThread"
        )
        self._new_conn_thread.start()
        self._receiver_thread = threading.Thread(
            target=self._handle_messages, name="TCPServerMessageReceiverThread"
        )
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
        if self._receive_conn:
            self._receive_conn = False
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
        while self._receive_conn:
            try:
                self._logger.debug("Waiting for new connections...")
                client_socket, client_address = self._new_conn_socket.accept()
                self._logger.info("Accepted connection from %s", client_address)
                client_socket.settimeout(TIMEOUT)
                try:
                    # First thing peer sends is their identification (serialized peer object)
                    peer: Peer = self._message_handler.receive_obj(client_socket)
                    try:
                        # Add the endpoint
                        self._endpoints[peer] = client_socket
                        self._status[peer] = ConnectionStatus.CONNECTING
                        # Try to handle the new peer connection
                        self._on_new_peer(peer)
                        self._status[peer] = ConnectionStatus.CONNECTED
                    except Exception as e:
                        # If handling the new peer fails, remove the endpoint
                        self._endpoints.pop(peer)
                        self._logger.error("Error handling new peer %s: %s", peer, e)
                except TimeoutError:
                    continue
            except Exception as e:
                if not self._receive_conn:
                    self._logger.info("Server stopped accepting new connections")
                else:
                    self._logger.error("Error handling connections: %s", e)

    def _handle_messages(self):
        while not self._closed:
            ready_sockets, _, _ = select.select(
                self._endpoints.values(), [], [], SELECT_TIMEOUT
            )
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
                except Exception as e:
                    # Remove endpoint and close socket on error
                    self._logger.error("Error receiving message: %s", e)
                    self._endpoints = {
                        p: s for p, s in self._endpoints.items() if s != sock
                    }
                    sock.close()

    def close(self):
        """Closes the server connection handler and all associated sockets."""
        self.stop_new_connections()
        if not self._closed:
            self._closed = True
            for sock in self._endpoints.values():
                if sock:
                    sock.shutdown(socket.SHUT_RDWR)
            self._receiver_thread.join()
            for sock in self._endpoints.values():
                sock.close()


class ClientConnectionHandler(abc.ABC):
    """Abstract base class for client connection handlers."""

    _logger = logging.getLogger(__name__)
    _on_message: Callable[[Any], None] | None

    def __init__(self):
        """Initialize the client connection handler."""
        self._on_message = None

    def set_on_message(self, on_message: Callable[[Any], None]) -> None:
        """Set the callback function to handle incoming messages.

        Args:
            on_message (Callable[[Any], None]): The callback function.
        """
        self._on_message = on_message

    @abc.abstractmethod
    def send_obj(self, obj: Any) -> None:
        """Send an object to the server.

        Args:
            obj (Any): The object to send.
        """


class TCPClientConnectionHandler(ClientConnectionHandler):
    """TCP implementation of a client connection handler."""

    _message_handler: TCPMessageHandler
    _peer: Peer
    _socket: socket.socket

    def __init__(self, my_self: Peer, endpoint: socket.socket):
        """Initialize the TCP client connection handler.

        Args:
            my_self (Peer): The local peer object.
            endpoint (socket.socket): The socket endpoint for the connection.
            on_message (Callable[[Any], None]): Callback function to handle incoming messages.
        """
        super().__init__()
        self._message_handler = MessageHandlerFactory.getDefault()
        self._peer = my_self
        self._socket = endpoint

    def send_obj(self, obj: Any) -> None:
        if self._socket:
            self._message_handler.send_obj(self._socket, obj)
        else:
            raise RuntimeError("Not connected to server.")


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
