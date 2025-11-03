from wiredwolf.controller.messages import AcknowledgeMessage, BaseMessage, ChatMessage, NightActionMessage, StartGameMessage, VoteBallotMessage, VotePlayerMessage
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
            await server.start_game()
        return False
        

class VotingPlugin(ServerPlugin):
    """A server plugin that handles voting functionality in the game server.
    A plugin should not be added to multiple servers.
    """
    def __init__(self):
        super().__init__([VotePlayerMessage, VoteBallotMessage])

    async def handle_message_sub(self, message: BaseMessage, server: GameServer) -> bool:
        if message.sender is None:
            raise ValueError("Message sender cannot be None.")
        if not server.game:
            raise RuntimeError("Game has not started yet.")
        match message:
            case VotePlayerMessage():
                try:
                    server.game.accuse_player(message.sender.uuid, message.voted_player_uuid)
                    await server.connection_handler.send_obj(
                        message.sender,
                        AcknowledgeMessage(message.sender, "Vote registered successfully.")
                    )
                    return True
                except Exception as e:
                    self._logger.error("Error handling vote: %s", e)
                    await server.connection_handler.send_obj(
                        message.sender,
                        e
                    )
                    return True
            case VoteBallotMessage():
                try:
                    server.game.ballot_vote(message.sender.uuid, message.vote)
                    await server.connection_handler.send_obj(
                        message.sender,
                        AcknowledgeMessage(message.sender, "Ballot cast successfully.")
                    )
                    return True
                except Exception as e:
                    self._logger.error("Error handling ballot vote: %s", e)
                    await server.connection_handler.send_obj(
                        message.sender,
                        e
                    )
                    return True
            case _:
                raise ValueError(f"Unhandled message type: {type(message)}")


class NightActionsPlugin(ServerPlugin):
    """A server plugin that handles night actions in the game server.
    A plugin should not be added to multiple servers.
    """
    def __init__(self):
        super().__init__([NightActionMessage])

    async def handle_message_sub(self, message: BaseMessage, server: GameServer) -> bool:
        if message.sender is None:
            raise ValueError("Message sender cannot be None.")
        if not server.game:
            raise RuntimeError("Game has not started yet.")
        if isinstance(message, NightActionMessage):
            try:
                result = server.game.perform_night_action(message.sender.uuid, message.target_player_uuid)
                await server.connection_handler.send_obj(
                    message.sender,
                    AcknowledgeMessage(message.sender, result.message)
                )
                return True
            except Exception as e:
                self._logger.error("Error handling night action: %s", e)
                await server.connection_handler.send_obj(
                    message.sender,
                    e
                )
                return True
        return False
        