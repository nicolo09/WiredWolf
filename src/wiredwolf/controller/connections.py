from abc import ABC


class BaseConnectionHandler(ABC):

    def __init__(self):
        pass

    def serialize(self, data):
        # TODO: Implement serialization logic
        pass

    def deserialize(self, data):
        # TODO: Implement deserialization logic
        pass


class ServerConnectionHandler(BaseConnectionHandler):

    __socket = None

    def __init__(self, socket):
        self.__socket = socket


class ClientConnectionHandler(BaseConnectionHandler):

    __socket = None

    def __init__(self, socket):
        self.__socket = socket
