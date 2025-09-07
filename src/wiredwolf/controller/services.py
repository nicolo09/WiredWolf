from collections.abc import Callable
import logging
import socket
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

from wiredwolf.controller import TIMEOUT


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
    __zeroconf: Zeroconf
    __service_type: str

    def __init__(self, service_type: str):
        self.__zeroconf = Zeroconf()
        self.__service_type = service_type

    def register_service(self, name: str, receiverSocket: socket.socket) -> ServiceInfo:
        self.__port = receiverSocket.getsockname()[1]
        self.__logger.info(
            f"Registering service {name} on port {self.__port}...")
        service_info = ServiceInfo(
            type_=self.__service_type,
            name=name + "." + self.__service_type,
            addresses=[socket.inet_aton("127.0.0.1")],
            port=self.__port,
            properties={}
        )
        self.__zeroconf.register_service(service_info)
        self.__logger.info(f"Service {name} registered successfully.")
        return service_info

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
    
    def connect_to_service(self, service_name: str) -> socket.socket:
        """Resolves a service by name and connects to it.

        Args:
            service_name (str): The name of the service to connect to.

        Raises:
            RuntimeError: If the service cannot be found or connected to.

        Returns:
            socket.socket: The connected socket.
        """
        service_info = self.__zeroconf.get_service_info(self.__service_type, service_name, timeout=TIMEOUT)
        if service_info:
            self.__logger.info(f"Connecting to service {service_name}...")
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((service_info.addresses[0], service_info.port))
                return sock
            except Exception as e:
                self.__logger.error(f"Error connecting to service {service_name}: {e}")
                raise RuntimeError(f"Could not connect to service {service_name}.") from e #TODO: Change RuntimeError with something more appropriate
        else:
            self.__logger.warning(f"Service {service_name} not found.")
            raise RuntimeError(f"Service {service_name} not found.") #TODO: Change RuntimeError with something more appropriate
