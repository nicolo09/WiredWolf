import abc
from dataclasses import dataclass
import uuid
from wiredwolf.controller.commons import Peer
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    # Avoid circular imports for type checking
    from wiredwolf.controller.lobbies import Lobby 
from wiredwolf.model.game import GameStatus
from wiredwolf.model.game_phases import GamePhase, GamePhaseOutcome

@dataclass
class BaseMessage(abc.ABC):
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


class LobbyUpdatedMessage(BaseMessage):
    """A message sent by the server to all peers when the lobby information is updated"""

    def __init__(self, lobby: "Lobby"):
        super().__init__(None)
        self._lobby = lobby

    @property
    def lobby(self) -> "Lobby":
        """Gets the updated lobby information.
        Returns:
            Lobby: The updated lobby information.
        """
        return self._lobby


class ChatMessage(BaseMessage):
    """Represents a chat message sent by a peer."""

    def __init__(self, sender: Peer, message: str, game_phase: GamePhase | None):
        super().__init__(sender)
        self._message: str = message
        self._game_phase: GamePhase | None = game_phase

    @property
    def message(self) -> str:
        """Gets the chat message.
        Returns:
            str: The chat message.
        """
        return self._message

    @property
    def game_phase(self) -> GamePhase | None:
        """Gets the game phase to which the chat message belongs.
        Returns:
            GamePhase | None: The game phase to which the chat message belongs.
        """
        return self._game_phase


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

    def __init__(self, outcome: GamePhaseOutcome, game_status: GameStatus):
        super().__init__(None)
        self._outcome = outcome
        self._game_status = game_status

    @property
    def outcome(self) -> GamePhaseOutcome:
        """Gets the outcome of the game phase advancement.
        Returns:
            GamePhaseOutcome: The outcome of the game phase advancement.
        """
        return self._outcome
    
    @property
    def game_status(self) -> GameStatus:
        """Gets the updated game status after the phase advancement.
        Returns:
            GameStatus: The updated game status after the phase advancement.
        """
        return self._game_status


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

    def __init__(self, uuid: str, sender: Peer | None, info: str, result: Any = None):
        super().__init__(sender)
        self._id = uuid
        self._info = info
        self._result = result

    @property
    def info(self) -> str:
        """Gets the info message.
        Returns:
            str: The info message.
        """
        return self._info

    @property
    def result(self) -> Any:
        """Gets the result of the acknowledged action.
        Returns:
            Any: The result of the acknowledged action.
        """
        return self._result


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


class ConnectionClosedMessage(BaseMessage):
    """A message sent to indicate that the connection has been closed"""

    def __init__(self, info: str):
        super().__init__(None)
        self._info = info

    @property
    def info(self) -> str:
        """Gets the info message about the connection closure.
        Returns:
            str: The info message about the connection closure.
        """
        return self._info
    
class HeartbeatMessage(BaseMessage):
    """A message sent to indicate that the connection is still active"""

    def __init__(self):
        super().__init__(None)

class RecoveredConnectionsMessage(BaseMessage):
    """A message sent to indicate how many connections a peer has recovered after a disconnection"""

    def __init__(self, sender: Peer | None, connections: int):
        super().__init__(sender)
        self._connections = connections

    @property
    def connections(self) -> int:
        """Gets the number of connections recovered.
        Returns:
            int: The number of connections recovered.
        """
        return self._connections
    
class CandidateForElectionMessage(BaseMessage):
    """A message sent to indicate that a peer is a candidate for election"""

    def __init__(self, sender: Peer | None):
        super().__init__(sender)

class ApproveCandidateMessage(BaseMessage):
    """A message sent to indicate that a peer approves a candidate for election"""

    def __init__(self, sender: Peer | None):
        super().__init__(sender)
        
class MasterElectedMessage(BaseMessage):
    """A message sent to indicate that a new master has been elected"""

    def __init__(self, sender: Peer | None, new_master: Peer | None):
        super().__init__(sender)
        self._new_master = new_master

    @property
    def new_master(self) -> Peer | None:
        """Gets the new master peer.
        Returns:
            Peer | None: The new master peer.
        """
        return self._new_master
    
class ElectionFailedMessage(BaseMessage):
    """A message sent to indicate that the peer didn't become the new master"""

    def __init__(self, sender: Peer | None):
        super().__init__(sender)
