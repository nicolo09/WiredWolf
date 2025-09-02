from dataclasses import dataclass
import uuid


class Peer:
    """Represents a peer in the network."""

    _name: str
    _address: str
    _uuid: uuid.UUID

    def __init__(self, name: str, address: str):
        self._name = name
        self._address = address
        self._uuid = uuid.uuid4()
        
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Peer):
            return NotImplemented
        return (self._name == value._name and
                self._address == value._address and
                self._uuid == value._uuid)

    @property
    def uuid(self):
        return self._uuid

    @property
    def address(self):
        return self._address

    @property
    def name(self):
        return self._name


@dataclass
class PasswordRequest:
    """Represents a password request message."""
    password: str | None = None
    id: str = str(uuid.uuid4())