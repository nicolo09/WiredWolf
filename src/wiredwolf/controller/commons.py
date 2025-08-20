class Peer:
    """Represents a peer in the network."""

    _name: str
    _address: str

    def __init__(self, name: str, address: str):
        self._name = name
        self._address = address

    @property
    def address(self):
        return self._address

    @property
    def name(self):
        return self._name
