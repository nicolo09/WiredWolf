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
from wiredwolf.model.player import BasicRole


class ChatPlugin(ServerPlugin):
    """A server plugin that adds chat functionality to the game server.
    A plugin should not be added to multiple servers.
    """

    def __init__(self):
        super().__init__([ChatMessage])

    async def handle_message_sub(
        self, message: BaseMessage, server: GameServer
    ) -> tuple[AcknowledgeMessage | NotAcknowledgeMessage, bool]:
        #TODO: This should be changed so that at night only certain messages are allowed, and only to certain players. A werewolf should be able to chat with other werewolves at night, but not with villagers.
        if isinstance(message, ChatMessage):
            if message.sender is None:
                # The message sender is None, we cannot process the message
                return NotAcknowledgeMessage(message.id, message.sender, ValueError("Message sender cannot be None.")), True
            if server.game is None and message.game_phase is None:
                # The game has not started yet, we allow all chat messages in the lobby
                await server.send_to_all(message)
            elif server.game is not None and message.game_phase == server.game.phase:
                # The game has started and the message is for the current phase
                sender_player = next((player for player in server.game.players if player.id == message.sender.uuid), None)
                if not sender_player:
                    # The message sender is not a player in the game
                    return NotAcknowledgeMessage(message.id, message.sender, ValueError("Message sender is not a player in the game.")), True
                elif not sender_player.is_alive():
                    # The game is from a player that is not alive
                    dead_players = [player for player in server.game.players if not player.is_alive()]
                    for dead_player in dead_players:
                        await server.send_to_uuid(dead_player.id, message)
                elif message.game_phase == GamePhase.NIGHT:
                    # The message is for the night phase, we only allow werewolves to chat with each other
                    if sender_player.role == BasicRole.WEREWOLF:
                        werewolves = [player for player in server.game.players if player.role == BasicRole.WEREWOLF and player.is_alive()]
                        for werewolf in werewolves:
                            await server.send_to_uuid(werewolf.id, message)
                    else:
                        # The message sender is not a werewolf, they cannot chat at night
                        return NotAcknowledgeMessage(message.id, message.sender, PermissionError("Only werewolves can chat at night.")), True
                else:
                    # The message is for the day phase, we allow all players to chat
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
                    server.game.accuse_player(
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