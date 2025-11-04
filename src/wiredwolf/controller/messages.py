import abc
import uuid
from wiredwolf.controller.commons import Peer
from wiredwolf.model.game import GameStatus
from wiredwolf.model.game_phases import GamePhaseOutcome


class BaseMessage(abc.ABC):  # TODO: Move to wiredwolf.controller.messages
    """Abstract base class for messages exchanged between peers."""

    def __init__(self, sender: Peer | None):
        self._sender: Peer | None = sender
        self._id: str = uuid.uuid4().hex

    @property
    def sender(self) -> Peer | None:
        """Gets the sender of the chat message.
        Returns:
            Peer: The sender of the chat message.
        """
        return self._sender

    @property
    def id(self) -> str:
        """Gets the unique identifier of the message.
        Returns:
            str: The unique identifier of the message.
        """
        return self._id


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


class VotePlayerMessage(BaseMessage):
    """A message sent by a peer to vote for another player"""

    def __init__(self, sender: Peer | None, voted_player_uuid: str):
        super().__init__(sender)
        self._voted_player_uuid = voted_player_uuid

    @property
    def voted_player_uuid(self) -> str:
        """Gets the UUID of the player being voted for.
        Returns:
            str: The UUID of the player being voted for.
        """
        return self._voted_player_uuid


class VoteBallotMessage(BaseMessage):
    """A message sent by a peer to cast their ballot vote"""

    def __init__(self, sender: Peer | None, vote: bool):
        super().__init__(sender)
        self._vote = vote

    @property
    def vote(self) -> bool:
        """Gets the vote.
        Returns:
            bool: The vote.
        """
        return self._vote


class AcknowledgeMessage(BaseMessage):
    """A message sent to confirm that something was successful"""

    def __init__(self, uuid: str, sender: Peer | None, info: str):
        super().__init__(sender)
        self._id = uuid
        self._info = info

    @property
    def info(self) -> str:
        """Gets the info message.
        Returns:
            str: The info message.
        """
        return self._info


class NotAcknowledgeMessage(BaseMessage):
    """A message sent to indicate that something failed"""

    def __init__(self, uuid: str, sender: Peer | None, error: Exception):
        super().__init__(sender)
        self._id = uuid
        self._error = error

    @property
    def error(self) -> Exception:
        """Gets the error.
        Returns:
            str: The error message.
        """
        return self._error


class NightActionMessage(BaseMessage):
    """A message sent by a peer to perform a night action"""

    def __init__(self, sender: Peer | None, target_player_uuid: str):
        super().__init__(sender)
        self._target_player_uuid = target_player_uuid

    @property
    def target_player_uuid(self) -> str:
        """Gets the UUID of the target player.
        Returns:
            str: The UUID of the target player.
        """
        return self._target_player_uuid
