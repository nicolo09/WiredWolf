from wiredwolf.controller.messages import (
    AcknowledgeMessage,
    BaseMessage,
    ChatMessage,
    NightActionMessage,
    NotAcknowledgeMessage,
    StartGameMessage,
    VoteBallotMessage,
    VotePlayerMessage,
)
from wiredwolf.controller.server import GameServer, ServerPlugin
from wiredwolf.model.game_phases import GamePhase


class ChatPlugin(ServerPlugin):
    """A server plugin that adds chat functionality to the game server.
    A plugin should not be added to multiple servers.
    """

    def __init__(self):
        super().__init__([ChatMessage])

    async def handle_message_sub(
        self, message: BaseMessage, server: GameServer
    ) -> tuple[AcknowledgeMessage | NotAcknowledgeMessage, bool]:
        if isinstance(message, ChatMessage):
            await server.send_to_all(message)
            return AcknowledgeMessage(message.id, message.sender, "Message sent to all players."), True
        else:
            raise ValueError(f"Unhandled message type: {type(message)}")


class GameLifecyclePlugin(ServerPlugin):
    """A server plugin that handles the game lifecycle"""

    def __init__(self) -> None:
        super().__init__([StartGameMessage])

    async def handle_message_sub(
        self, message: BaseMessage, server: GameServer
    ) -> tuple[AcknowledgeMessage | NotAcknowledgeMessage, bool]:
        if isinstance(message, StartGameMessage):
            if message.sender != server.lobby.owner:
                return NotAcknowledgeMessage(message.id, message.sender, PermissionError("Only the lobby owner can start the game.")), True
            await server.start_game()
        return AcknowledgeMessage(message.id, message.sender, "Game started successfully."), True


class VotingPlugin(ServerPlugin):
    """A server plugin that handles voting functionality in the game server.
    A plugin should not be added to multiple servers.
    """

    def __init__(self):
        super().__init__([VotePlayerMessage, VoteBallotMessage])

    async def handle_message_sub(
        self, message: BaseMessage, server: GameServer
    ) -> tuple[AcknowledgeMessage | NotAcknowledgeMessage, bool]:
        if message.sender is None:
            raise ValueError("Message sender cannot be None.")
        if not server.game:
            raise RuntimeError("Game has not started yet.")
        match message:
            case VotePlayerMessage():
                try:
                    action_result = None
                    match server.game.phase:
                        #TODO: This should be 2 different message types, because a message might be sent during day and arrive during night 
                        case GamePhase.DAY_ACCUSING:
                            server.game.accuse_player(
                            message.sender.uuid, message.voted_player_uuid
                        )
                        case GamePhase.NIGHT:
                            action_result = server.game.perform_night_action(
                                message.sender.uuid, message.voted_player_uuid
                            )
                    await server.connection_handler.send_obj(
                            message.sender,
                            AcknowledgeMessage(
                                message.id, message.sender, "Vote registered successfully.", action_result
                            ),
                        )    
                    return AcknowledgeMessage(message.id, message.sender, "Vote registered successfully.", action_result), True
                except Exception as e:
                    self._logger.error("Error handling vote: %s", e)
                    return NotAcknowledgeMessage(message.id, message.sender, e), True
            case VoteBallotMessage():
                try:
                    server.game.ballot_vote(message.sender.uuid, message.vote)
                    return AcknowledgeMessage(message.id, message.sender, "Ballot cast successfully."), True
                except Exception as e:
                    self._logger.error("Error handling ballot vote: %s", e)
                    return NotAcknowledgeMessage(message.id, message.sender, e), True
            case _:
                raise ValueError(f"Unhandled message type: {type(message)}")


class NightActionsPlugin(ServerPlugin):
    """A server plugin that handles night actions in the game server.
    A plugin should not be added to multiple servers.
    """

    def __init__(self):
        super().__init__([NightActionMessage])

    async def handle_message_sub(
        self, message: BaseMessage, server: GameServer
    ) -> tuple[AcknowledgeMessage | NotAcknowledgeMessage, bool]:
        if message.sender is None:
            raise ValueError("Message sender cannot be None.")
        if not server.game:
            raise RuntimeError("Game has not started yet.")
        if isinstance(message, NightActionMessage):
            try:
                result = server.game.perform_night_action(
                    message.sender.uuid, message.target_player_uuid
                )
                return AcknowledgeMessage(message.id, message.sender, "Night action performed successfully.", result), True
            except Exception as e:
                self._logger.error("Error handling night action: %s", e)
                return NotAcknowledgeMessage(message.id, message.sender, e), True
        else:
            raise ValueError(f"Unhandled message type: {type(message)}")

@staticmethod
async def get_plugins_list() -> list[ServerPlugin]:
    """Returns a list of server plugins.

    Returns:
        list[ServerPlugin]: The list of plugins.
    """
    return [ChatPlugin(), GameLifecyclePlugin(), VotingPlugin(), NightActionsPlugin()]