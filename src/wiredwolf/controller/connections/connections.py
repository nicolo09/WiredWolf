import abc
from collections.abc import Callable
import logging
from enum import Enum
from types import CoroutineType
from typing import Any
import pickle
from wiredwolf.controller.commons import (
    CONNECTION_TIMEOUT,
    RECEIVING_TASK_CLOSE_TIMEOUT,
    Peer,
)
from wiredwolf.controller.messages import (
    BaseMessage,
    ConnectionClosedMessage,
    HeartbeatMessage,
    NotAcknowledgeMessage,
)
import asyncio
from asyncio import CancelledError


PEERNAME_EXTRA_INFO = "peername"
HEARTBEAT_INTERVAL = 5  # seconds
CONNECTION_TIMEOUT_HEARTBEAT = 10  # seconds

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
    """Abstract base class for server side connection handlers."""
    _logger = logging.getLogger(__name__)

    def __init__(self):
        self._message_handler: AsyncTCPMessageHandler = (
            MessageHandlerFactory.getDefault()
        )

    @abc.abstractmethod
    async def send_obj(self, receiver: Peer, obj: Any) -> None:
        """Send an object to a specific peer."""
        pass

    @abc.abstractmethod
    async def receive_obj(self, sender: Peer) -> Any:
        """Receive an object from a specific peer."""
        pass

    @abc.abstractmethod
    async def start_listening(self) -> None:
        """Start listening for new connections."""
        pass

    @abc.abstractmethod
    def stop_new_connections(self):
        """Stop accepting new connections to this server."""
        pass

    @abc.abstractmethod
    async def close(self):
        """Close the server connection handler, including all active connections and resetting its state."""
        pass


class ClientConnectionHandler(abc.ABC):
    """Abstract base class for client side connection handlers."""

    _logger = logging.getLogger(__name__)

    def __init__(self, my_self: Peer):
        """Initialize the client connection handler."""
        self._on_message: Callable[[BaseMessage], None] | None = None
        self._my_self: Peer = my_self

    @property
    def my_self(self) -> Peer:
        """Get the peer representing this client.

        Returns:
            Peer: The peer representing this client.
        """
        return self._my_self

    def set_on_message(self, on_message: Callable[[BaseMessage], None]) -> None:
        """Set the callback function to handle incoming messages.

        Args:
            on_message (Callable[[BaseMessage], None]): The callback function.
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
        self, my_self: Peer, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, endpoint: tuple[str, int], on_disconnect: Callable[[], CoroutineType[Any, Any, None]] | None = None
    ):
        """Initialize the client connection handler with the given peer as self, reader and writer to communicate with the server."""
        super().__init__(my_self)
        self._message_handler: AsyncTCPMessageHandler = (
            MessageHandlerFactory.getDefault()
        )
        self._my_self: Peer = my_self
        self._reader: asyncio.StreamReader = reader
        self._writer: asyncio.StreamWriter = writer
        self._endpoint: tuple[str, int] = endpoint
        self._receiving_task: asyncio.Task[None] | None = None
        self._on_disconnect: Callable[[], CoroutineType[Any, Any, None]] | None = on_disconnect

    @property
    def endpoint(self) -> tuple[str, int]:
        """Get the endpoint (host, port) of the server this client is connected to.

        Returns:
            tuple[str, int]: The endpoint of the server.
        """
        return self._endpoint

    async def send_obj(self, obj: Any):
        """Send an object to the server.

        Args:
            obj (Any): The object to send.
        """
        await self._message_handler.send_obj(self._writer, obj)

    async def start_receiving(self) -> None:
        """Start receiving messages from the server."""
        if self._receiving_task is not None:
            raise RuntimeError("Already receiving messages.")
        self._receiving_task = asyncio.create_task(self._receive_loop())
        self._receiving_task.add_done_callback(self._handle_receive_loop_closed)

    def _handle_receive_loop_closed(self, task: asyncio.Task[None]) -> None:
        """Handle the completion of the receive loop task.

        Args:
            task (asyncio.Task[None]): The completed task.
        """
        # TODO: Implement reconnection logic here
        if self._writer.is_closing():
            # Since I want to close the connection myself, ignore errors from receive loop and just exit
            self._logger.info(
                "Writer is closing, ignoring receive loop task exit status."
            )
        elif task.cancelled():
            # If the task was cancelled, treat it as a normal shutdown
            self._logger.info("Receive loop task was cancelled.")
        else:
            try:
                exc = task.exception()
            except asyncio.CancelledError:
                self._logger.info("Receive loop task was cancelled.")
                return
            except Exception as e:
                self._logger.error(
                    "Error while retrieving receive loop task during close: %s", e
                )
                return

            if exc is None or isinstance(exc, ConnectionClosedError):
                # No exception or graceful connection closed
                self._logger.info("Receive loop task completed successfully.")
            elif isinstance(exc, TimeoutError):
                self._logger.warning(
                    "Receive loop task timed out. Connection may be lost."
                )
            else:
                self._logger.error("Receive loop task encountered an error: %s", exc)
            if self._on_message:
                self._on_message(
                    ConnectionClosedMessage("Connection closed by the server.")
                )

    async def _receive_loop(self) -> None:
        """Internal method to continuously receive messages."""
        while True:
            try:
                async with asyncio.timeout(CONNECTION_TIMEOUT_HEARTBEAT):
                    msg: Any = await self._message_handler.receive_obj(self._reader)
                    if self._on_message:
                        self._on_message(msg) 
                    else:
                        self._logger.warning(
                        "Received message but no on_message callback is set."
                        )
            except asyncio.CancelledError:
                self._logger.info("Receive loop cancelled.")
                return
            except TimeoutError as e:
                #TODO: Connection with server is considered killed, handle possible reconnection
                self._logger.info("Receive loop timed out.")
                if self._on_disconnect:
                    await self._on_disconnect() #FIXME: should this be used here?
                raise e
            except Exception as e:
                raise e

    async def close(self) -> None:
        """Closes the client connection handler."""
        try:
            #Close the writer to the server first, the server will close its writer from its side
            self._writer.close()
            await self._writer.wait_closed()
        except ConnectionResetError:
            self._logger.info(
                "Was trying to close connection but it was reset by server, considering it to be already closed."
            )
        finally:
            if self._receiving_task:
                try:
                    self._logger.info("Waiting for receiving task to finish...")
                    async with asyncio.timeout(RECEIVING_TASK_CLOSE_TIMEOUT):
                        await self._receiving_task
                except asyncio.CancelledError:
                    self._logger.info("Receiving task was cancelled during close.")
                except ConnectionClosedError:
                    self._logger.info(
                        "Connection closed from other side while closing from this side."
                    )
                except TimeoutError:
                    self._logger.warning(
                        "Receiving task didn't finish within timeout, cancelling it."
                    )
                    self._receiving_task.cancel()
                    await self._receiving_task
                finally:
                    self._logger.info("Receiving task awaited.")
        self._logger.info("Client connection closed.")


class AsyncTCPMessageHandler:  # TODO: Make this implement a MessageHandler interface
    """Message handler that uses a length-prefixed protocol to send and receive messages over asyncio TCP connections modeled with writers and readers."""

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
        """Sends data to endpoint adding length prefix before as a 4 digit int

        Args:
            endpoint (asyncio.StreamWriter): The writer to the endpoint
            data (bytes): The data to send
        """
        endpoint.write(self.add_length_prefix(data))
        await endpoint.drain()

    async def send_msg(self, endpoint: asyncio.StreamWriter, msg: str) -> None:
        """Sends a message to the endpoint, encoding it in UTF-8 and converting it to bytes.

        Args:
            endpoint (asyncio.StreamWriter): The writer to the endpoint
            msg (str): The message to send
        """
        data = msg.encode("utf-8")
        await self.send(endpoint, data)

    async def send_obj(self, endpoint: asyncio.StreamWriter, obj: Any) -> None:
        """Sends a serialized object to the endpoint.

        Args:
            endpoint (asyncio.StreamWriter): The writer to the endpoint
            obj (Any): The object to send
        """
        data = self._serializer.serialize(obj)
        await self.send(endpoint, data)

    async def receive(self, endpoint: asyncio.StreamReader) -> bytes:
        """Receives data from the endpoint, first reading the length prefix.

        Args:
            endpoint (asyncio.StreamReader): The reader to the endpoint
        Returns:
            bytes: The received data
        Raises:
            ConnectionClosedError: If the connection is closed by the other side.
        """
        data_len = await endpoint.read(self.PREFIX_LEN)
        if not data_len:
            raise ConnectionClosedError("Connection closed by the other side.")
        data_len = int(data_len.decode("utf-8").strip())
        return await endpoint.read(data_len)

    async def receive_msg(self, endpoint: asyncio.StreamReader) -> str:
        """Receives a message from the endpoint, decoding it from UTF-8.

        Args:
            endpoint (asyncio.StreamReader): The reader to the endpoint
        Returns:
            str: The received message
        Raises:
            ConnectionClosedError: If the connection is closed by the other side.
        """
        data = await self.receive(endpoint)
        return data.decode("utf-8")

    async def receive_obj(self, endpoint: asyncio.StreamReader) -> Any:
        """Receives a serialized object from the endpoint.

        Args:
            endpoint (asyncio.StreamReader): The reader to the endpoint
        Returns:
            Any: The received object
        Raises:
            ConnectionClosedError: If the connection is closed by the other side.
        """
        data = await self.receive(endpoint)
        return self._serializer.deserialize(data)


class AsyncTCPServerConnectionHandler(ServerConnectionHandler):
    """Server connection handler implementation using asyncio and TCP sockets."""

    def __init__(
        self,
        bind_address: tuple[str | None, int],
        on_new_peer: Callable[[Peer], CoroutineType[Any, Any, None]],
        on_peer_disconnected: Callable[[Peer], CoroutineType[Any, Any, None]],
        on_new_message: Callable[[BaseMessage], CoroutineType[Any, Any, None]],
        callback_failed_heartbeat: Callable[[Peer], CoroutineType[Any, Any, None]]|None=None,
        owner_connection: tuple[Peer, asyncio.StreamReader, asyncio.StreamWriter]
        | None = None,
        
    ):
        super().__init__()
        self._bind_address: tuple[str | None, int] = bind_address
        self._on_new_peer: Callable[[Peer], CoroutineType[Any, Any, None]] = on_new_peer
        self._on_peer_disconnected: Callable[[Peer], CoroutineType[Any, Any, None]] = (
            on_peer_disconnected
        )
        self._on_new_message: Callable[[BaseMessage], CoroutineType[Any, Any, None]] = (
            on_new_message
        )
        self._async_message_handler = AsyncTCPMessageHandler(
            MessageHandlerFactory.getDefaultSerializer()
        )
        self._endpoints: dict[
            Peer, tuple[asyncio.StreamReader, asyncio.StreamWriter]
        ] = {}
        self._status: dict[Peer, ConnectionStatus] = {}
        self._receiving_tasks: dict[Peer, asyncio.Task[None]] = {}
        self._server: asyncio.Server | None = None
        self._server_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._callback_failed_heartbeat: Callable[[Peer], CoroutineType[Any, Any, None]] | None = callback_failed_heartbeat
        if owner_connection is not None:
            peer, reader, writer = owner_connection
            self._endpoints[peer] = (reader, writer)
            self._status[peer] = ConnectionStatus.CONNECTED
            self._receiving_tasks[peer] = asyncio.create_task(
                self._handle_peer_message(peer)
            )

    async def start_listening(self) -> None:
        if self._server:
            raise RuntimeError("Server is already listening for new connections.")
        else:
            self._server = await asyncio.start_server(
                self._client_connected_cb,
                host=self._bind_address[0],
                port=self._bind_address[1],
            )
            self._logger.info(
                "Server started listening for new connections on %s:%d",
                self._bind_address[0],
                self._bind_address[1],
            )
            # keep a reference to the serve_forever task so it can be awaited/cancelled on close
            self._server_task = asyncio.create_task(self._server.serve_forever())
            self._heartbeat_task = asyncio.create_task(self._send_heartbeat())

    async def _send_heartbeat(self):
        """A function that sends a heartbeat message to all connected peers regularly"""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL) 
            for peer in list(self._endpoints.keys()):
                try:
                    await self.send_obj(peer, HeartbeatMessage())
                except Exception as e:
                    self._logger.error(
                        "Error sending heartbeat to %s: %s", peer, e
                    )
                    #TODO: handle properly what happens next
                    if self._callback_failed_heartbeat!=None:
                        await self._callback_failed_heartbeat(peer)

    async def _client_connected_cb(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        client_address = writer.get_extra_info(PEERNAME_EXTRA_INFO)
        self._logger.info("Accepted connection from %s", client_address)
        async with asyncio.timeout(CONNECTION_TIMEOUT):
            try:
                # First thing peer sends is their identification (serialized peer object)
                peer: Peer = await self._async_message_handler.receive_obj(
                    reader
                )  # TODO: Change this to a message containing the peer info instead of just the peer object
                self._logger.info("Identified new peer: %s", peer)
                self._endpoints[peer] = (reader, writer)
                self._status[peer] = ConnectionStatus.CONNECTING
                await self._on_new_peer(peer)
                # Successful connection
                self._logger.info("New peer connected: %s", peer)
                self._status[peer] = ConnectionStatus.CONNECTED
                self._receiving_tasks[peer] = asyncio.create_task(
                    self._handle_peer_message(peer)
                )
            except ConnectionClosedError:
                # Peer tried to connect but closed the connection before ending the handshake
                self._logger.warning(
                    "Connection from %s closed before identification.", client_address
                )
                writer.close()
                await writer.wait_closed()
                return
            except TimeoutError:
                # Peer did not identify in time
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
                    await self.send_obj(
                        peer,
                        NotAcknowledgeMessage(
                            msg.id, msg.sender, RuntimeError("Incorrect message sender")
                        ),
                    )  # TODO: Define a proper exception for this case
                else:
                    try:
                        await self._on_new_message(msg)
                    except Exception as e:
                        self._logger.error(
                            "Error handling message from %s: %s", peer, e
                        )
                        await self.send_obj(
                            peer, NotAcknowledgeMessage(msg.id, msg.sender, e)
                        )
            except ConnectionClosedError:
                self._logger.info("Connection closed by peer: %s", peer)
                self._endpoints.pop(peer)
                self._status.pop(peer)
                await self._on_peer_disconnected(peer)
                return
            except Exception as e:
                self._logger.error("Error receiving message from %s: %s", peer, e)
                self._status[peer] = ConnectionStatus.ERROR
                await self._on_peer_disconnected(peer)
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

    async def close(self):
        """Stops receiving new connections, closes all the open peer connections to this server and reset its status"""
        # Stop accepting new connections if server exists
        try:
            self.stop_new_connections()
        except Exception as e:
            self._logger.error(
                "Error while stopping new server connections during close: %s", e
            )
        finally:
            # Cancel any receiving tasks and wait for them to finish
            receiving_tasks = list(self._receiving_tasks.values())
            if receiving_tasks:
                for task in receiving_tasks:
                    try:
                        task.cancel()
                    except Exception:
                        pass
                await asyncio.gather(*receiving_tasks, return_exceptions=True)

            # Close all endpoint writers
            wait_closed_awaitables: list[CoroutineType[Any, Any, None]] = []
            for peer, (_, writer) in list(self._endpoints.items()):
                try:
                    writer.close()
                    wait_closed_awaitables.append(writer.wait_closed())
                    self._logger.info("Closed connection with peer: %s", peer)
                except Exception as e:
                    self._logger.warning("Error closing writer for %s: %s", peer, e)

            if wait_closed_awaitables:
                await asyncio.gather(*wait_closed_awaitables, return_exceptions=True)

            # Wait for the server to be fully closed and the serve_forever task to complete
            if self._server:
                try:
                    await self._server.wait_closed()
                except Exception as e:
                    self._logger.warning(
                        "Error while waiting for server to close: %s", e
                    )

            if self._server_task:
                try:
                    self._server_task.cancel()
                    await self._server_task
                except (Exception, CancelledError):
                    pass

            # Clear internal state
            self._endpoints.clear()
            self._status.clear()
            self._receiving_tasks.clear()
            self._server = None
            self._server_task = None
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
    def get_server_connection_handler(
        bind_address: tuple[str | None, int],
        on_new_peer: Callable[[Peer], CoroutineType[Any, Any, None]],
        on_peer_disconnected: Callable[[Peer], CoroutineType[Any, Any, None]],
        on_new_message: Callable[[BaseMessage], CoroutineType[Any, Any, None]],
        owner_connection: tuple[Peer, asyncio.StreamReader, asyncio.StreamWriter]
        | None = None,
    ) -> ServerConnectionHandler:
        """Creates and returns a new ServerConnectionHandler.

        Args:
            on_new_peer (Callable[[Peer], CoroutineType[Any, Any, None]]): The callback for new peer connections.
            on_peer_disconnected (Callable[[Peer], CoroutineType[Any, Any, None]]): The callback for peer disconnections.
            on_new_message (Callable[[BaseMessage], CoroutineType[Any, Any, None]]): The callback for new messages.

        Returns:
            ServerConnectionHandler: The created server connection handler.
        """
        return AsyncTCPServerConnectionHandler(
            bind_address=bind_address,
            on_new_peer=on_new_peer,
            on_peer_disconnected=on_peer_disconnected,
            on_new_message=on_new_message,
            owner_connection=owner_connection,
        )

    @staticmethod
    def get_client_connection_handler(
        my_self: Peer,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        endpoint: tuple[str, int],
        on_disconnect: Callable[[], CoroutineType[Any, Any, None]] | None = None,
    ) -> ClientConnectionHandler:
        """Creates and returns a new ClientConnectionHandler.

        Args:
            my_self (Peer): The peer representing this client.
            reader (asyncio.StreamReader): The reader for the connection.
            writer (asyncio.StreamWriter): The writer for the connection.
            endpoint (tuple[str, int]): The (IP, port) endpoint of the server to connect to. #FIXME is this correct?
            on_disconnect (Callable[[], CoroutineType[Any, Any, None]] | None): Optional callback to be invoked when the connection is lost.
        Returns:
            ClientConnectionHandler: The created client connection handler.
        """
        return AsyncTCPClientConnectionHandler(my_self, reader, writer, endpoint, on_disconnect)
