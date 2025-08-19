class Peer:
    """Represents a peer in the network."""

    __name = None
    __address = None

    def __init__(self, name: str, address: str):
        self.__name = name
        self.__address = address

    @property
    def address(self):
        return self.__address

    @property
    def name(self):
        return self.__name
