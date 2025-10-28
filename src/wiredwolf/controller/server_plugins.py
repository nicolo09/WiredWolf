from wiredwolf.controller.messages import BaseMessage, ChatMessage
from wiredwolf.controller.server import ServerPlugin

class ChatPlugin(ServerPlugin):
    
    """A server plugin that adds chat functionality to the game server.
    A plugin should not be added to multiple servers.
    """
    def __init__(self):
        super().__init__([ChatMessage])
        
    async def handle_message(self, message: BaseMessage) -> bool:
        await super().handle_message(message)
        if not self.server:
            raise RuntimeError("Plugin is not attached to any server.")
        if isinstance(message, ChatMessage):
            await self.server.send_to_all(message)
            return True
        else:
            raise ValueError(f"Unhandled message type: {type(message)}")
