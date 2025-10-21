import socket
from typing import Any
import pytest
import wiredwolf.controller.connections as connections


class TestBaseConnection:
    def test_too_long_data_raises(self):
        handler = connections.TCPMessageHandler(connections.PickleSerializer())
        with pytest.raises(ValueError):
            handler.add_length_prefix(b"x" * (int("9" * handler.PREFIX_LEN) + 1))

    def test_base_connection_handler(self):
        handler = connections.TCPMessageHandler(connections.PickleSerializer())
        assert handler.add_length_prefix(b"test") == b"0004test"

    def test_send_and_receive(self):
        server_socket, client_socket = socket.socketpair()
        handler = connections.TCPMessageHandler(connections.PickleSerializer())
        handler.send(server_socket, b"test")
        received = handler.receive(client_socket)
        assert received == b"test"


@pytest.fixture
def server_conn_handler():
    def check_is_instance(obj: Any, cls: type):
        assert isinstance(obj, cls)

    serverConnHandler = connections.TCPServerConnectionHandler(
        lambda peer: check_is_instance(peer, connections.Peer),
        lambda msg: check_is_instance(msg, connections.BaseMessage),
        ("127.0.0.1", 0),
    )
    yield serverConnHandler
    serverConnHandler.stop_new_connections()
    serverConnHandler.close()


class TestServerConnection:
    def test_server_creation(
        self, server_conn_handler: connections.TCPServerConnectionHandler
    ):
        assert server_conn_handler is not None
