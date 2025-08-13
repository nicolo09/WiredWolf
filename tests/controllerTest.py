import os
import socket
import time
import unittest

import concurrent.futures

from zeroconf import ServiceBrowser, ServiceInfo
from wiredwolf.controller.lobbies import Lobby, LobbyBrowser, ServiceManager


class ServiceManagerTest(unittest.TestCase):

    SERVICE_TYPE = "_wiredwolf._tcp.local."

    def setUp(self):
        # This method would be called before each test to set up the environment
        self.service_manager = ServiceManager(service_type=self.SERVICE_TYPE)
        
    def register_service(self, service_name) -> ServiceInfo:
        sck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sck.bind(('localhost', 0))
        # Test service registration
        return self.service_manager.register_service(service_name, sck)

    def test_service_registration(self):
        NAME = "WiredWolfTest1"
        try:
            serviceInfo = self.register_service(NAME)
        except Exception as e:
            self.fail(f"Service registration raised an exception: {e}")
        self.service_manager.unregister_service(serviceInfo)

    def test_service_discovery(self):
        services = []
        self.service_manager.get_service_browser(listener=self.service_manager.get_service_listener(
            service_type=self.SERVICE_TYPE,
            on_service_added=lambda name: services.append(name),
            on_service_removed=lambda name: services.remove(name),
            on_service_updated=lambda name: None
        ))
        self.register_service("WiredWolfTest2")

        timeout = 10
        while timeout > 0:

            if any(filter(lambda x: x.startswith("WiredWolfTest2"), services)):
                break
            time.sleep(1)
            timeout -= 1
        self.assertTrue(any(filter(lambda x: x.startswith("WiredWolfTest2"), services)),
                        "Service 'WiredWolfTest2' was not discovered in time.")


class LobbyBrowserTest(unittest.TestCase):

    def setUp(self):
        self.lobby_browser = LobbyBrowser()

    def test_lobby_publish_and_discovery(self):
        discovered_lobbies: list[str] = []

        def on_lobby_found(name):
            discovered_lobbies.append(name)

        self.lobby_browser.start_lobby_browser(
            on_lobby_found=on_lobby_found,
            on_lobby_lost=lambda name: None,
            on_lobby_updated=lambda name: None
        )

        receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        receiver_socket.bind(('localhost', 0))

        # Simulate the publication of a lobby
        self.lobby_browser.publish_lobby(Lobby(name="TestLobby"), receiver_socket)

        timeout = 10
        while timeout > 0:
            if discovered_lobbies:
                break
            time.sleep(1)
            timeout -= 1

        self.assertTrue(discovered_lobbies[0].startswith("TestLobby"), "No lobbies were discovered.")
