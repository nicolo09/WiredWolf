import asyncio
from enum import Enum
import random
import logging
import abc

from wiredwolf.controller import commons
from wiredwolf.controller.connections.connections import AsyncTCPClientConnectionHandler, ClientConnectionHandler, ConnectionHandlerFactory, ServerConnectionHandler
from wiredwolf.controller.lobbies import Lobby, LobbyBrowser, TcpMdnsLobbyBrowser
from wiredwolf.controller.messages import BaseMessage, CandidateForElectionMessage, ElectionFailedMessage, MasterElectedMessage, RecoveredConnectionsMessage, ApproveCandidateMessage
from wiredwolf.controller.server import GameServer, GameServerFactory
from wiredwolf.model.game import GameStatus

class Recoverable(abc.ABC):
    """Interface for classes that can be recovered by a ConnectionRecoverer."""
    
    @property
    @abc.abstractmethod
    def my_self(self) -> commons.Peer:
        """
        Returns the current peer instance.
        """
        
    @property
    @abc.abstractmethod
    def lobby_browser(self) -> LobbyBrowser:
        """
        Returns the lobby browser instance.
        """
        
    @property
    @abc.abstractmethod
    def connection_handler(self) -> ClientConnectionHandler | None:
        """
        Returns the connection handler instance.
        """
        
    @property
    @abc.abstractmethod
    def lobby(self) -> Lobby | None:
        """
        Returns the current lobby instance, or None if not in a lobby.
        """


DIRECT_RECONNECTION_TIMEOUT = 5  # seconds
DIRECT_RECONNECTION_RETRIES = 3  # number of retries for direct reconnection
DIRECT_RECONNECTION_WAIT_BETWEEN_RETRY = 1  # seconds to wait between retries

NEW_CONNECTION_TIMEOUT = 5  # seconds
NEW_CONNECTION_RETRIES = 3  # number of retries for new connection attempts
NEW_CONNECTION_WAIT_BETWEEN_RETRY = 2  # seconds to wait between retries

CANDIDATE_FOR_ELECTION_DELAY_RANGE = (0, 6)  # seconds, range for random delay before sending CandidateForElectionMessage
CANDIDATION_AWAIT = 5  # seconds, timeout for candidation phase
ELECTION_TIMEOUT = 120  # seconds, timeout for election phase #TODO: Too low? Too high?

class ConnectionStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

class RecoveryPhase(Enum): #TODO: some phases might be useless
    RECONNECTING_TO_SERVER = 1
    CONNECTING_TO_PEERS = 2
    READY_FOR_ELECTION = 3
    CANDIDATE_FOR_ELECTION = 4
    APPROVED_CANDIDATE = 5
    RESTORING_GAME = 6
    LOST_CONNECTION = 7
    RECOVERY_FAILED = 8
    
class RecoveryFailedException(Exception):
    """Exception raised when the recovery process fails."""
    pass

class ConnectionRecoverer(abc.ABC):
    
    @abc.abstractmethod
    async def recover(self, controller: Recoverable) -> tuple[Lobby, GameServer | None, ClientConnectionHandler, GameStatus]:
        """
        Tries to recover the connection of the given Recoverable.

        Args:
            controller (Recoverable): The Recoverable instance to recover.
        """

class TCPConnectionRecoverer(ConnectionRecoverer):

    __logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()
        self._new_master: commons.Peer | None = None
        self._server_conn_handler: ServerConnectionHandler | None = None
        self._client_conn_handlers: dict[commons.Peer, ClientConnectionHandler] = {}
        self._approved_candidate: commons.Peer | None = None
        self._phase = RecoveryPhase.LOST_CONNECTION
        self._backups: set[commons.Peer] = set()  # Set of backup peers that can be used for recovery
        self._can_candidate: bool = False  # Flag to indicate if candidation is allowed after the timeout

    async def recover(self, controller: Recoverable) -> tuple[Lobby, GameServer | None, ClientConnectionHandler, GameStatus]:
        """
        Tries to recover the TCP connection of the given Recoverable.

        Args:
            controller (Recoverable): The Recoverable instance to recover.
        """
        self._clean()  # Reset internal state before starting recovery

        lobby_browser = controller.lobby_browser
        connection_handler = controller.connection_handler
        if isinstance(lobby_browser, TcpMdnsLobbyBrowser) and isinstance(connection_handler, AsyncTCPClientConnectionHandler):
            tries = 0
            self._phase = RecoveryPhase.RECONNECTING_TO_SERVER
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
            self._phase = RecoveryPhase.CONNECTING_TO_PEERS
            lobby = controller.lobby
            if lobby is not None:
                peers_status: dict[commons.Peer, ConnectionStatus] = {peer: ConnectionStatus.DISCONNECTED for peer in lobby.peers if peer != controller.my_self}
                peers_connections: dict[commons.Peer, int] = {controller.my_self: 0} # Number of active connection each peer has recovered
                approvals: dict[commons.Peer, bool] = {}
                candidates: list[commons.Peer] = []

                def on_message(message: BaseMessage):
                    if message.sender is not None:
                        self.__logger.info("New message received from sender: %s, message: %s", message.sender, message)
                        if isinstance(message, RecoveredConnectionsMessage):
                            peers_connections[message.sender] = message.connections
                        elif isinstance(message, CandidateForElectionMessage):
                            candidates.append(message.sender)
                        elif isinstance(message, ApproveCandidateMessage):
                            approvals[message.sender] = True
                        elif isinstance(message, MasterElectedMessage):
                            if message.new_master is not None and peers_status.get(message.new_master) != ConnectionStatus.DISCONNECTED:
                                if message.new_master is not self._approved_candidate:
                                    self._backups.add(message.new_master)
                                elif message.new_master != controller.my_self:
                                    self._new_master = message.new_master
                            else:
                                self.__logger.warning("Cannot connect to the new master, cannot recover game") #FIXME: only if all the peers I'm connected to have a new master that is unreachable I should consider the recovery failed
                                self._phase = RecoveryPhase.RECOVERY_FAILED
                        elif isinstance(message, ElectionFailedMessage):
                            if self._phase == RecoveryPhase.APPROVED_CANDIDATE and message.sender == self._approved_candidate:
                                self.__logger.info("Received ElectionFailedMessage from current candidate: %s", message.sender)
                                self._approved_candidate = None
                                if self._backups:
                                    best_backup = self._get_preferred_new_master({backup: peers_connections.get(backup, 0) for backup in self._backups})
                                    if best_backup is not None:
                                        self._new_master = best_backup
                                else:
                                    self._phase = RecoveryPhase.READY_FOR_ELECTION

                async def on_new_peer_connection(peer: commons.Peer):
                    self.__logger.info("New peer connection established with peer: %s", peer)
                    peers_status[peer] = ConnectionStatus.CONNECTED
                    peers_connections[peer] = 0
                    peers_connections[controller.my_self] = len(self._get_connected_peers(peers_status))
                    await self._send_message_to_all(
                        RecoveredConnectionsMessage(
                            controller.my_self,
                            len(self._get_connected_peers(peers_status)),
                        ),
                        peers_status,
                    )

                async def on_peer_disconnection(peer: commons.Peer):
                        self.__logger.info("Peer disconnected: %s", peer)
                        peers_status[peer] = ConnectionStatus.DISCONNECTED
                        peers_connections.pop(peer, None)
                        peers_connections[controller.my_self] = len(self._get_connected_peers(peers_status))
                        await self._send_message_to_all(
                            RecoveredConnectionsMessage(
                                controller.my_self,
                                len(self._get_connected_peers(peers_status)),
                            ),
                            peers_status,
                        )

                async def on_new_message(message: BaseMessage):
                    self.__logger.info("New message received: %s", message)
                    on_message(message)  # Call the on_message method to handle the received message

                self._server_conn_handler = ConnectionHandlerFactory.get_server_connection_handler(
                    (commons.DEFAULT_SERVER_HOST, commons.DEFAULT_SERVER_PORT),
                    on_new_peer=on_new_peer_connection,
                    on_peer_disconnected=on_peer_disconnection,
                    on_new_message=on_new_message
                )
                await self._server_conn_handler.start_listening()
                # ...and in the meanwhile we try to connect to other peers in the lobby
                for new_connection_attempt in range(NEW_CONNECTION_RETRIES):
                    for peer in lobby.peers:
                        if peers_status.get(peer) == ConnectionStatus.DISCONNECTED:
                            try:
                                async with asyncio.timeout(NEW_CONNECTION_TIMEOUT):  # Set a timeout for the new connection attempt
                                    client_conn_handler = await lobby_browser.connect_to_peer(controller.my_self, (commons.DEFAULT_SERVER_HOST, commons.DEFAULT_SERVER_PORT)) #FIXME: should use the peer's actual endpoint, not the default one
                                    client_conn_handler.set_on_disconnect(lambda peer=peer: on_peer_disconnection(peer)) 
                                    self.__logger.info("Successfully connected to peer: %s", peer)
                                    peers_status[peer] = ConnectionStatus.CONNECTED
                                    peers_connections[peer] = 0
                                    peers_connections[controller.my_self] = len(self._get_connected_peers(peers_status))
                                    client_conn_handler.set_on_message(on_message)
                                    self._client_conn_handlers[peer] = client_conn_handler
                                    await self._send_message_to_all(
                                        RecoveredConnectionsMessage(
                                            controller.my_self,
                                            len(self._get_connected_peers(peers_status)),
                                        ),
                                        peers_status,
                                    )
                            except (asyncio.TimeoutError, Exception) as e:
                                self.__logger.error("Attempt %d Failed to connect to peer: %s", new_connection_attempt + 1, peer)
                    await asyncio.sleep(NEW_CONNECTION_WAIT_BETWEEN_RETRY)  # Wait a bit before retrying

                if any(status != ConnectionStatus.DISCONNECTED for status in peers_status.values()):
                    self.__logger.info("Successfully connected to at least one peer.")

                    self._phase = RecoveryPhase.READY_FOR_ELECTION

                    timer_task: asyncio.Task[None] | None = None    

                    try:
                        async with asyncio.timeout(ELECTION_TIMEOUT):  # Set a timeout for the election process
                            while not self._is_new_master_elected():
                                if self._can_become_new_master(controller.my_self, peers_connections) and self._phase != RecoveryPhase.APPROVED_CANDIDATE:
                                    if not self._can_candidate and timer_task is None:
                                        candidate_delay = random.randint(*CANDIDATE_FOR_ELECTION_DELAY_RANGE)
                                        timer_task = asyncio.create_task(
                                                self._start_timer(candidate_delay)
                                            )
                                    elif self._can_candidate:
                                        self.__logger.info("Timeout reached, sending CandidateForElectionMessage.")
                                        self._phase = RecoveryPhase.CANDIDATE_FOR_ELECTION
                                        await self._send_message_to_all(
                                            CandidateForElectionMessage(controller.my_self),
                                            peers_status
                                        )
                                        # Wait for a while to see if any other peer sends an ApproveCandidateMessage
                                        await asyncio.sleep(CANDIDATION_AWAIT)
                                        if len(approvals) > (len(self._get_connected_peers(peers_status)) + 1) / 2:
                                            self.__logger.info("Received majority of approvals, becoming the new master.")
                                            self._new_master = controller.my_self
                                            await self._send_message_to_all(
                                                MasterElectedMessage(controller.my_self, self._new_master),
                                                peers_status
                                            )
                                        else:
                                            self.__logger.info("Did not receive majority of approvals, waiting for the election process to complete.")
                                            self._phase = RecoveryPhase.READY_FOR_ELECTION
                                            await self._send_message_to_all(
                                                ElectionFailedMessage(controller.my_self),
                                                peers_status
                                            )
                                            approvals.clear()  # Clear approvals for the next round
                                        self._can_candidate = False  # Reset the candidation flag for the next round
                                        if timer_task is not None:
                                            timer_task.cancel()
                                            timer_task = None  # Reset the timer task for the next round

                                # Check if any peer has sent a CandidateForElectionMessage
                                for candidate in candidates:
                                    self.__logger.info("Peer %s has sent a CandidateForElectionMessage", candidate)
                                    if candidate == self._get_preferred_new_master(peers_connections) and self._phase != RecoveryPhase.APPROVED_CANDIDATE:
                                        self._approved_candidate = candidate
                                        await self._send_message_to_peer(
                                            candidate,
                                            ApproveCandidateMessage(controller.my_self),
                                            peers_status
                                        )
                                        self._phase = RecoveryPhase.APPROVED_CANDIDATE
                                await asyncio.sleep(0.1)
                    except asyncio.TimeoutError as e:
                        self.__logger.error("Election process timed out, could not elect a new master.")
                    finally:
                        if timer_task is not None:
                            timer_task.cancel()  # Cancel the timer task if it's still running

                    if self._new_master and self._phase != RecoveryPhase.RECOVERY_FAILED:
                        self.__logger.info("New master elected: %s", self._new_master)
                        # TODO: handle recovery of the game
                        if self._new_master == controller.my_self:
                            # Everybody will connect to me, so I must close the connections to peers
                            for client_conn_handler in self._client_conn_handlers.values():
                                await client_conn_handler.close()
                        else:
                            await self._send_message_to_all(
                                MasterElectedMessage(controller.my_self, self._new_master),
                                peers_status
                            )
                            await self._server_conn_handler.close()  # Close the server connection handler if I'm not the new master
                    else:
                        self.__logger.error("Recovery failed, could not elect a new master.")
                else:
                    self.__logger.error("Failed to connect to any peers after %d attempts.", NEW_CONNECTION_RETRIES)
            else:
                self.__logger.error("Lobby is None, cannot retrieve the list of peers to connect to.")
        else:
            self.__logger.error("Lobby browser or connection handler is not of the expected type for TCP recovery.")
            raise ValueError("Lobby browser or connection handler is not of the expected type for TCP recovery.")

    async def _send_message_to_peer(
        self,
        peer: commons.Peer,
        message: BaseMessage,
        peers_status: dict[commons.Peer, ConnectionStatus],
    ) -> None:
        """
        Sends a message to a specific peer.

        Args:
            peer (Peer): The peer to send the message to.
            message (BaseMessage): The message to send.
            peers_status (dict): A dictionary mapping peers to their connection status.
        """
        if peers_status.get(peer) != ConnectionStatus.DISCONNECTED:
            client_conn_handler = self._client_conn_handlers.get(peer)
            if client_conn_handler is not None:
                try:
                    await client_conn_handler.send_obj(message)
                    self.__logger.info("Sent message to peer: %s", peer)
                except Exception as e:
                    self.__logger.error("Failed to send message to peer %s: %s", peer, e)
            elif self._server_conn_handler is not None:
                try:
                    await self._server_conn_handler.send_obj(peer, message)
                    self.__logger.info("Sent message to peer: %s", peer)
                except Exception as e:
                    self.__logger.error("Failed to send message to peer %s: %s", peer, e)
        else:
            self.__logger.warning(
                "Cannot send message to peer %s because it is disconnected.", peer
            )

    async def _send_message_to_all(
        self,
        message: BaseMessage,
        peers_status: dict[commons.Peer, ConnectionStatus],
    ) -> None:
        """
        Sends a message to all connected peers.

        Args:
            message (BaseMessage): The message to send.
            peers_status (dict): A dictionary mapping peers to their connection status.
        """
        for peer in peers_status.keys():
            await self._send_message_to_peer(peer, message, peers_status)

    async def _start_timer(self, timeout: int) -> None:
        """
        Starts a timer for the specified timeout duration.

        Args:
            timeout (int): The timeout duration in seconds.
        """
        await asyncio.sleep(timeout)
        self._can_candidate = True  # Set the flag to allow candidation after the timeout

    def _get_connected_peers(self, peers_status: dict[commons.Peer, ConnectionStatus]) -> list[commons.Peer]:
        """
        Returns a list of peers that are currently connected.

        Args:
            peers_status (dict): A dictionary mapping peers to their connection status.

        Returns:
            list[commons.Peer]: A list of connected peers.
        """
        return [peer for peer, status in peers_status.items() if status != ConnectionStatus.DISCONNECTED]

    def _get_preferred_new_master(self, peers_connections: dict[commons.Peer, int]) -> commons.Peer | None:
        """
        Returns the peer with the highest number of connections recovered. If there there is a tie the peer alphabetically first is returned.

        Args:
            peers_connections (dict): A dictionary mapping peers to the number of connections they have recovered.

        Returns:
            Peer | None: The preferred new master, or None if no peers are available.
        """
        if not peers_connections:
            return None
        max_connections = max(peers_connections.values())
        preferred_peers = [peer for peer, connections in peers_connections.items() if connections == max_connections]
        return min(preferred_peers, key=lambda peer: peer.uuid)

    def _is_new_master_elected(self) -> bool:
        """
        Checks if a new master has been elected.

        Returns:
            bool: True if a new master has been elected among the connected peers, False otherwise.
        """
        return self._new_master is not None or self._phase == RecoveryPhase.RECOVERY_FAILED

    def _can_become_new_master(self, peer: commons.Peer, peers_connections: dict[commons.Peer, int]) -> bool:
        """
        Checks if the specified peer can become the new master.

        Args:
            peer (Peer): The peer to check.
            peers_connections (dict): A dictionary mapping peers to the number of connections they have recovered.

        Returns:
            bool: True if the specified peer can become the new master, False otherwise.
        """
        if not peers_connections:
            return False
        max_connections = max(peers_connections.values())
        return peer in peers_connections and peers_connections[peer] == max_connections

    def _clean(self) -> None:
        """
        Resets the internal state of the ConnectionRecoverer.
        """
        self._new_master = None
        self._server_conn_handler = None
        self._client_conn_handlers = {}
        self._approved_candidate = None
        self._phase = RecoveryPhase.LOST_CONNECTION
        self._backups = set()  
        self._can_candidate = False
