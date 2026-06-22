from unittest.mock import AsyncMock
import pytest
import pytest_asyncio
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.messages import AcknowledgeMessage, ChatMessage
from wiredwolf.controller.server_plugins import ChatPlugin
from wiredwolf.model.game_phases import GamePhase
from wiredwolf.model.player import BasicRole, Player


@pytest_asyncio.fixture
async def server_mock():
    players = [
        Player("1", "Alice", BasicRole.VILLAGER),
        Player("2", "Bob", BasicRole.VILLAGER),
        Player("3", "Charlie", BasicRole.WEREWOLF),
        Player("4", "David", BasicRole.CLAIRVOYANT)
    ]
    server = AsyncMock()
    server.game = AsyncMock()
    server.game.players = players
    server.game.phase = None
    yield server

@pytest_asyncio.fixture
async def chat_plugin():
    plugin = ChatPlugin()
    yield plugin

@pytest.mark.asyncio
async def test_chat_plugin_lobby(chat_plugin: ChatPlugin, server_mock: AsyncMock):
    message = ChatMessage(Peer("Alice", "1"), "Hello everyone!", server_mock.game.phase)
    ack_message, should_stop = await chat_plugin.handle_message_sub(message, server_mock)
    assert isinstance(ack_message, AcknowledgeMessage)
    server_mock.send_to_all.assert_called_once_with(message)

@pytest.mark.asyncio
@pytest.mark.parametrize("game_phase", [GamePhase.DAY_DISCUSSION, GamePhase.DAY_ACCUSING, GamePhase.DAY_BALLOT, GamePhase.FIRST_DAY, GamePhase.BALLOT_RESULT])
async def test_chat_plugin_day_all_alive(chat_plugin: ChatPlugin, server_mock: AsyncMock, game_phase: GamePhase):
    server_mock.game.phase = game_phase
    message = ChatMessage(Peer("Alice", "1"), "Hello everyone!", server_mock.game.phase)
    ack_message, should_stop = await chat_plugin.handle_message_sub(message, server_mock)
    assert isinstance(ack_message, AcknowledgeMessage)
    server_mock.send_to_all.assert_called_once_with(message)

#TODO: Test for other cases, such as night phase with werewolves, night phase with non-werewolves, messages from dead players, and wrong senders.