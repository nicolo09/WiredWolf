import socket
import time
import unittest

from zeroconf import ServiceInfo

from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer
from wiredwolf.controller.lobbies import Lobby, LobbyBrowser, LobbyInfo, TcpMdnsLobbyBrowser
from wiredwolf.controller.services import ServiceManager


class ServiceManagerTest(unittest.TestCase):
    SERVICE_TYPE = "_wiredwolf._tcp.local."

    def setUp(self):
        # This method would be called before each test to set up the environment
        self.service_manager = ServiceManager(service_type=self.SERVICE_TYPE)

    def register_service(self, service_name: str) -> ServiceInfo:
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sck.bind(("localhost", 0))
        # Test service registration
        return self.service_manager.register_service(service_name, DEFAULT_SERVER_PORT, {})

    def test_service_registration_dont_raise(
        self,
    ):  # TODO: Flaky test, sometimes raises exception
        NAME = "WiredWolfTest1"
        try:
            serviceInfo = self.register_service(NAME)
        except Exception as e:
            self.fail(f"Service registration raised an exception: {e}")
        self.service_manager.unregister_service(serviceInfo)

    def test_service_discovery(self):
        services: dict[str, dict[str, str]] = {}
        self.service_manager.get_service_browser(
            listener=self.service_manager.get_service_listener(self.SERVICE_TYPE,
                on_service_added=lambda name, info: services.update({name: info}),
                on_service_removed=lambda name: (services.pop(name, None), None)[1],
                on_service_updated=lambda name, info: services.update({name: info})
                )
        )
        self.register_service("WiredWolfTest2")

        timeout = 10
        while timeout > 0:
            if any(
                filter(
                    lambda x: isinstance(x, str) and x.startswith("WiredWolfTest2"),
                    services,
                )
            ):
                break
            time.sleep(1)
            timeout -= 1
        self.assertTrue(
            any(
                filter(
                    lambda x: isinstance(x, str) and x.startswith("WiredWolfTest2"),
                    services,
                )
            ),
            "Service 'WiredWolfTest2' was not discovered in time.",
        )


class LobbyBrowserTest(unittest.TestCase):
    def setUp(self):
        self.lobby_browser: LobbyBrowser = TcpMdnsLobbyBrowser()

    def test_lobby_publish_and_discovery(self):  # TODO: Flaky test, sometimes fails
        discovered_lobbies: list[LobbyInfo] = []

        def on_lobby_found(lobby_info: LobbyInfo):
            discovered_lobbies.append(lobby_info)

        self.lobby_browser.start_lobby_browser(
            on_lobby_found=on_lobby_found,
            on_lobby_lost=lambda lobby_info: None,
            on_lobby_updated=lambda lobby_info: None,
        )

        receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        receiver_socket.bind(("localhost", 0))

        # Simulate the publication of a lobby
        owner = Peer("TestOwner")
        lobby_info = Lobby(owner, "TestLobby").lobby_info()
        self.lobby_browser.publish_lobby(lobby_info, DEFAULT_SERVER_PORT)

        timeout = 10
        while timeout > 0:
            if discovered_lobbies:
                break
            time.sleep(1)
            timeout -= 1

        self.assertTrue(
            discovered_lobbies[0].name.startswith("TestLobby"), "No lobbies were discovered."
        )
