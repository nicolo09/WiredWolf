from wiredwolf.controller.messages import BaseMessage, ChatMessage
from wiredwolf.controller.server import ServerPlugin

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
