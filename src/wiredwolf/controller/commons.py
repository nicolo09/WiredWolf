from dataclasses import dataclass, field
import random
import string
import uuid

DEFAULT_SERVER_HOST = "0.0.0.0" # Default host to bind the server to
DEFAULT_SERVER_PORT = 12233 # Default port to bind the server to
CONNECTION_TIMEOUT = 100  # seconds #TODO Should this be merged with the TIMEOUT variable in __init__.py?


FIRST_DAY_PHASE_DURATION_SECONDS = 10 # Duration of the first day phase, in seconds
BALLOT_RESULT_PHASE_DURATION_SECONDS = 20 # Duration of the ballot result (show if spared or executed) phase, in seconds
PHASE_DURATION_SECONDS = 60 # Duration of each phase after the first day phase, in seconds
ACK_TIMEOUT_SECONDS = 10  # Timeout to wait for an acknowledgment from the server, in seconds #TODO Should this be merged with the TIMEOUT variable in __init__.py?
RECEIVING_TASK_CLOSE_TIMEOUT = 3  # Timeout to wait for the receiving task of the connection handlers to close, in seconds
ERROR_PAUSE_TIME = 5  # Time to wait after an error occurs and is shown, in seconds #TODO: This should probably be view logic


MIN_PLAYERS = 8 # Minimum number of players required to start a game
MAX_PLAYERS = 32 # Maximum number of players allowed in a game
PLAYERS_TO_ADD_MEDIUM = 9 # Number of players to add the medium role
PLAYERS_TO_ADD_ESCORT = 16 # Number of players to add the escort role


@dataclass(frozen=True)
class Peer:
    """Represents a peer in the network."""

    name: str
    uuid: str = field(default_factory=lambda: str(uuid.uuid4())) #TODO: Possible UUID collision will have to be handled in server code


@dataclass(frozen=False)
class PasswordRequest:
    """Represents a password request sent by the server to a client who wants to join a lobby."""

    password: str | None = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

def id_generator(size: int = 15, chars: str = string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))