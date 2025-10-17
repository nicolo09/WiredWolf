import abc
from wiredwolf.controller.commons import Peer


class BaseMessage(abc.ABC): #TODO: Move to wiredwolf.controller.messages
    """Abstract base class for messages exchanged between peers.
    """
    pass


class ChatMessage(BaseMessage): #TODO: Move to wiredwolf.controller.messages
    """Represents a chat message sent by a peer.
    """

    _sender: Peer
    _message: str

    def __init__(self, sender: Peer, message: str):
        self._sender = sender
        self._message = message

    @property
    def sender(self) -> Peer:
        """Gets the sender of the chat message.
        Returns:
            Peer: The sender of the chat message.
        """
        return self._sender

    @property
    def message(self) -> str:
        """Gets the chat message.
        Returns:
            str: The chat message.
        """
        return self._message

