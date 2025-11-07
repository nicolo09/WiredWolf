from dataclasses import dataclass
import uuid

DEFAULT_SERVER_PORT = 12233
CONNECTION_TIMEOUT = 10  # seconds

FIRST_DAY_PHASE_DURATION_SECONDS = 10
PHASE_DURATION_SECONDS = 60
ACK_TIMEOUT_SECONDS = 10  # seconds
RECEIVING_TASK_CLOSE_TIMEOUT = 3  # seconds

MIN_PLAYERS = 8
MAX_PLAYERS = 32
PLAYERS_TO_ADD_MEDIUM = 9
PLAYERS_TO_ADD_ESCORT = 16


@dataclass(frozen=True)
class Peer:
    """Represents a peer in the network."""

    name: str
    uuid: str = str(uuid.uuid4())


@dataclass(frozen=False)
class PasswordRequest:
    """Represents a password request message."""

    password: str | None = None
    id: str = str(uuid.uuid4())
