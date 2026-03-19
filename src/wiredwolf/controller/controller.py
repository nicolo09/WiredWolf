import asyncio
import logging

from wiredwolf.controller.connections import ClientConnectionHandler
from wiredwolf.controller.lobbies import LobbyBrowser
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.messages import (
    AcknowledgeMessage,
    BaseMessage,
    ChatMessage,
    GameStartedMessage,
    NotAcknowledgeMessage,
    PhaseAdvanceMessage,
    StartGameMessage,
    VoteBallotMessage,
    VotePlayerMessage,
)
from wiredwolf.controller.server import GameServer, GameServerFactory
from wiredwolf.controller.commons import ACK_TIMEOUT_SECONDS, DEFAULT_SERVER_PORT, Peer
from wiredwolf.model.game import GameStatus
from wiredwolf.model.game_phases import GamePhase
from wiredwolf.model.player import Role
from wiredwolf.view.custom_events import EventSender


class GameController:
    """Handles the game logic and player interactions. This controller is implemented by means of
    TCP connections and mDNS for lobby discovery.
    """

    _logger = logging.getLogger(__name__)

    def __init__(self, browser: LobbyBrowser, event_sender: EventSender):
        self._lobby_browser: LobbyBrowser = browser
        self._lobby: Lobby | None = None
        self._server: GameServer | None = None
        self._my_self: Peer
        self._client_connection_handler: ClientConnectionHandler | None = None
        self._waiting_for_ack: dict[str, tuple[asyncio.Event, Exception | None]] = {}
        self._game_status: GameStatus | None = None
        self._event_sender: EventSender = event_sender

    @property
    def my_self(self) -> Peer:
        """Gets the local player peer.

        Returns:
            Peer: The local player peer.
        """
        return self._my_self

    @property
    def lobby_browser(self) -> LobbyBrowser:
        """Gets the lobby browser.
        Returns:
            TcpMdnsLobbyBrowser: The lobby browser.
        """
        return self._lobby_browser

    @property
    def lobby(self) -> Lobby | None:
        """Gets the current lobby.
        Returns:
            Lobby: The current lobby.
        """
        return self._lobby

    def set_my_self(self, my_self: Peer):
        """Sets the local player peer.

        Args:
            my_self (Peer): The peer representing the local player.
        """
        self._my_self = my_self

    async def create_lobby(self, name: str, password: str | None = None) -> Lobby:
        """Creates a new lobby and local server.

        Args:
            name (str): The name of the lobby.
            password (str | None, optional): The lobby password or None if no password is set.

        Raises:
            RuntimeError: If the lobby could not be created.

        Returns:
            Lobby: The created lobby.
        """
        self._lobby = Lobby(self._my_self, name=name, password=password)
        self._server, self._client_connection_handler = await GameServerFactory.get_game_server(self._lobby)
        self._client_connection_handler.set_on_message(self._on_message)
        await self._client_connection_handler.start_receiving()
        await self._server.start_listening()
        self._lobby_browser.publish_lobby(self._lobby.name, DEFAULT_SERVER_PORT)
        return self._lobby

    async def join_lobby(self, lobby_name: str, lobby_password: str | None) -> Lobby:
        """Joins a lobby by its name.

        Args:
            lobby_name (str): The name of the lobby to join.
            lobby_password (str | None): The password for the lobby or None if no password is set.
        """
        (
            self._client_connection_handler,
            self._lobby,
        ) = await self._lobby_browser.connect_to_lobby_by_name(
            self._my_self, lobby_name, lobby_password
        )
        self._client_connection_handler.set_on_message(self._on_message)
        await self._client_connection_handler.start_receiving()
        return self._lobby

    def start_listening_for_lobbies(self):
        def remove_and_readd_lobby(lobby_name: str):
            """Removes and re-adds a lobby to the discovered lobbies list. This is used to update the
            lobby information when it changes."""
            self._event_sender.remove_discovered_lobby(lobby_name)
            self._event_sender.new_discovered_lobby(lobby_name)
        """Starts listening for available lobbies."""
        self._lobby_browser.start_lobby_browser(
            lambda lobby_name: self._event_sender.new_discovered_lobby(lobby_name),
            lambda lobby_name: self._event_sender.remove_discovered_lobby(lobby_name),
            lambda lobby_name: remove_and_readd_lobby(lobby_name)
        )

    def stop_listening_for_lobbies(self):
        """Stops listening for available lobbies."""
        self._lobby_browser.stop_lobby_browser()

    def _on_message(self, message: BaseMessage):
        match message:
            case AcknowledgeMessage():
                # Notify the waiting coroutine that the acknowledgment has been received
                if message.id in self._waiting_for_ack:
                    self._waiting_for_ack[message.id][0].set()
            case NotAcknowledgeMessage():
                # Notify the waiting coroutine that an error has occurred
                self._waiting_for_ack[message.id] = (
                    self._waiting_for_ack[message.id][0],
                    message.error,
                )
                if message.id in self._waiting_for_ack:
                    self._waiting_for_ack[message.id][0].set()
            case GameStartedMessage():
                self._logger.info("Game has started.")
                self._game_status = message.status
                self._event_sender.game_started_by_master()
            case PhaseAdvanceMessage():
                self._logger.info("Game phase has advanced.")
                match message.outcome.new_phase:
                    case GamePhase.DAY_DISCUSSION:
                        self._event_sender.end_night()
                    case GamePhase.DAY_ACCUSING:
                        self._event_sender.start_voting_for_nominations()
                    case GamePhase.DAY_BALLOT:
                        self._event_sender.start_voting_for_ballot()
                    case GamePhase.NIGHT:
                        if self._game_status is not None:
                            my_self = next(player for player in self._game_status.players if player.id == self._my_self.uuid)
                            self._event_sender.start_night(my_self.role is Role.VILLAGER)
                    case _:
                        NotImplementedError("")
                        #TODO: Add game end screens
                if message.outcome.someone_died():
                    self._logger.info("A player has died this phase.")
                    for player in message.outcome.deaths:
                        self._event_sender.display_chat_message(
                            f"{player} has died."
                        )
                if message.outcome.new_phase in (
                    GamePhase.VILLAGERS_VICTORY,
                    GamePhase.WEREWOLVES_VICTORY,
                ):
                    self._logger.info("Game has ended with a victory.")
                    if message.outcome.new_phase == GamePhase.VILLAGERS_VICTORY:
                        self._event_sender.villager_win()
                    elif message.outcome.new_phase == GamePhase.WEREWOLVES_VICTORY:
                        self._event_sender.werewolf_win()
                    #TODO: Wait for a few seconds and then return to the main menu
            case _:
                self._logger.warning("Unhandled message type: %s", type(message))

    async def _wait_for_acknowledgment(self, message_id: str):
        """Waits for an acknowledgment for a message with the given ID.

        Args:
            message_id (str): The ID of the message to wait for acknowledgment.
        """
        try:
            async with asyncio.timeout(ACK_TIMEOUT_SECONDS):
                await self._waiting_for_ack[message_id][0].wait()
            error = self._waiting_for_ack[message_id][1]
            if error:
                self._logger.error("Error NACK received for message: %s", message_id)
                raise error
            else:
                self._logger.info("ACK received for message: %s", message_id)
        except TimeoutError as e:
            self._logger.warning("ACK timeout for message: %s", message_id)
            raise e
        finally:
            del self._waiting_for_ack[message_id]

    async def _send_message_and_wait_for_ack(self, message: BaseMessage):
        if self._client_connection_handler is None:
            raise RuntimeError("Not connected to a lobby.")
        self._waiting_for_ack[message.id] = (asyncio.Event(), None)
        await self._client_connection_handler.send_obj(message)
        await self._wait_for_acknowledgment(message.id)

    async def send_chat_message(self, message: str):
        """Sends a chat message to all peers in the lobby.

        Args:
            message (str): The chat message to send.
        """
        if self._client_connection_handler is None:
            raise RuntimeError("Not connected to a lobby.")
        await self._client_connection_handler.send_obj(
            ChatMessage(self._my_self, message)
        )

    async def start_game(self):
        """Sends a request to start the game. This method may be called only by the lobby owner."""
        await self._send_message_and_wait_for_ack(
            StartGameMessage(self._my_self)
        )

    async def choose_player(self, player: Peer):
        """Votes a player in the lobby. This method may be called only during a voting phase.

        Args:
            player (Peer): The player to choose.
        """
        await self._send_message_and_wait_for_ack(
            VotePlayerMessage(self._my_self, player.uuid)
        )

    async def vote_guilty(self):
        """Votes for the selected player to be guilty. This method may be called only during a
        guilty decision voting phase."""
        #TODO: Change this and vote_innocent to a single method that takes a boolean parameter, since the logic is the same for both
        await self._send_message_and_wait_for_ack(
            VoteBallotMessage(self._my_self, True)
        )

    async def vote_innocent(self):
        """Votes for the selected player to be innocent. This method may be called only during a
        guilty decision voting phase."""
        #TODO: Change this and vote_guilty to a single method that takes a boolean parameter, since the logic is the same for both
        await self._send_message_and_wait_for_ack(
            VoteBallotMessage(self._my_self, False)
        )

class ControllerFactory:
    @staticmethod
    def get_controller(browser: LobbyBrowser, event_sender: EventSender) -> GameController:
        """Creates and returns a new GameController instance.

        Args:
            browser (LobbyBrowser): The lobby browser to use.
            event_sender (EventSender): The event sender to use.
        Returns:
            GameController: The created game controller.
        """
        return GameController(browser, event_sender)