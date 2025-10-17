import abc

from wiredwolf.controller.messages import BaseMessage, ChatMessage
from wiredwolf.controller.server import GameServer


class ServerPlugin(abc.ABC):
    """Abstract base class for server pieces that adds common functionalities.
    A plugin should not be added to multiple servers.
    """
    
    _server: GameServer
    _handled_messages: list[type]

    @property
    def server(self) -> GameServer:
        return self._server
    
    @server.setter
    def server(self, server: GameServer):
        self._server = server
        
    @property
    def handled_messages(self) -> list[type]:
        return self._handled_messages
    
    @abc.abstractmethod
    def handle_message(self, message: BaseMessage) -> bool:
        """Handles received messages, subclasses should implement this method but call super().handle_message().

        Args:
            message (BaseMessage): The message to handle.

        Raises:
            ValueError: If the message type is not handled by this plugin.

        Returns:
            bool: True if the message should not be passed to other handlers, False otherwise.
        """
        if not type(message) in self._handled_messages:
            raise ValueError(f"Message of type {type(message)} not handled by this plugin.")
        # To be implemented by subclasses


class ChatPlugin(ServerPlugin):
    
    """A server plugin that adds chat functionality to the game server.
    A plugin should not be added to multiple servers.
    """
    def __init__(self):
        self._handled_messages = [ChatMessage]
        
    def handle_message(self, message: BaseMessage) -> bool:
        super().handle_message(message)
        if isinstance(message, ChatMessage):
            self.server.send_to_all(message)
            return True
        else:
            raise ValueError(f"Unhandled message type: {type(message)}")
