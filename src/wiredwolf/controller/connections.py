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


class ServerConnectionHandler():

    __logger = logging.getLogger(__name__)

    __receiver_socket: socket.socket
    __receiver_thread: threading.Thread
    __serializer: PickleSerializer

    receive_conn: bool = True

    def __init__(self, on_new_peer: Callable[[Peer], None], bind_address: tuple[str, int] = ("", 0)):
        self.__on_new_peer = on_new_peer
        self.__receiver_socket = socket.create_server(bind_address)
        self.__receiver_thread = threading.Thread(
            target=self.__handle_connections)
        self.__receiver_thread.start()
        self.__logger.info(
            f"Server listening on {self.__receiver_socket.getsockname()}")
        self.__serializer = PickleSerializer()

    def stop_new_connections(self):
        self.receive_conn = False
        self.__receiver_socket.close()
        self.__receiver_thread.join()

    def get_receiver_socket(self) -> socket.socket:
        return self.__receiver_socket

    def __handle_connections(self):
        try:
            while self.receive_conn:
                self.__logger.debug("Waiting for new connections...")
                client_socket, client_address = self.__receiver_socket.accept()
                self.__logger.info(
                    f"Accepted connection from {client_address}")
                client_socket.settimeout(5)  # TODO: magic number
                self.__on_new_peer(Peer("peer", client_address[0]))
                # try:
                #     # TODO: Receive peer identification
                #     data = client_socket.recv(1024)  # TODO: magic number
                #     if data:
                #         peer: Peer = self.__serializer.deserialize(data)
                # except TimeoutError:
                #     continue
                # finally:
                #     client_socket.close()
        except OSError as e:
            self.__logger.error(f"Error handling connections: {e}")


class ClientConnectionHandler():

    __logger = logging.getLogger(__name__)

    __serializer: PickleSerializer

    def __init__(self, peer: Peer):
        self.__serializer = PickleSerializer()
        self.__peer = peer
    
    def connect_to_server(self, address: tuple[str, int]) -> socket.socket | None:
        """Connects to a server at the specified address and port."""
        try:
            self.__socket = socket.create_connection(
                address, timeout=5)  # TODO: Magic number
            return self.__socket
        except OSError as e:
            self.__logger.error(f"Error connecting to server: {e}")
            return None
