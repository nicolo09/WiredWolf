import asyncio
import logging

from wiredwolf.controller import commons
from wiredwolf.controller.connections.connections import AsyncTCPClientConnectionHandler, ConnectionHandlerFactory
from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser
from wiredwolf.controller.messages import BaseMessage

DIRECT_RECONNECTION_TIMEOUT = 5  # seconds
DIRECT_RECONNECTION_RETRIES = 3  # number of retries for direct reconnection
DIRECT_RECONNECTION_WAIT_BETWEEN_RETRY = 1  # seconds to wait between retries

class ConnectionStatus:
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

class ConnectionRecoverer:
    async def recover(self, controller: GameController) -> None:
        """
        Tries to recover the connection of the given GameController.

        Args:
            controller (GameController): The GameController instance to recover.
        """
        pass

class TCPConnectionRecoverer(ConnectionRecoverer):

    __logger = logging.getLogger(__name__)

    async def recover(self, controller: GameController) -> None:
        """
        Tries to recover the TCP connection of the given GameController.

        Args:
            controller (GameController): The GameController instance to recover.
        """
        lobby_browser = controller.lobby_browser
        connection_handler = controller.connection_handler
        if isinstance(lobby_browser, TcpMdnsLobbyBrowser) and isinstance(connection_handler, AsyncTCPClientConnectionHandler):
            tries = 0
            # First thing to do is to try to reconnect to the server
            for tries in range(DIRECT_RECONNECTION_RETRIES):
                try:
                    async with asyncio.timeout(DIRECT_RECONNECTION_TIMEOUT):  # Set a timeout for the direct reconnection attempt
                        await lobby_browser.connect_to_lobby_directly(controller.my_self, connection_handler.endpoint, None)
                        self.__logger.info("Direct reconnection attempt %d succeeded.", tries + 1)
                        #TODO: Add logic to handle successful reconnection, e.g. reinitialize the controller's connection handler and game state...
                except (asyncio.TimeoutError, Exception) as e:
                    # This attempt timed out or failed for another reason, log the warning and continue to the next attempt
                    self.__logger.warning("Direct reconnection attempt failed after %d tries.", tries + 1)
                    self.__logger.debug("Exception occurred: %s", e)
                    await asyncio.sleep(DIRECT_RECONNECTION_WAIT_BETWEEN_RETRY)  # Wait a bit before retrying
            # If we reach here, all direct reconnection attempts have failed, we consider server as unreachable and try to connect to other peers in the lobby
            self.__logger.info("All direct reconnection attempts failed. Server is considered unreachable.")
            # Direct reconnection failed, we open a server conn handler to let other peer connect to us...
            lobby = controller.lobby
            if lobby is not None:
                peers_status = {peer: ConnectionStatus.DISCONNECTED for peer in lobby.peers}
                async def on_new_peer_connection(peer: commons.Peer):
                    self.__logger.info("New peer connection established with peer: %s", peer)
                    peers_status[peer] = ConnectionStatus.CONNECTED
                async def on_peer_disconnection(peer: commons.Peer):
                    self.__logger.info("Peer disconnected: %s", peer)
                    peers_status[peer] = ConnectionStatus.DISCONNECTED
                async def on_new_message(message: BaseMessage):
                    self.__logger.info("New message received: %s", message)                
                server_conn_handler = ConnectionHandlerFactory.get_server_connection_handler(
                    (commons.DEFAULT_SERVER_HOST, commons.DEFAULT_SERVER_PORT),
                    on_new_peer=on_new_peer_connection,
                    on_peer_disconnected=on_peer_disconnection,
                    on_new_message=on_new_message
                )
                await server_conn_handler.start_listening()
                #...and in the meanwhile we try to connect to other peers in the lobby
                #TODO Add retry logic for connecting to peers
                for peer in lobby.peers:
                    if peer.uuid != controller.my_self.uuid and peers_status.get(peer) == ConnectionStatus.DISCONNECTED:  # Don't try to connect to ourselves
                        try:
                            client_conn_handler = await lobby_browser.connect_to_peer(controller.my_self, (commons.DEFAULT_SERVER_HOST, commons.DEFAULT_SERVER_PORT))
                            # TODO: Implement further logic for handling the connected client connection handler
                            self.__logger.info("Successfully connected to peer: %s", peer)
                            peers_status[peer] = ConnectionStatus.CONNECTED
                        except Exception as e:
                            self.__logger.error("Failed to connect to peer: %s", peer)
            else:
                self.__logger.error("Lobby is None, cannot retrieve the list of peers to connect to.")
        else:
            self.__logger.error("Lobby browser or connection handler is not of the expected type for TCP recovery.")
            raise ValueError("Lobby browser or connection handler is not of the expected type for TCP recovery.")