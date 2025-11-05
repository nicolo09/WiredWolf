import asyncio
import logging
import pytest
import pytest_asyncio
from tests.controller.utils import TestFactory
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.connections import ClientConnectionHandler
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.messages import (
    BaseMessage,
    GameStartedMessage,
    StartGameMessage,
)
from wiredwolf.controller.server import GameServer

logger = logging.getLogger(__name__)


@pytest_asyncio.fixture
async def lobby_owner_server_clients(request: pytest.FixtureRequest):
    owner = Peer("Owner")
    lobby = Lobby(owner, "Test Lobby", None)
    server, handlers = await TestFactory.create_tcp_server_with_connected_clients(
        request.param, lobby
    )
    yield lobby, owner, server, handlers
    await server.close()
    for handler in handlers:
        await handler.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("lobby_owner_server_clients", [5, 34], indirect=True)
async def test_start_game_with_too_few_or_too_many_players(
    lobby_owner_server_clients: tuple[
        Lobby, Peer, GameServer, list[ClientConnectionHandler]
    ],
):
    event = asyncio.Event()
    _, owner, _, handlers = lobby_owner_server_clients

    def on_message(msg: BaseMessage) -> None:
        if isinstance(msg, GameStartedMessage):
            pytest.fail(
                "GameStartedMessage should not be received with too few players"
            )
        elif isinstance(msg, Exception):
            logger.info(msg)
            event.set()

    for handler in handlers:
        handler.set_on_message(on_message)
    await handlers[0].send_obj(StartGameMessage(owner))
    try:
        async with asyncio.timeout(5):
            await event.wait()
    except TimeoutError:
        logger.info("Test timed out waiting for event")
        pytest.fail("No exception received as expected with too few players")



@pytest.mark.asyncio
@pytest.mark.parametrize("lobby_owner_server_clients", [15], indirect=True)
async def test_start_game_success(
    lobby_owner_server_clients: tuple[
        Lobby, Peer, GameServer, list[ClientConnectionHandler]
    ],
):
    event = asyncio.Event()
    _, owner, _, handlers = lobby_owner_server_clients

    def on_message(msg: BaseMessage) -> None:
        if isinstance(msg, GameStartedMessage):
            logger.info(msg)
            event.set()
        elif isinstance(msg, Exception):
            raise msg

    for handler in handlers:
        handler.set_on_message(on_message)
    await handlers[0].send_obj(StartGameMessage(owner))
    try:
        async with asyncio.timeout(5):
            await event.wait()
    except TimeoutError:
        logger.info("Test timed out waiting for event")
        pytest.fail("No GameStartedMessage received")

@pytest.mark.asyncio
@pytest.mark.parametrize("lobby_owner_server_clients", [15], indirect=True)
async def test_non_owner_cannot_start_game(
    lobby_owner_server_clients: tuple[
        Lobby, Peer, GameServer, list[ClientConnectionHandler]
    ],
):
    event = asyncio.Event()
    _, _, _, handlers = lobby_owner_server_clients

    def on_message(msg: BaseMessage) -> None:
        if isinstance(msg, GameStartedMessage):
            pytest.fail("GameStartedMessage should not be received from non-owner")
        elif isinstance(msg, Exception):
            logger.info(msg)
            event.set()

    for handler in handlers:
        handler.set_on_message(on_message)
    # Use a non-owner peer to attempt to start the game
    await handlers[1].send_obj(StartGameMessage(handlers[1].my_self))
    try:
        async with asyncio.timeout(5):
            await event.wait()
    except TimeoutError:
        logger.info("Test timed out waiting for event")
        pytest.fail("No exception received as expected from non-owner")

@pytest.mark.asyncio
@pytest.mark.parametrize("lobby_owner_server_clients", [15], indirect=True)
async def test_start_game_multiple_times(
    lobby_owner_server_clients: tuple[
        Lobby, Peer, GameServer, list[ClientConnectionHandler]
    ],
):
    event = asyncio.Event()
    _, owner, _, handlers = lobby_owner_server_clients

    def on_first_message(msg: BaseMessage) -> None:
        if isinstance(msg, GameStartedMessage):
            logger.info("Received GameStartedMessage")
            event.set()
        elif isinstance(msg, Exception):
            raise msg

    for handler in handlers:
        handler.set_on_message(on_first_message)
    
    await handlers[0].send_obj(StartGameMessage(owner))
    try:
        async with asyncio.timeout(5):
            await event.wait()
    except TimeoutError:
        logger.info("Test timed out waiting for event")
        pytest.fail("No GameStartedMessage received")

    # Reset event for second attempt
    event.clear()
    def on_second_message(msg: BaseMessage) -> None:
        if isinstance(msg, GameStartedMessage):
            pytest.fail("GameStartedMessage should not be received on second start")
        elif isinstance(msg, Exception):
            logger.info("Correctly received Exception on second start")
            event.set()
    for handler in handlers:
        handler.set_on_message(on_second_message)
    await handlers[0].send_obj(StartGameMessage(owner))
    try:
        async with asyncio.timeout(5):
            await event.wait()
    except TimeoutError:
        logger.info("No messages received on second start as expected")
