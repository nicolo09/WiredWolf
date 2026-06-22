from unittest.mock import AsyncMock, call
import pytest
import pytest_asyncio
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.messages import AcknowledgeMessage, ChatMessage, NotAcknowledgeMessage
from wiredwolf.controller.server_plugins import ChatPlugin
from wiredwolf.model.game_phases import GamePhase
from wiredwolf.model.player import BasicRole, Player, Status


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

@pytest.mark.asyncio
async def test_chat_plugin_night_werewolves_allowed(chat_plugin: ChatPlugin, server_mock: AsyncMock):
    # Change players in game with two werewolves
    players = [
        Player("1", "Alice", BasicRole.VILLAGER),
        Player("2", "Bob", BasicRole.WEREWOLF),
        Player("3", "Charlie", BasicRole.WEREWOLF),
        Player("4", "David", BasicRole.CLAIRVOYANT),
    ]
    server_mock.game.players = players
    server_mock.game.phase = GamePhase.NIGHT

    message = ChatMessage(Peer("Charlie", "3"), "Night: werewolf chat", server_mock.game.phase)
    ack_message, should_stop = await chat_plugin.handle_message_sub(message, server_mock)

    assert isinstance(ack_message, AcknowledgeMessage)
    werewolves = [p for p in server_mock.game.players if p.role == BasicRole.WEREWOLF and p.is_alive()]
    # There should be a call to send_to_uuid for each alive werewolf (including sender)
    expected_calls = [call(w.id, message) for w in werewolves]
    server_mock.send_to_uuid.assert_has_calls(expected_calls, any_order=True)
    server_mock.send_to_all.assert_not_called()


@pytest.mark.asyncio
async def test_chat_plugin_night_non_werewolf_rejected(chat_plugin: ChatPlugin, server_mock: AsyncMock):
    # Set game phase to night and try to send a message from a non-werewolf player
    server_mock.game.phase = GamePhase.NIGHT
    message = ChatMessage(Peer("Alice", "1"), "I should not talk at night", server_mock.game.phase)
    ack_message, should_stop = await chat_plugin.handle_message_sub(message, server_mock)
    # It should be rejected with a permission error
    assert isinstance(ack_message, NotAcknowledgeMessage)
    assert isinstance(ack_message.error, PermissionError)


@pytest.mark.asyncio
async def test_chat_plugin_dead_players_chat_and_see_living_messages(chat_plugin: ChatPlugin, server_mock: AsyncMock):
    # Mark two players as dead
    players = [
        Player("1", "Alice", BasicRole.VILLAGER),
        Player("2", "Bob", BasicRole.VILLAGER),
        Player("3", "Charlie", BasicRole.WEREWOLF),
        Player("4", "David", BasicRole.CLAIRVOYANT),
    ]
    players[0].status = Status.DEAD
    players[1].status = Status.DEAD
    server_mock.game.players = players
    server_mock.game.phase = GamePhase.DAY_DISCUSSION

    # If a dead player sends a message it should be forwarded only to other dead players
    dead_message = ChatMessage(Peer("Alice", "1"), "I'm dead, whisper to other dead", server_mock.game.phase)
    ack_dead, _ = await chat_plugin.handle_message_sub(dead_message, server_mock)
    assert isinstance(ack_dead, AcknowledgeMessage)
    dead_players = [p for p in server_mock.game.players if not p.is_alive()]
    expected_dead_calls = [call(p.id, dead_message) for p in dead_players]
    server_mock.send_to_uuid.assert_has_calls(expected_dead_calls, any_order=True)
    server_mock.send_to_all.assert_not_called()

    # Dead players should still see messages from alive players
    alive_message = ChatMessage(Peer("Charlie", "3"), "Alive says hello", server_mock.game.phase)
    ack_alive, _ = await chat_plugin.handle_message_sub(alive_message, server_mock)
    assert isinstance(ack_alive, AcknowledgeMessage)
    server_mock.send_to_all.assert_called_once_with(alive_message)


@pytest.mark.asyncio
async def test_chat_plugin_wrong_senders_rejected(chat_plugin: ChatPlugin, server_mock: AsyncMock):
    server_mock.game.phase = GamePhase.DAY_DISCUSSION

    # Sender not in game
    fake_sender_msg = ChatMessage(Peer("FakePeer", "999"), "I'm not in the game", server_mock.game.phase)
    ack_fake, _ = await chat_plugin.handle_message_sub(fake_sender_msg, server_mock)
    assert isinstance(ack_fake, NotAcknowledgeMessage)
    assert isinstance(ack_fake.error, ValueError)