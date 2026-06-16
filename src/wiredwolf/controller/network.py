from abc import ABC, abstractmethod
import socket

import psutil

class NetworkExplorer(ABC):
    
    @staticmethod
    @abstractmethod
    def get_local_ipv4_addresses() -> list[list[str]]:
        """
        Returns a list of lists of local IPv4 addresses for each network interface.
        """
    
    
class PsutilNetworkExplorer(NetworkExplorer):

    @staticmethod
    def get_local_ipv4_addresses() -> list[list[str]]:
        local_ip_addresses: list[list[str]] = []
        for interface_addresses in psutil.net_if_addrs().values():
            ipv4_addresses = [
                address.address
                for address in interface_addresses
                if address.family == socket.AF_INET
                # and not address.address.startswith("127.")  # Exclude loopback addresses
                #TODO: remove localhost?
            ]
            local_ip_addresses.append(ipv4_addresses)
        return local_ip_addresses