from collections.abc import Callable
import ipaddress
import logging
import socket
from zeroconf import ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf

from wiredwolf.controller import TIMEOUT


class CallbackServiceListener(ServiceListener):
    def __init__(
        self,
        on_service_added: Callable[[str], None],
        on_service_removed: Callable[[str], None],
        on_service_updated: Callable[[str], None],
    ) -> None:
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


class ServiceManager:
    __logger = logging.getLogger(__name__)

    def __init__(self, service_type: str):
        self._zeroconf: Zeroconf = Zeroconf()
        self._service_type: str = service_type

    def register_service(self, name: str, receiverPort: int) -> ServiceInfo:
        self.__logger.info(f"Registering service {name} on port {receiverPort}...")
        service_info = ServiceInfo(
            type_=self._service_type,
            name=name + "." + self._service_type,
            addresses=[socket.inet_aton("127.0.0.1")],
            port=receiverPort,
            properties={},
        )
        self._zeroconf.register_service(service_info)
        self.__logger.info(f"Service {name} registered successfully.")
        return service_info

    def unregister_service(self, info: ServiceInfo) -> None:
        self.__logger.info(f"Unregistering service {info.name}...")
        self._zeroconf.unregister_service(info)
        self.__logger.info(f"Service {info.name} unregistered successfully.")

    def get_service_listener(
        self,
        service_type: str,
        on_service_added: Callable[[str], None],
        on_service_removed: Callable[[str], None],
        on_service_updated: Callable[[str], None],
    ) -> CallbackServiceListener:
        self.__logger.info("Starting service listener for type" + service_type + "...")
        return CallbackServiceListener(
            on_service_added=on_service_added,
            on_service_removed=on_service_removed,
            on_service_updated=on_service_updated,
        )

    def get_service_browser(self, listener: ServiceListener) -> ServiceBrowser:
        return ServiceBrowser(self._zeroconf, self._service_type, listener)

    def get_service_endpoint(self, service_name: str) -> tuple[str, int]:
        service_info = self._zeroconf.get_service_info(
            self._service_type, service_name, timeout=TIMEOUT
        )
        if service_info and service_info.addresses[0] and service_info.port:
            return str(ipaddress.ip_address(service_info.addresses[0])), service_info.port
        else:
            self.__logger.warning(f"Service {service_name} not found or informations incomplete.")
            raise RuntimeError(
                f"Service {service_name} not found."
            )  # TODO: Change RuntimeError with something more appropriate
