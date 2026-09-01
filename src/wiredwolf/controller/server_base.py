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
    async def process_incoming_message(self, message: BaseMessage):
        """Handles a message coming from a peer.

        Args:
            message (BaseMessage): The message to handle.
        """

    @property
    @abc.abstractmethod
    async def should_recover_connections(self) -> bool:
        """Indicates whether the connection handler this server uses should attempt to recover lost connections."""
