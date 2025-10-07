import abc
from collections.abc import Callable
import logging
import socket
import threading
from typing import Any
import pickle

from wiredwolf.controller import TIMEOUT
from wiredwolf.controller.commons import Peer


class Serializer(abc.ABC):
    @abc.abstractmethod
    def serialize(self, data: Any) -> bytes:
        pass

    @abc.abstractmethod
    def deserialize(self, data: bytes) -> Any:
        pass


class PickleSerializer(Serializer):

    def __init__(self):
        pass

    def serialize(self, data: Any) -> bytes:
        return pickle.dumps(data)

    def deserialize(self, data: bytes) -> Any:
        return pickle.loads(data)


class TCPMessageHandler():

    PREFIX_LEN: int = 4

    def __init__(self, serializer: Serializer):
        self._serializer = serializer

    def add_length_prefix(self, data: bytes) -> bytes:
        if len(data) < int("9"*self.PREFIX_LEN):
            # Ensure the data length is within the limit
            bytes_len = format(
                len(data), '0'+str(self.PREFIX_LEN)+'d').encode('utf-8')
            return bytes_len + data
        else:
            raise ValueError("Data too long")

    def send(self, endpoint: socket.socket, data: bytes) -> None:
        endpoint.sendall(self.add_length_prefix(data))

    def send_msg(self, endpoint: socket.socket, msg: str) -> None:
        data = msg.encode('utf-8')
        self.send(endpoint, data)

    def send_obj(self, endpoint: socket.socket, obj: Any) -> None:
        data = self._serializer.serialize(obj)
        self.send(endpoint, data)

    def receive(self, endpoint: socket.socket) -> bytes:
        data_len = endpoint.recv(self.PREFIX_LEN)
        if not data_len:
            return b""
        data_len = int(data_len.decode('utf-8').strip())
        return endpoint.recv(data_len)

    def receive_msg(self, endpoint: socket.socket) -> str:
        data = self.receive(endpoint)
        return data.decode('utf-8')

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


class TCPServerConnectionHandler(ServerConnectionHandler):

    _on_new_peer: Callable[[Peer], None]
    _receiver_socket: socket.socket
    _receiver_thread: threading.Thread
    _endpoints: dict[Peer, socket.socket] = {}
    receive_conn: bool = True

    def __init__(self, on_new_peer: Callable[[Peer], None], bind_address: tuple[str, int] = ("", 0), server_socket: socket.socket | None = None):
        super().__init__()
        self._on_new_peer = on_new_peer
        self._receiver_socket = server_socket if server_socket else socket.create_server(
            bind_address)
        self._receiver_thread = threading.Thread(
            target=self._handle_connections,
            name="TCPServerConnectionHandlerThread")
        self._receiver_thread.start()
        self._logger.info(
            "Server listening on %s", self._receiver_socket.getsockname())

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
        self.receive_conn = False
        self._receiver_socket.close()
        self._receiver_thread.join()

    def get_receiver_socket(self) -> socket.socket:
        return self._receiver_socket

    def _handle_connections(self):
        while self.receive_conn:
            try:
                self._logger.debug("Waiting for new connections...")
                client_socket, client_address = self._receiver_socket.accept()
                self._logger.info(
                    "Accepted connection from %s", client_address)
                client_socket.settimeout(TIMEOUT)
                try:
                    # First thing peer sends is their identification (serialized peer object)
                    peer: Peer = self._message_handler.receive_obj(
                        client_socket)
                    try:
                        # Add the endpoint
                        self._endpoints[peer] = client_socket
                        # Try to handle the new peer connection
                        self._on_new_peer(peer)
                    except Exception as e:
                        # If handling the new peer fails, remove the endpoint
                        self._endpoints.pop(peer)
                        self._logger.error(
                            "Error handling new peer %s: %s", peer, e)
                except TimeoutError:
                    continue
            except OSError as e:
                if not self.receive_conn:
                    self._logger.info(
                        "Server stopped accepting new connections")
                else:
                    self._logger.error("Error handling connections: %s", e)


class TCPClientConnectionHandler(TCPMessageHandler):

    __logger = logging.getLogger(__name__)
    _message_handler: TCPMessageHandler
    _socket: socket.socket | None = None

    def __init__(self, peer: Peer):
        super().__init__(MessageHandlerFactory.getDefaultSerializer())
        self._peer = peer
        self._message_handler = MessageHandlerFactory.getDefault()

    def connect_to_server(self, address: tuple[str, int]) -> socket.socket | None:
        """Connects to a server at the specified address and port."""
        try:
            self._socket = socket.create_connection(
                address, timeout=TIMEOUT)
            self._socket.settimeout(TIMEOUT)
            self._message_handler.send_obj(self._socket, self._peer)
            return self._socket
        except OSError as e:
            self.__logger.error("Error connecting to server: %s", e)
            return None


class ConnectionHandlerFactory:

    @staticmethod
    def getDefaultClientHandler(peer: Peer) -> TCPClientConnectionHandler:
        return TCPClientConnectionHandler(peer)
    
    @staticmethod
    def getDefaultServerHandler(on_new_peer: Callable[[Peer], None]) -> TCPServerConnectionHandler:
        return TCPServerConnectionHandler(on_new_peer) 