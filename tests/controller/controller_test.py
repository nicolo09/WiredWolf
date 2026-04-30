import asyncio
from typing import AsyncGenerator
from unittest import mock

import pytest
import pytest_asyncio
from tests.controller.conftest import TIMEOUT
from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser
from wiredwolf.view.custom_events import EventSender

LOBBY_NAME = "Test Lobby"
USER1_NAME = "TestUser"
USER2_NAME = "SecondUser"


@pytest_asyncio.fixture
async def host_controller(
    browser: TcpMdnsLobbyBrowser,
) -> AsyncGenerator[tuple[GameController, EventSender], None]:
    event_sender = mock.Mock()
    controller = GameController(browser=browser, event_sender=event_sender)
    controller.set_username(USER1_NAME)
    yield controller, event_sender
    try:
        await controller.leave()  # TODO: Change this to a more robust method that ensures the controller is properly cleaned up after each test
    except Exception:
        pass


client_controller = host_controller


@pytest.mark.asyncio
async def test_controller_initialization(
    host_controller: tuple[GameController, EventSender],
):
    host_game_controller, event_sender = host_controller
    assert isinstance(host_game_controller, GameController)
    assert host_game_controller.lobby is None


@pytest.mark.asyncio
async def test_controller_publish_discover_lobby(
    host_controller: tuple[GameController, EventSender],
    client_controller: tuple[GameController, EventSender],
):
    host_game_controller, host_event_sender = host_controller
    client_game_controller, client_event_sender = client_controller
    client_game_controller.start_listening_for_lobbies()

    if isinstance(client_event_sender, mock.Mock):
        client_event_sender.new_discovered_lobby.assert_not_called()
    await host_game_controller.create_lobby(name=LOBBY_NAME, password=None)

    if isinstance(client_event_sender, mock.Mock):
        try:
            async with asyncio.timeout(TIMEOUT):
                while not client_event_sender.new_discovered_lobby.called:
                    await asyncio.sleep(0.1)
                client_event_sender.new_discovered_lobby.assert_called_once()
        except asyncio.TimeoutError:
            pytest.fail(
                "Client controller did not discover the lobby within the timeout period."
            )


@pytest.mark.asyncio
async def test_controller_join_lobby(
    host_controller: tuple[GameController, EventSender],
    client_controller: tuple[GameController, EventSender],
):
    host_game_controller, host_event_sender = host_controller
    client_game_controller, client_event_sender = client_controller
    await host_game_controller.create_lobby(name=LOBBY_NAME, password=None)
    assert host_game_controller.lobby is not None
    client_game_controller.start_listening_for_lobbies()

    lobby_info = None
    if isinstance(client_event_sender, mock.Mock):
        try:
            async with asyncio.timeout(TIMEOUT):
                # Wait until the second controller discovers the lobby and captures the lobby info from the call arguments
                while (
                    not client_event_sender.new_discovered_lobby.called
                    or lobby_info is None
                ):
                    if client_event_sender.new_discovered_lobby.call_args:
                        calls = client_event_sender.new_discovered_lobby.call_args_list
                        calls = [
                            call
                            for call in calls
                            if call.args
                            and call.args[0].uuid
                            == host_game_controller.lobby.lobby_info().uuid
                        ]
                        if calls:
                            lobby_info = calls[0].args[0]
                    await asyncio.sleep(0.1)
        except asyncio.TimeoutError:
            pytest.fail(
                "Second controller did not discover the lobby within the timeout period."
            )

    assert lobby_info is not None, (
        "Lobby info was not received by the second controller."
    )
    assert lobby_info == host_game_controller.lobby.lobby_info(), (
        "The discovered lobby info does not match the created lobby info."
    )

    await client_game_controller.join_lobby(lobby_name=lobby_info, lobby_password=None)

    assert client_game_controller.lobby is not None

    try:
        async with asyncio.timeout(TIMEOUT):
            # Wait for the first controller to update its lobby state
            while len(host_game_controller.lobby.peers) < 2:
                await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail(
            "First controller did not update its lobby state after the second controller joined within the timeout period."
        )
    assert host_game_controller.lobby == client_game_controller.lobby
    assert len(client_game_controller.lobby.peers) == 2


@pytest.mark.asyncio
async def test_controller_leave_lobby(
    host_controller: tuple[GameController, EventSender],
    client_controller: tuple[GameController, EventSender],
):
    await test_controller_join_lobby(host_controller, client_controller)
    host_game_controller, host_event_sender = host_controller
    client_game_controller, client_event_sender = client_controller
    assert isinstance(host_event_sender, mock.Mock)
    assert isinstance(client_event_sender, mock.Mock)
    await client_game_controller.leave()
    assert client_game_controller.lobby is None
    assert host_game_controller.lobby is not None
    try:
    # Wait for the first controller to update its lobby state after the second controller leaves
        async with asyncio.timeout(TIMEOUT):
                while len(host_game_controller.lobby.peers) != 1:
                    await asyncio.sleep(0.1)
    except asyncio.TimeoutError:
        pytest.fail(
            "First controller did not update its lobby state after the second controller left within the timeout period."
        )
    assert len(host_game_controller.lobby.peers) == 1
    assert any(peer.name == USER1_NAME for peer in host_game_controller.lobby.peers)
    assert not any(peer.name == USER2_NAME for peer in host_game_controller.lobby.peers)
    host_event_sender.remove_user_in_lobby.assert_called_once()
