from collections.abc import Callable
import logging
import socket
import threading
from typing import Any
import pickle

from wiredwolf.controller.commons import Peer


class PickleSerializer():

    def __init__(self):
        pass

    def serialize(self, data: Any) -> bytes:
        return pickle.dumps(data)

    def deserialize(self, data: bytes) -> Any:
        return pickle.loads(data)


class MessageHandler():

    PREFIX_LEN: int = 4

    def __init__(self, Serializer: PickleSerializer):
        self._serializer = Serializer

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

    def send_obj(self, endpoint: socket.socket, obj: Any) -> None:
        data = self._serializer.serialize(obj)
        self.send(endpoint, data)

    def receive(self, endpoint: socket.socket) -> bytes:
        data_len = endpoint.recv(self.PREFIX_LEN)
        if not data_len:
            return b""
        data_len = int(data_len.decode('utf-8').strip())
        return endpoint.recv(data_len)

    def receive_obj(self, endpoint: socket.socket) -> Any:
        data = self.receive(endpoint)
        return self._serializer.deserialize(data)


class ServerConnectionHandler():

    __logger = logging.getLogger(__name__)

    _receiver_socket: socket.socket
    _receiver_thread: threading.Thread
    _receiver_message_handler: MessageHandler

    receive_conn: bool = True

    def __init__(self, on_new_peer: Callable[[Peer, socket.socket], None], bind_address: tuple[str, int] = ("", 0)):
        self._on_new_peer = on_new_peer
        self._receiver_socket = socket.create_server(bind_address)
        self._receiver_thread = threading.Thread(
            target=self._handle_connections)
        self._receiver_thread.start()
        self.__logger.info(
            f"Server listening on {self._receiver_socket.getsockname()}")
        self._receiver_message_handler = MessageHandler(PickleSerializer())

    def stop_new_connections(self):
        self.receive_conn = False
        self._receiver_socket.close()
        self._receiver_thread.join()

    def get_receiver_socket(self) -> socket.socket:
        return self._receiver_socket

    def _handle_connections(self):
        while self.receive_conn:
            try:
                self.__logger.debug("Waiting for new connections...")
                client_socket, client_address = self._receiver_socket.accept()
                self.__logger.info(
                    f"Accepted connection from {client_address}")
                client_socket.settimeout(5)  # TODO: magic number
                try:
                    # First thing peer sends is their identification (serialized peer object)
                    peer: Peer = self._receiver_message_handler.receive_obj(client_socket)
                    self._on_new_peer(Peer(peer.name, client_address), client_socket)
                except TimeoutError:
                    continue
                finally:
                    client_socket.close()
            except OSError as e:
                if not self.receive_conn:
                    self.__logger.info(
                        f"Server stopped accepting new connections")
                else:
                    self.__logger.error(f"Error handling connections: {e}")


class ClientConnectionHandler(MessageHandler):

    __logger = logging.getLogger(__name__)
    _message_handler: MessageHandler

    def __init__(self, peer: Peer):
        self._peer = peer
        self._message_handler = MessageHandler(PickleSerializer())

    def connect_to_server(self, address: tuple[str, int]) -> socket.socket | None:
        """Connects to a server at the specified address and port."""
        try:
            self._socket = socket.create_connection(
                address, timeout=5)  # TODO: Magic number
            self._socket.settimeout(5)  # TODO: Magic number
            self._message_handler.send_obj(self._socket, self._peer)
            return self._socket
        except OSError as e:
            self.__logger.error(f"Error connecting to server: {e}")
            return None
