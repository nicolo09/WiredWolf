from dataclasses import dataclass, field
import random
import string
import uuid

DEFAULT_SERVER_HOST = "0.0.0.0"
DEFAULT_SERVER_PORT = 12233
CONNECTION_TIMEOUT = 100  # seconds

FIRST_DAY_PHASE_DURATION_SECONDS = 10
BALLOT_RESULT_PHASE_DURATION_SECONDS = 20
PHASE_DURATION_SECONDS = 60
ACK_TIMEOUT_SECONDS = 10  # seconds
RECEIVING_TASK_CLOSE_TIMEOUT = 3  # seconds
ERROR_PAUSE_TIME = 5  # seconds

MIN_PLAYERS = 8
MAX_PLAYERS = 32
PLAYERS_TO_ADD_MEDIUM = 9
PLAYERS_TO_ADD_ESCORT = 16


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