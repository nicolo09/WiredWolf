from collections.abc import Callable
import ipaddress
import logging
import socket
from zeroconf import NonUniqueNameException, ServiceBrowser, ServiceInfo, ServiceListener, Zeroconf
from netifaces import interfaces, ifaddresses, AF_INET


class CallbackCachedServiceListener(ServiceListener):
    def __init__(
        self,
        on_service_added: Callable[[str, dict[str, str]], None],
        on_service_removed: Callable[[str], None],
        on_service_updated: Callable[[str, dict[str, str]], None],
    ) -> None:
        super().__init__()
        self.cache: dict[str, dict[str, str]] = {}
        self.__on_service_added = on_service_added
        self.__on_service_removed = on_service_removed
        self.__on_service_updated = on_service_updated

    def decode_properties(self, zc: Zeroconf, type_: str, name: str) -> dict[str, str]:
        service_properties: dict[str, str] = {}
        try:
            info = zc.get_service_info(type_, name)
            if info and info.properties:
                service_properties = {
                    key.decode("utf-8"): value.decode("utf-8")
                    if isinstance(value, bytes)
                    else ""
                    for key, value in info.properties.items()
                }
        except Exception as e:
            logging.warning(f"Failed to get properties for service {name}: {e}")
        return service_properties

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        # Retrieve service properties and pass them to the callback
        if name not in self.cache:
            # If not in cache, decode properties and call the added callback
            self.cache[name] = self.decode_properties(zc, type_, name)
            self.__on_service_added(name, self.cache[name])
        elif self.cache[name] != self.decode_properties(zc, type_, name):
            # If in cache but properties have changed, update cache and call the updated callback
            self.cache[name] = self.decode_properties(zc, type_, name)
            self.__on_service_updated(name, self.cache[name])
        else:
            # If in cache and properties have not changed, do nothing
            pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        if name in self.cache:
            # Remove the service from cache and call the removed callback
            del self.cache[name]
            self.__on_service_removed(name)
        else:
            # If the service is not in cache do nothing
            pass


    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        # If the service is in cache and properties have changed, update cache and call the updated callback
        if name in self.cache and self.cache[name] != self.decode_properties(zc, type_, name):
            self.cache[name] = self.decode_properties(zc, type_, name)
            self.__on_service_updated(name, self.cache[name])
        else:
            # If the service is not in cache or properties have not changed, do nothing
            pass 


class ServiceManager:
    __logger = logging.getLogger(__name__)

    def __init__(self, service_type: str):
        self._zeroconf_client: Zeroconf = Zeroconf()
        self._zeroconf_server: dict[ServiceInfo, Zeroconf] = {}
        self._service_type: str = service_type
        self._closed: bool = False

    def _get_all_local_ips(self) -> list[list[str]]:
        intface_ips = []
        for iface_name in interfaces():
            ips = []
            ifaddresses(iface_name)
            for info in ifaddresses(iface_name).get(AF_INET, []):
                ip = str(info["addr"])
                # if not ip.startswith("127."):     # exclude loopback
                ips.append(ip)
            intface_ips.append(ips)
        return intface_ips

    async def register_service(
        self, name: str, receiverPort: int, properties: dict[str, str]
    ) -> list[ServiceInfo]:
        self.__logger.info(f"Registering service {name} on port {receiverPort}...")
        service_infos = []
        for intface_ips in self._get_all_local_ips():
            self.__logger.debug(f"Local IP address found: {intface_ips}")
            service_info = ServiceInfo(
                type_=self._service_type,
                name=name + "." + self._service_type,
                addresses=[socket.inet_aton(ip) for ip in intface_ips],
                port=receiverPort,
                properties={
                    key: value.encode("utf-8") for key, value in properties.items()
                },
            )
            try:
                zeroconf = Zeroconf(intface_ips)
                await zeroconf.async_register_service(service_info, cooperating_responders=True)
                self._zeroconf_server[service_info] = zeroconf
                service_infos.append(service_info)
            except NonUniqueNameException as e:
                self.__logger.error(f"Service name {name} is already in use.")
                raise RuntimeError(f"Service name {name} is already in use.") from e
            except Exception as e:
                self.__logger.error(f"Failed to register service {name}: {e}")
                raise RuntimeError(f"Failed to register service {name}: {e}") from e
            self.__logger.info(f"Service {name} registered successfully.")
        return service_infos

    async def unregister_service(self, info: list[ServiceInfo]) -> None:
        self.__logger.info(f"Unregistering service {info[0].name}...")
        for service_info in info:
            zeroconf = self._zeroconf_server.get(service_info)
            if zeroconf:
                await zeroconf.async_unregister_service(service_info)
                self.__logger.info(
                    f"Service {service_info.name} unregistered successfully."
                )

    def get_service_listener(
        self,
        service_type: str,
        on_service_added: Callable[[str, dict[str, str]], None],
        on_service_removed: Callable[[str], None],
        on_service_updated: Callable[[str, dict[str, str]], None],
    ) -> CallbackCachedServiceListener:
        self.__logger.info("Starting service listener for type" + service_type + "...")
        return CallbackCachedServiceListener(
            on_service_added=on_service_added,
            on_service_removed=on_service_removed,
            on_service_updated=on_service_updated,
        )

    def get_service_browser(self, listener: ServiceListener) -> ServiceBrowser:
        return ServiceBrowser(self._zeroconf_client, self._service_type, listener)

    async def get_service_endpoints(self, service_name: str) -> list[tuple[str, int]]:
        """Returns the endpoint associated with the provided service name by means of service discovery.

        Args:
            service_name (str): The name of the service to discover.

        Raises:
            RuntimeError: If the service cannot be found or is not properly configured.

        Returns:
            list[tuple[str, int]]: A list of tuples containing the IP addresses and ports of the service.
        """
        service_info = await self._zeroconf_client.async_get_service_info(
            type_=self._service_type, name=service_name + "." + self._service_type
        )
        if service_info and service_info.addresses[0] and service_info.port:
            return [(
                str(ipaddress.ip_address(ip)),
                service_info.port
            ) for ip in service_info.addresses]
        else:
            self.__logger.warning(
                f"Service {service_name} not found or informations incomplete."
            )
            raise TimeoutError(f"Service {service_name} not found.")

    def close(self) -> None:
        """Closes the underlying Zeroconf instance."""
        for server in self._zeroconf_server.values():
            try:
                server.close()
                self.__logger.info("Zeroconf server instance closed.")
            except Exception as e:
                self.__logger.warning(f"Error while closing Zeroconf server: {e}")
        try:
            self._zeroconf_client.close()
            self.__logger.info("Zeroconf instance closed.")
        except Exception as e:
            self.__logger.warning(f"Error while closing Zeroconf: {e}")
