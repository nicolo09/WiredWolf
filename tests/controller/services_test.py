import socket
import asyncio
import pytest

import pytest_asyncio
from zeroconf import ServiceInfo

from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.lobbies import Lobby, LobbyBrowser, LobbyInfo, TcpMdnsLobbyBrowser
from wiredwolf.controller.services import ServiceManager


SERVICE_TYPE = "_wiredwolf._tcp.local."


@pytest_asyncio.fixture
async def service_manager():
    yield ServiceManager(service_type=SERVICE_TYPE)


async def _register_service(service_manager: ServiceManager, service_name: str) -> ServiceInfo:
    sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sck.bind(("localhost", 0))
    try:
        return await service_manager.register_service(service_name, DEFAULT_SERVER_PORT, {})
    finally:
        sck.close()


@pytest.mark.asyncio
async def test_service_registration_dont_raise(service_manager: ServiceManager):
    NAME = "WiredWolfTest1"
    try:
        serviceInfo = await _register_service(service_manager, NAME)
    except Exception as e:
        pytest.fail(f"Service registration raised an exception: {e}")
    await service_manager.unregister_service(serviceInfo)


@pytest.mark.asyncio
async def test_service_discovery(service_manager: ServiceManager):
    services: dict[str, dict[str, str]] = {}
    service_manager.get_service_browser(
        listener=service_manager.get_service_listener(
            SERVICE_TYPE,
            on_service_added=lambda name, info: services.update({name: info}),
            on_service_removed=lambda name: (services.pop(name, None), None)[1],
            on_service_updated=lambda name, info: services.update({name: info}),
        )
    )
    await _register_service(service_manager, "WiredWolfTest2")

    timeout = 10
    while timeout > 0:
        if any(
            filter(
                lambda x: isinstance(x, str) and x.startswith("WiredWolfTest2"),
                services,
            )
        ):
            break
        await asyncio.sleep(1)
        timeout -= 1
    assert any(
        filter(
            lambda x: isinstance(x, str) and x.startswith("WiredWolfTest2"),
            services,
        )
    ), "Service 'WiredWolfTest2' was not discovered in time."


@pytest_asyncio.fixture
async def lobby_browser():
    lb: LobbyBrowser = TcpMdnsLobbyBrowser()
    yield lb


@pytest.mark.asyncio
async def test_lobby_publish_and_discovery(lobby_browser: LobbyBrowser):
    discovered_lobbies: list[LobbyInfo] = []

    def on_lobby_found(lobby_info: LobbyInfo):
        discovered_lobbies.append(lobby_info)

    lobby_browser.start_lobby_browser(
        on_lobby_found=on_lobby_found,
        on_lobby_lost=lambda lobby_info: None,
        on_lobby_updated=lambda lobby_info: None,
    )

    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    receiver_socket.bind(("localhost", 0))
    receiver_socket.close()

    owner = Peer("TestOwner")
    lobby_info = Lobby(owner, "TestLobby").lobby_info()
    await lobby_browser.publish_lobby(lobby_info, DEFAULT_SERVER_PORT)

    timeout = 10
    while timeout > 0:
        if discovered_lobbies:
            break
        await asyncio.sleep(1)
        timeout -= 1

    assert discovered_lobbies and discovered_lobbies[0].name.startswith("TestLobby"), "No lobbies were discovered."
