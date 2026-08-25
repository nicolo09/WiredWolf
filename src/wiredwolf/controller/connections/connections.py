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
    NewPeerMessage,
    NotAcknowledgeMessage,
    RemovedPeerMessage,
)
import asyncio
from asyncio import CancelledError

PEERNAME_EXTRA_INFO = "peername"
HEARTBEAT_INTERVAL = 5  # seconds
CONNECTION_TIMEOUT_HEARTBEAT = 10  # seconds
MAX_RECONNECT_TIMEOUT = 10  # seconds


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

    def set_on_disconnect(
        self, on_disconnect: Callable[[], CoroutineType[Any, Any, None]]
    ) -> None:
        """Set the callback function to handle disconnection events.

        Args:
            on_disconnect (Callable[[], CoroutineType[Any, Any, None]]): The callback function.
        """
        self._on_disconnect = on_disconnect

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
        self,
        my_self: Peer,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        endpoint: tuple[str, int],
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
        self._other_peers: dict[Peer, str] = {}  # Dictionary to store other peers and their addresses
        self._receiving_task: asyncio.Task[None] | None = None
        self._on_disconnect: Callable[[], CoroutineType[Any, Any, None]] | None = None

    @property
    def endpoint(self) -> tuple[str, int]:
        """Get the endpoint (host, port) of the server this client is connected to.

        Returns:
            tuple[str, int]: The endpoint of the server.
        """
        return self._endpoint
    
    @property
    def other_peers(self) -> dict[Peer, str]:
        """Get the dictionary of other known peers and their addresses.

        Returns:
            dict[Peer, str]: The dictionary of other known peers and their addresses.
        """
        return self._other_peers

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
                if exc is None:
                    # No exception or graceful connection closed
                    self._logger.info("Receive loop task completed successfully.")
                elif isinstance(exc, ConnectionClosedError) or isinstance(
                    exc, TimeoutError
                ):
                    self._logger.warning(
                        "Receive loop task timed out or connection closed. Connection may be lost."
                    )
                else:
                    self._logger.error(
                        "Receive loop task encountered an error: %s", exc
                    )
            except asyncio.CancelledError:
                self._logger.info("Receive loop task was cancelled.")
                return
            except Exception as e:
                self._logger.error(
                    "Error while retrieving receive loop task during close: %s", e
                )
                return
            if self._on_disconnect:
                asyncio.create_task(self._on_disconnect())

    async def _receive_loop(self) -> None:
        """Internal method to continuously receive messages."""
        while True:
            try:
                async with asyncio.timeout(CONNECTION_TIMEOUT_HEARTBEAT):
                    msg: Any = await self._message_handler.receive_obj(self._reader)
                    if isinstance(msg, NewPeerMessage):
                        self._other_peers[msg.new_peer] = msg.address
                    elif isinstance(msg, RemovedPeerMessage):
                        self._other_peers.pop(msg.removed_peer, None)
                    elif self._on_message:
                        self._on_message(msg)
                    else:
                        self._logger.warning(
                            "Received message but no on_message callback is set."
                        )
            except asyncio.CancelledError:
                self._logger.info("Receive loop cancelled.")
                return
            except TimeoutError as e:
                # Connection timed out, no heartbeat received in time
                self._logger.error("Receive loop timed out.")
                raise e
            except Exception as e:
                # Error receiving message
                self._logger.error("Error receiving message: %s", e)
                raise e

    async def close(self) -> None:
        """Closes the client connection handler."""
        try:
            # Close the writer to the server first, the server will close its writer from its side
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
        on_peer_recovery: Callable[[Peer], CoroutineType[Any, Any, None]],
        owner_connection: (
            tuple[Peer, asyncio.StreamReader, asyncio.StreamWriter] | None
        ) = None,
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
        self._on_peer_recovery: Callable[[Peer], CoroutineType[Any, Any, None]] = (
            on_peer_recovery
        )
        self._async_message_handler = AsyncTCPMessageHandler(
            MessageHandlerFactory.getDefaultSerializer()
        )
        self._endpoints: dict[
            Peer, tuple[asyncio.StreamReader, asyncio.StreamWriter]
        ] = {}
        self._client_addresses: dict[Peer, str] = {}
        self._status: dict[Peer, ConnectionStatus] = {}
        self._receiving_tasks: dict[Peer, asyncio.Task[None]] = {}
        self._server: asyncio.Server | None = None
        self._server_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._reconnect_timeout_task: asyncio.Task[None] | None = None
        if owner_connection is not None:
            peer, reader, writer = owner_connection
            self._endpoints[peer] = (reader, writer)
            self._status[peer] = ConnectionStatus.CONNECTED
            self._receiving_tasks[peer] = asyncio.create_task(
                self._handle_peer_message(peer)
            )
        self._heartbeat_task = asyncio.create_task(self._send_heartbeat())

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

    async def _send_heartbeat(self):
        """A function that sends a heartbeat message to all connected peers regularly"""
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            for peer in list(self._endpoints.keys()):
                try:
                    await self.send_obj(peer, HeartbeatMessage())
                except Exception as e:
                    if self._status.get(peer) == ConnectionStatus.CONNECTED:
                        self._logger.error("Error sending heartbeat to %s: %s", peer, e)
                        await self._on_peer_error(peer)

    async def _on_peer_error(self, peer: Peer) -> None:
        """Handles errors with a peer connection.

        Args:
            peer (Peer): The peer with the error.
        """
        self._status[peer] = ConnectionStatus.RECOVERING
        try:
            if not self._server:
                # Start a new server for recovery connections
                self._server = await asyncio.start_server(
                    self._client_recovery_cb,
                    host=self._bind_address[0],
                    port=self._bind_address[1],
                )
                self._logger.info(
                    "Server started listening for new connections on %s:%d",
                    self._bind_address[0],
                    self._bind_address[1],
                )
                self._server_task = asyncio.create_task(self._server.serve_forever())
            # If a reconnect timeout task is already running, cancel it and start a new one
            # This ensures that the server will only close after the last peer has had a chance to reconnect
            if self._reconnect_timeout_task:
                self._reconnect_timeout_task.cancel()
            self._reconnect_timeout_task = asyncio.create_task(
                self._wait_and_close_server(MAX_RECONNECT_TIMEOUT)
            )
        except Exception:
            # If an error occurs the peer is considered disconnected and the server will not wait for it to reconnect
            self._endpoints.pop(peer, None)
            self._status.pop(peer, None)
            #FIXME: does this make sense?
            receiving_task = self._receiving_tasks.pop(peer, None)
            if receiving_task is not None and not receiving_task.done():
                receiving_task.cancel()
            await self._on_peer_disconnected(peer)
            # Inform other peers about the disconnection
            for other_peer in self._client_addresses.keys():
                await self.send_obj(other_peer, RemovedPeerMessage(peer))
            self._client_addresses.pop(peer, None)
            
    async def _wait_and_close_server(self, timeout: float):
        """Waits for a specified timeout and then closes the server if it's still running.

        Args:
            timeout (float): The time in seconds to wait before closing the server.
        """
        await asyncio.sleep(timeout)
        if self._server:
            self._logger.info(
                "Closing server after waiting for %s seconds.", timeout
            )
            self.stop_new_connections()
            disconnected_peers: list[Peer] = []
            for peer, status in list(self._status.items()):
                if status == ConnectionStatus.RECOVERING:
                    self._logger.info(
                        "Peer %s is still in recovering state after timeout.", peer
                    )
                    await self._on_peer_disconnected(peer)
                    disconnected_peers.append(peer)
            for peer in disconnected_peers:
                self._status.pop(peer, None)
                self._endpoints.pop(peer, None)
                receiving_task = self._receiving_tasks.pop(peer, None)
                if receiving_task is not None and not receiving_task.done():
                    receiving_task.cancel()
                # Inform other peers about the disconnection
                for other_peer in self._client_addresses.keys():
                    await self.send_obj(other_peer, RemovedPeerMessage(peer))
                self._client_addresses.pop(peer, None)
        
    async def _client_recovery_cb(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        """
        Callback for handling incoming recovery connections attempts from peers.
        
        Args:
            reader (asyncio.StreamReader): The stream reader for the connection.
            writer (asyncio.StreamWriter): The stream writer for the connection.
        """
        client_address = writer.get_extra_info(PEERNAME_EXTRA_INFO)
        self._logger.info("Accepted connection from %s", client_address)
        async with asyncio.timeout(CONNECTION_TIMEOUT):
            try:
                # First thing peer sends is their identification (serialized peer object)
                peer: Peer = await self._async_message_handler.receive_obj(
                    reader
                )
                if peer in self._status and self._status[peer] == ConnectionStatus.RECOVERING:
                    # Peer has successfully reconnected, update its status and start receiving messages
                    old_task = self._receiving_tasks.pop(peer, None)
                    if old_task is not None and not old_task.done():
                        old_task.cancel()
                    self._endpoints[peer] = (reader, writer)
                    await self._on_peer_recovery(peer)
                    self._status[peer] = ConnectionStatus.CONNECTED
                    self._receiving_tasks[peer] = asyncio.create_task(
                        self._handle_peer_message(peer)
                    )
                else:
                    self._logger.warning(
                        "Received recovery connection from %s, but peer is not in recovering state.",
                        peer,
                    )
                    writer.close()
                    await writer.wait_closed()
                    return                
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
            finally:
                if ConnectionStatus.RECOVERING not in self._status.values():
                    if self._reconnect_timeout_task and not self._reconnect_timeout_task.done():
                        self._reconnect_timeout_task.cancel()
                    self._reconnect_timeout_task = None
                    # If no more peers are in recovering state, stop the server from accepting new connections
                    self.stop_new_connections()
        

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
                self._client_addresses[peer] = client_address
                self._endpoints[peer] = (reader, writer)
                self._status[peer] = ConnectionStatus.CONNECTING
                await self._on_new_peer(peer)
                # Successful connection
                self._logger.info("New peer connected: %s", peer)
                self._status[peer] = ConnectionStatus.CONNECTED
                self._receiving_tasks[peer] = asyncio.create_task(
                    self._handle_peer_message(peer)
                )
                for other_peer in self._client_addresses.keys():
                    if other_peer != peer:
                        # Update all other clients about the new peer
                        await self.send_obj(
                            other_peer, NewPeerMessage(peer, client_address)
                        )
                        # Update the new peer about all other connected peers
                        await self.send_obj(
                            peer, NewPeerMessage(other_peer, self._client_addresses[other_peer])
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
                await self._on_peer_error(peer)
                return
            except Exception as e:
                self._logger.error("Error receiving message from %s: %s", peer, e)
                await self._on_peer_error(peer)
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

            if self._heartbeat_task:
                self._heartbeat_task.cancel()

            if self._reconnect_timeout_task:
                self._reconnect_timeout_task.cancel()

            # Clear internal state
            self._endpoints.clear()
            self._status.clear()
            self._receiving_tasks.clear()
            self._server = None
            self._server_task = None
            self._heartbeat_task = None
            self._reconnect_timeout_task = None
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
        on_peer_recovery: Callable[[Peer], CoroutineType[Any, Any, None]],
        owner_connection: (
            tuple[Peer, asyncio.StreamReader, asyncio.StreamWriter] | None
        ) = None,
    ) -> ServerConnectionHandler:
        """Creates and returns a new ServerConnectionHandler.

        Args:
            bind_address (tuple[str | None, int]): The address to bind the server to.
            on_new_peer (Callable[[Peer], CoroutineType[Any, Any, None]]): The callback for new peer connections.
            on_peer_disconnected (Callable[[Peer], CoroutineType[Any, Any, None]]): The callback for peer disconnections.
            on_new_message (Callable[[BaseMessage], CoroutineType[Any, Any, None]]): The callback for new messages.
            on_peer_recovery (Callable[[Peer], CoroutineType[Any, Any, None]]): The callback for peer recovery.

        Returns:
            ServerConnectionHandler: The created server connection handler.
        """
        return AsyncTCPServerConnectionHandler(
            bind_address=bind_address,
            on_new_peer=on_new_peer,
            on_peer_disconnected=on_peer_disconnected,
            on_new_message=on_new_message,
            on_peer_recovery=on_peer_recovery,
            owner_connection=owner_connection,
        )

    @staticmethod
    def get_client_connection_handler(
        my_self: Peer,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        endpoint: tuple[str, int],
    ) -> ClientConnectionHandler:
        """Creates and returns a new ClientConnectionHandler.

        Args:
            my_self (Peer): The peer representing this client.
            reader (asyncio.StreamReader): The reader for the connection.
            writer (asyncio.StreamWriter): The writer for the connection.
            endpoint (tuple[str, int]): The (IP, port) endpoint of the server to connect to.
        Returns:
            ClientConnectionHandler: The created client connection handler.
        """
        return AsyncTCPClientConnectionHandler(my_self, reader, writer, endpoint)
