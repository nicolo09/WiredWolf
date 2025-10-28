import abc
from collections.abc import Callable
import logging
from enum import Enum
from types import CoroutineType
from typing import Any
import pickle
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.messages import BaseMessage
import asyncio


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


class ConnectionStatus(Enum):
    CONNECTING = 1
    CONNECTED = 2
    RECOVERING = 3
    ERROR = 4


class ServerConnectionHandler(abc.ABC):
    _logger = logging.getLogger(__name__)

    def __init__(self):
        self._message_handler: AsyncTCPMessageHandler = (
            MessageHandlerFactory.getDefault()
        )

    @abc.abstractmethod
    async def send_obj(self, receiver: Peer, obj: Any) -> None:
        pass

    @abc.abstractmethod
    async def receive_obj(self, sender: Peer) -> Any:
        pass

    @abc.abstractmethod
    async def start_listening(self, bind_address: tuple[str, int]) -> None:
        pass

    @abc.abstractmethod
    def stop_new_connections(self):
        pass

    @abc.abstractmethod
    def close(self):
        pass


class ClientConnectionHandler(abc.ABC):
    """Abstract base class for client connection handlers."""

    _logger = logging.getLogger(__name__)

    def __init__(self, my_self: Peer):
        """Initialize the client connection handler."""
        self._on_message: Callable[[Any], None] | None = None
        self._my_self: Peer = my_self

    @property
    def my_self(self) -> Peer:
        """Get the peer representing this client.

        Returns:
            Peer: The peer representing this client.
        """
        return self._my_self

    def set_on_message(self, on_message: Callable[[Any], None]) -> None:
        """Set the callback function to handle incoming messages.

        Args:
            on_message (Callable[[Any], None]): The callback function.
        """
        self._on_message = on_message

    @abc.abstractmethod
    async def send_obj(self, obj: Any) -> None:
        """Send an object to the server.

        Args:
            obj (Any): The object to send.
        """
        pass

    @abc.abstractmethod
    async def start_receiving(self):
        """Start receiving messages from the server."""
        pass

    @abc.abstractmethod
    async def close(self):
        """Close the client connection handler."""
        pass


class AsyncTCPClientConnectionHandler(ClientConnectionHandler):
    _logger = logging.getLogger(__name__)

    def __init__(
        self, my_self: Peer, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        super().__init__(my_self)
        self._message_handler: AsyncTCPMessageHandler = (
            MessageHandlerFactory.getDefault()
        )
        self._my_self: Peer = my_self
        self._reader: asyncio.StreamReader = reader
        self._writer: asyncio.StreamWriter = writer
        self._receiving_task: asyncio.Task[None] | None = None

    async def send_obj(self, obj: Any):
        """Send an object to the server.

        Args:
            obj (Any): The object to send.
        """
        await self._message_handler.send_obj(self._writer, obj)

    async def start_receiving(self):
        """Start receiving messages from the server."""
        self._receiving_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        """Internal method to continuously receive messages."""
        while True:
            try:
                msg: Any = await self._message_handler.receive_obj(self._reader)
                if self._on_message:
                    self._on_message(msg)
            except ConnectionClosedError:
                self._logger.info("Connection closed by server.")
                return
            except Exception as e:
                self._logger.error("Error receiving message: %s", e)
                return

    async def close(self):
        """Close the client connection handler."""
        self._writer.close()
        await self._writer.wait_closed()
        if self._receiving_task:
            self._receiving_task.cancel()
            await self._receiving_task
        self._logger.info("Client connection closed.")


MAX_CONNECTION_TIME = 10  # seconds


class AsyncTCPMessageHandler:
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

    async def send(self, endpoint: asyncio.StreamWriter, data: bytes) -> None:
        endpoint.write(self.add_length_prefix(data))
        await endpoint.drain()

    async def send_msg(self, endpoint: asyncio.StreamWriter, msg: str) -> None:
        data = msg.encode("utf-8")
        await self.send(endpoint, data)

    async def send_obj(self, endpoint: asyncio.StreamWriter, obj: Any) -> None:
        data = self._serializer.serialize(obj)
        await self.send(endpoint, data)

    async def receive(self, endpoint: asyncio.StreamReader) -> bytes:
        data_len = await endpoint.read(self.PREFIX_LEN)
        if not data_len:
            raise ConnectionClosedError("Connection closed by the other side.")
        data_len = int(data_len.decode("utf-8").strip())
        return await endpoint.read(data_len)

    async def receive_msg(self, endpoint: asyncio.StreamReader) -> str:
        data = await self.receive(endpoint)
        return data.decode("utf-8")

    async def receive_obj(self, endpoint: asyncio.StreamReader) -> Any:
        data = await self.receive(endpoint)
        return self._serializer.deserialize(data)


class AsyncTCPServerConnectionHandler(ServerConnectionHandler):
    def __init__(
        self,
        on_new_peer: Callable[[Peer], CoroutineType[Any, Any, None]],
        on_new_message: Callable[[BaseMessage], CoroutineType[Any, Any, None]],
    ):
        super().__init__()
        self._on_new_peer: Callable[[Peer], CoroutineType[Any, Any, None]] = on_new_peer
        self._on_new_message: Callable[[BaseMessage], CoroutineType[Any, Any, None]] = on_new_message
        self._async_message_handler = AsyncTCPMessageHandler(
            MessageHandlerFactory.getDefaultSerializer()
        )
        self._endpoints: dict[
            Peer, tuple[asyncio.StreamReader, asyncio.StreamWriter]
        ] = {}
        self._status: dict[Peer, ConnectionStatus] = {}
        self._receiving_tasks: dict[Peer, asyncio.Task[None]] = {}
        self._server: asyncio.Server | None = None

    async def start_listening(self, bind_address: tuple[str, int]) -> None:
        if self._server:
            raise RuntimeError("Server is already listening for new connections.")
        else:
            self._server = await asyncio.start_server(
                self._client_connected_cb,
                host=bind_address[0],
                port=bind_address[1],
            )
            self._logger.info(
                "Server started listening for new connections on %s:%d",
                bind_address[0],
                bind_address[1],
            )
            asyncio.create_task(self._server.serve_forever())

    async def _client_connected_cb(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        client_address = writer.get_extra_info("peername")
        self._logger.info("Accepted connection from %s", client_address)
        async with asyncio.timeout(MAX_CONNECTION_TIME):
            try:
                # First thing peer sends is their identification (serialized peer object)
                peer: Peer = await self._async_message_handler.receive_obj(reader)
                self._logger.info("Identified new peer: %s", peer)
                self._endpoints[peer] = (reader, writer)
                self._status[peer] = ConnectionStatus.CONNECTED
                await self._on_new_peer(peer)
                # TODO Start listening for messages from this peer
            except ConnectionClosedError:
                self._logger.warning(
                    "Connection from %s closed before identification.", client_address
                )
                writer.close()
                await writer.wait_closed()
                return
            except TimeoutError:
                self._logger.warning(
                    "Connection from %s timed out during identification.",
                    client_address,
                )
                writer.close()
                await writer.wait_closed()
                return
            except Exception as e:
                self._logger.error(
                    "Error during connection from %s: %s", client_address, e
                )
                writer.close()
                await writer.wait_closed()
                return
            else:
                # Successful connection
                self._logger.info("New peer connected: %s", peer)
                self._status[peer] = ConnectionStatus.CONNECTED
                self._receiving_tasks[peer] = asyncio.create_task(
                    self._handle_peer_message(peer)
                )

    async def _handle_peer_message(self, peer: Peer):
        reader, _ = self._endpoints[peer]
        while True:
            try:
                msg: BaseMessage = await self._async_message_handler.receive_obj(reader)
                if msg.sender != peer:  # Ensure the message sender is set correctly
                    self._logger.warning(
                        "Message from %s has incorrect sender (%s) and will not be handled",
                        peer,
                        msg.sender,
                    )
                else:
                    await self._on_new_message(msg)
            except ConnectionClosedError:
                self._logger.info("Connection closed by peer: %s", peer)
                self._endpoints.pop(peer)
                self._status.pop(peer)
                return
            except Exception as e:
                self._logger.error("Error receiving message from %s: %s", peer, e)
                self._status[peer] = ConnectionStatus.ERROR
                # TODO: Implement reconnection logic
                return

    def stop_new_connections(self):
        if self._server is None:
            raise RuntimeError("Server is not currently accepting new connections.")
        else:
            self._server.close()
            self._logger.info("Stopped accepting new connections.")

    async def send_obj(self, receiver: Peer, obj: Any) -> None:
        if receiver in self._endpoints:
            _, writer = self._endpoints[receiver]
            await self._async_message_handler.send_obj(writer, obj)
        else:
            self._logger.error("No connection found for peer: %s", receiver)
            raise ValueError(f"No connection found for peer: {receiver}")

    async def receive_obj(self, sender: Peer) -> Any:
        if sender in self._endpoints:
            reader, _ = self._endpoints[sender]
            return await self._async_message_handler.receive_obj(reader)
        else:
            self._logger.error("No connection found for peer: %s", sender)
            raise ValueError(f"No connection found for peer: {sender}")

    def close(self):
        for peer, (_, writer) in self._endpoints.items():
            writer.close()
            asyncio.run(writer.wait_closed())
            self._logger.info("Closed connection with peer: %s", peer)
        self._endpoints.clear()
        self._status.clear()
        self._receiving_tasks.clear()
        self._logger.info("All connections closed.")


class MessageHandlerFactory:
    @staticmethod
    def getDefaultSerializer() -> Serializer:
        return PickleSerializer()

    @staticmethod
    def getDefault() -> AsyncTCPMessageHandler:
        return AsyncTCPMessageHandler(PickleSerializer())


class ConnectionHandlerFactory:
    """Factory class for creating connection handlers."""

    @staticmethod
    def get_default_server_handler(
        on_new_peer: Callable[[Peer], CoroutineType[Any, Any, None]],
        on_new_message: Callable[[BaseMessage], CoroutineType[Any, Any, None]],
    ) -> ServerConnectionHandler:
        """Get the default server connection handler.

        Args:
            on_new_peer (Callable[[Peer], None]): Callback function to call on new peer connections.

        Returns:
            ServerConnectionHandler: The default server connection handler.
        """
        # TODO: Make this generic implementing ServerConnectionHandler interface
        return AsyncTCPServerConnectionHandler(on_new_peer, on_new_message)
