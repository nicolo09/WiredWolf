from wiredwolf.controller.messages import BaseMessage, ChatMessage, StartGameMessage
from wiredwolf.controller.server import GameServer, ServerPlugin

class ChatPlugin(ServerPlugin):
    
    """A server plugin that adds chat functionality to the game server.
    A plugin should not be added to multiple servers.
    """
    def __init__(self):
        super().__init__([ChatMessage])
        
    async def handle_message_sub(self, message: BaseMessage, server: GameServer) -> bool:
        if isinstance(message, ChatMessage):
            await server.send_to_all(message)
            return True
        else:
            raise ValueError(f"Unhandled message type: {type(message)}")

class GameLifecyclePlugin(ServerPlugin):
    """A server plugin that handles the game lifecycle
    """

    def __init__(self) -> None:
        super().__init__([StartGameMessage])

    async def handle_message_sub(self, message: BaseMessage, server: GameServer) -> bool:
        if isinstance(message, StartGameMessage):
            if message.sender != server.lobby.owner:
                raise PermissionError("Only the lobby owner can start the game.")
            server.start_game()
        return False
        
