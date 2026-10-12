import abc
from asyncio import Future

from wiredwolf.controller import commons
from wiredwolf.controller.messages import BaseMessage


class Server(abc.ABC):
    """Abstract base class for a server."""

    @abc.abstractmethod
    async def _on_new_peer(self, peer: commons.Peer):
        """Called when a new peer connects to the server."""

    @abc.abstractmethod
    async def _on_peer_disconnected(self, peer: commons.Peer):
        """Called when a peer disconnects from the server."""

    @abc.abstractmethod
    async def _on_peer_error(
        self, peer: commons.Peer, outcome: Future[commons.ReconnectedOutcome]
    ):
        """Called when a peer encounters an error.

        Args:
            peer (commons.Peer): The peer that encountered an error.
            outcome (Future[commons.ReconnectedOutcome]): The future that will be completed when the peer either reconnects or fails to reconnect.
        """
        
    @abc.abstractmethod
    async def start_listening(self):
        """Starts the server and begins listening for incoming connections."""

    @abc.abstractmethod
    def stop_new_connections(self):
        """Stops the server from accepting new connections."""

    @abc.abstractmethod
    async def process_incoming_message(self, message: BaseMessage):
        """Handles a message coming from a peer.

        Args:
            message (BaseMessage): The message to handle.
        """
    
    @abc.abstractmethod
    async def send_to_peer(self, peer: commons.Peer, message: BaseMessage):
        """Sends a message to a specific peer.

        Args:
            peer (commons.Peer): The peer to send the message to.
            message (BaseMessage): The message to send.
        """
        
    @abc.abstractmethod
    async def close(self):
        """Closes the server and all active connections."""

    @property
    @abc.abstractmethod
    async def should_recover_connections(self) -> bool:
        """Indicates whether the connection handler this server uses should attempt to recover lost connections."""
