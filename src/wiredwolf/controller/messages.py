import abc
from wiredwolf.controller.commons import Peer


class BaseMessage(abc.ABC):  # TODO: Move to wiredwolf.controller.messages
    """Abstract base class for messages exchanged between peers."""

    def __init__(self, sender: Peer):
        self._sender: Peer = sender

    @property
    def sender(self) -> Peer:
        """Gets the sender of the chat message.
        Returns:
            Peer: The sender of the chat message.
        """
        return self._sender

    pass


class ChatMessage(BaseMessage):  # TODO: Move to wiredwolf.controller.messages
    """Represents a chat message sent by a peer."""

    def __init__(self, sender: Peer, message: str):
        super().__init__(sender)
        self._message: str = message

    @property
    def message(self) -> str:
        """Gets the chat message.
        Returns:
            str: The chat message.
        """
        return self._message


class StartGameMessage(BaseMessage):
    """A message sent by a lobby owner to the server to start the game"""

    def __init__(self, sender: Peer):
        super().__init__(sender)
