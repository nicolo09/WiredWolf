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

    @property
    def uuid(self):
        return self._uuid

    @property
    def address(self):
        return self._address

    @property
    def name(self):
        return self._name
