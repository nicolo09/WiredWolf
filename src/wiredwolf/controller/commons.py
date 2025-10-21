from dataclasses import dataclass
import uuid


class Peer:
    """Represents a peer in the network."""

    _name: str
    _uuid: str

    def __init__(self, name: str, peer_id: str | None = None):
        self._name = name
        self._uuid = peer_id or str(uuid.uuid4())

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Peer):
            return NotImplemented
        return self._name == value._name and self._uuid == value._uuid

    def __hash__(self) -> int:
        return hash((self._name, self._uuid))

    @property
    def uuid(self):
        return self._uuid

    @property
    def name(self):
        return self._name


@dataclass
class PasswordRequest:
    """Represents a password request message."""

    password: str | None = None
    id: str = str(uuid.uuid4())
