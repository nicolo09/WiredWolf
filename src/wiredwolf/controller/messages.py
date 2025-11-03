import abc
from wiredwolf.controller.commons import Peer
from wiredwolf.model.game import GameStatus
from wiredwolf.model.game_phases import GamePhaseOutcome


class BaseMessage(abc.ABC):  # TODO: Move to wiredwolf.controller.messages
    """Abstract base class for messages exchanged between peers."""

    def __init__(self, sender: Peer | None):
        self._sender: Peer | None = sender

    @property
    def sender(self) -> Peer | None:
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


class GameStartedMessage(BaseMessage):
    """A message sent by the server to all peers when the game has started"""

    def __init__(self, status: GameStatus):
        super().__init__(None)
        self._status = status

    @property
    def status(self) -> GameStatus:
        """Gets the status of the started game.
        Returns:
            GameStatus: The status of the started game.
        """
        return self._status
    
class PhaseAdvanceMessage(BaseMessage):
    """A message sent by the server to all peers when the game phase has advanced"""

    def __init__(self, outcome: GamePhaseOutcome):
        super().__init__(None)
        self._outcome = outcome

    @property
    def outcome(self) -> GamePhaseOutcome:
        """Gets the outcome of the game phase advancement.
        Returns:
            GamePhaseOutcome: The outcome of the game phase advancement.
        """
        return self._outcome
