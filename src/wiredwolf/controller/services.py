from collections.abc import Callable
import logging
import socket
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf


class CallbackServiceListener(ServiceListener):

    def __init__(self, on_service_added: Callable[[str], None], on_service_removed: Callable[[str], None], on_service_updated: Callable[[str], None]) -> None:
        super().__init__()
        self.__on_service_added = on_service_added
        self.__on_service_removed = on_service_removed
        self.__on_service_updated = on_service_updated

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.__on_service_added(name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.__on_service_removed(name)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.__on_service_updated(name)  # TODO: Implement service update logic


class ServiceManager():

    __logger = logging.getLogger(__name__)

    __port: int

    def __init__(self, service_type: str):
        self.__zeroconf = Zeroconf()
        self.__service_type = service_type

    def register_service(self, name: str, receiverSocket: socket.socket) -> ServiceInfo:
        self.__port = receiverSocket.getsockname()[1]
        self.__logger.info(
            f"Registering service {name} on port {self.__port}...")
        serviceInfo = ServiceInfo(
            type_=self.__service_type,
            name=name + "." + self.__service_type,
            addresses=[socket.inet_aton("127.0.0.1")],
            port=self.__port,
            properties={}
        )
        self.__zeroconf.register_service(serviceInfo)
        self.__logger.info(f"Service {name} registered successfully.")
        return serviceInfo

    def unregister_service(self, info: ServiceInfo) -> None:
        self.__logger.info(f"Unregistering service {info.name}...")
        self.__zeroconf.unregister_service(info)
        self.__logger.info(f"Service {info.name} unregistered successfully.")

    def get_service_listener(self, service_type: str, on_service_added: Callable[[str], None], on_service_removed: Callable[[str], None], on_service_updated: Callable[[str], None]) -> CallbackServiceListener:
        self.__logger.info(
            "Starting service listener for type" + service_type + "...")
        return CallbackServiceListener(
            on_service_added=on_service_added,
            on_service_removed=on_service_removed,
            on_service_updated=on_service_updated
        )

    def get_service_browser(self, listener: ServiceListener) -> ServiceBrowser:
        return ServiceBrowser(self.__zeroconf, self.__service_type, listener)
