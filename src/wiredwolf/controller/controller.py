import asyncio
import copy
import logging

from wiredwolf.controller.connections import ClientConnectionHandler
from wiredwolf.controller.lobbies import LobbyBrowser, LobbyBrowserFactory, LobbyInfo
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.messages import (
    AcknowledgeMessage,
    BaseMessage,
    ChatMessage,
    GameStartedMessage,
    LobbyUpdatedMessage,
    NotAcknowledgeMessage,
    PhaseAdvanceMessage,
    StartGameMessage,
    VoteBallotMessage,
    VotePlayerMessage,
)
from wiredwolf.controller.server import GameServer, GameServerFactory
from wiredwolf.controller.commons import ACK_TIMEOUT_SECONDS, DEFAULT_SERVER_PORT, Peer
from wiredwolf.model.game import GameStatus, can_perform_action_on
from wiredwolf.model.game_phases import GamePhase
from wiredwolf.model.player import BasicRole, Player
from wiredwolf.view.custom_events import EventSender

# TODO: Check if the lobby is removed from advertisement when the game starts


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
        """Gets the current lobby (this is a copy, changes are not reflected in the controller).
        Returns:
            Lobby: The current lobby.
        """
        return copy.deepcopy(self._lobby)

    def my_self_as_player(self) -> Player | None:
        """Gets the local player as a Player object if the lobby and game status are available.

        Returns:
            Player | None: The local player as a Player object, or None if the lobby or game status is not available.
        """
        return self._peer_as_player(self._my_self)

    def _peer_as_player(self, peer: Peer) -> Player | None:
        """Gets a Player object associated with the given peer if the lobby and game status are available.

        Args:
            peer (Peer): The peer to convert.

        Returns:
            Player | None: The Player object associated with the peer, or None if not found.
        """
        if self._lobby and self._game_status:
            return next(
                player for player in self._game_status.players if player.id == peer.uuid
            )
        return None

    def set_username(self, username: str):
        """Sets the username for the local player.

        Args:
            username (str): The username to set.
        """
        self._my_self = Peer(username)

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
        if self.lobby is not None:
            (
                self._server,
                self._client_connection_handler,
            ) = await GameServerFactory.get_game_server(self.lobby)
            self._client_connection_handler.set_on_message(self._on_message)
            await self._client_connection_handler.start_receiving()
            await self._server.start_listening()
            self._lobby_browser = LobbyBrowserFactory.get_lobby_browser()
            await self._lobby_browser.publish_lobby(
                self._lobby.lobby_info(), DEFAULT_SERVER_PORT
            )
            return self.lobby
        else:
            raise RuntimeError("Failed to create lobby.")

    async def leave(self) -> None:
        """Leaves the current lobby and shuts down the server if applicable."""
        # Checks if this controller has a server to shut down
        if self._server:
            await self._server.close()
            self._server = None
        # Checks if this controller is publishing a lobby
        if self._lobby_browser.is_publishing_lobby:
            await self.stop_publishing_lobby()
        # Checks if this controller has a client connection to close
        if self._client_connection_handler:
            await self._client_connection_handler.close()
            self._client_connection_handler = None
        # Reset the lobby status
        self._lobby = None

    async def stop_publishing_lobby(self):
        """Stops publishing the lobby."""
        if self._lobby:
            await self._lobby_browser.stop_publishing_lobby()

    async def join_lobby(
        self, lobby_name: LobbyInfo, lobby_password: str | None
    ) -> Lobby:
        """Joins a lobby by its name.

        Args:
            lobby_name (LobbyInfo): The info of the lobby to join.
            lobby_password (str | None): The password for the lobby or None if no password is set.
        """
        (
            self._client_connection_handler,
            self._lobby,
        ) = await self._lobby_browser.connect_to_lobby_by_id(
            self._my_self, lobby_name.uuid, lobby_password
        )
        self._client_connection_handler.set_on_message(self._on_message)
        await self._client_connection_handler.start_receiving()
        return self._lobby

    def start_listening_for_lobbies(self) -> None:
        def remove_and_readd_lobby(lobby_info: LobbyInfo):
            """Removes and re-adds a lobby to the discovered lobbies list. This is used to update the
            lobby information when it changes."""
            self._event_sender.remove_discovered_lobby(lobby_info)
            self._event_sender.new_discovered_lobby(lobby_info)

        """Starts listening for available lobbies."""
        self._lobby_browser.start_lobby_browser(
            lambda lobby_info: self._event_sender.new_discovered_lobby(lobby_info),
            lambda lobby_info: self._event_sender.remove_discovered_lobby(lobby_info),
            lambda lobby_info: remove_and_readd_lobby(lobby_info),
        )

    def stop_listening_for_lobbies(self) -> None:
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
            case LobbyUpdatedMessage():
                self._logger.info("Lobby information updated.")
                old_lobby = self._lobby
                self._lobby = message.lobby
                if old_lobby:
                    # If it's an update and not the first time lobby is sent, notify the view about who left or joined the lobby
                    joined_users = self._lobby.peers - old_lobby.peers
                    left_users = old_lobby.peers - self._lobby.peers
                    for user in joined_users:
                        self._event_sender.new_user_in_lobby(user)
                    for user in left_users:
                        self._event_sender.remove_user_in_lobby(user)
            case GameStartedMessage():
                self._logger.info("Game has started.")
                self._game_status = message.status
                self._event_sender.game_started_by_master()
                myself = self.my_self_as_player()
                if myself is not None:
                    self._event_sender.user_role(
                        myself.role.role_name, ""
                    )  # TODO: Add role description
                self._event_sender.start_first_day()  # TODO: Shouldn't this be view logic?
            case PhaseAdvanceMessage():
                self._logger.info("Game phase has advanced, updating game status.")
                self._game_status = message.game_status
                if message.outcome.someone_died():
                    self._logger.info("A player has died this phase.")
                    for player in message.outcome.deaths:
                        self._event_sender.display_chat_message(f"{player} has died.")
                        if self.my_self.uuid == player.id:
                            self._event_sender.player_is_dead()
                match message.outcome.new_phase:
                    case GamePhase.DAY_DISCUSSION:
                        self._event_sender.end_night()
                    case GamePhase.DAY_ACCUSING:
                        if self._game_status is not None:
                            votable_peers = [
                                Peer(player.name, player.id)
                                for player in self._game_status.players
                                if player.is_alive() and player.id != self._my_self.uuid
                            ]
                            self._event_sender.start_nomination_for_execution(
                                votable_peers
                            )
                        else:
                            self._logger.error("Game status is not available.")
                    case GamePhase.DAY_BALLOT:
                        accused_player = message.outcome.get_accused_player()
                        if (
                            self._game_status is not None
                            and self.lobby is not None
                            and accused_player is not None
                        ):
                            peer = next(
                                (
                                    peer
                                    for peer in self.lobby.peers
                                    if peer.uuid == accused_player.id
                                )
                            )
                            self._event_sender.user_to_nominated_for_ballot(peer)
                        else:
                            self._logger.error(
                                "Game status, lobby, or accused player is not available."
                            )
                    case GamePhase.NIGHT:
                        if (message.outcome.someone_died()):
                            self._logger.info("Day ballot phase ended with an execution.")
                            for player in message.outcome.deaths:
                                self._event_sender.message_player_executed(player.name)
                        if self._game_status is not None:
                            my_self = self.my_self_as_player()
                            if my_self is not None and self.lobby is not None:
                                self._event_sender.start_night(
                                    my_self.role is BasicRole.VILLAGER
                                )
                                self._event_sender.can_use_powers_on(
                                    [
                                        peer
                                        for peer in self.lobby.peers
                                        if self._peer_as_player(peer)
                                        in can_perform_action_on(
                                            my_self, self._game_status
                                        )
                                    ]
                                )
                    case GamePhase.VILLAGERS_VICTORY | GamePhase.WEREWOLVES_VICTORY:
                        self._logger.info("Game has ended with a victory.")
                        if message.outcome.new_phase == GamePhase.VILLAGERS_VICTORY:
                            self._event_sender.villager_win()
                        elif message.outcome.new_phase == GamePhase.WEREWOLVES_VICTORY:
                            self._event_sender.werewolf_win()
            case ChatMessage():
                self._logger.info(
                    "Chat message received from %s: %s", message.sender, message.message
                )
                if message.sender and message.message:
                    self._event_sender.display_chat_message(
                        f"{message.sender.name}: {message.message}"
                    )
                else:
                    self._logger.warning(
                        "Received chat message with missing sender or message content."
                    )
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
        try:
            await self._send_message_and_wait_for_ack(StartGameMessage(self._my_self))
            await self.stop_publishing_lobby()
        except Exception as e:
            self._logger.error("Failed to start game: %s", e)
            raise

    async def choose_player(self, player: Peer):
        """Chooses a player in the lobby. This method may be called only during a voting phase or during the night phase if the player can do an action.

        Args:
            player (Peer): The player to choose.
        """
        await self._send_message_and_wait_for_ack(
            VotePlayerMessage(self._my_self, player.uuid)
        )

    async def vote_guilty(self):
        """Votes for the selected player to be guilty. This method may be called only during a
        guilty decision voting phase."""
        # TODO: Change this and vote_innocent to a single method that takes a boolean parameter, since the logic is the same for both
        await self._send_message_and_wait_for_ack(
            VoteBallotMessage(self._my_self, True)
        )

    async def vote_innocent(self):
        """Votes for the selected player to be innocent. This method may be called only during a
        guilty decision voting phase."""
        # TODO: Change this and vote_guilty to a single method that takes a boolean parameter, since the logic is the same for both
        await self._send_message_and_wait_for_ack(
            VoteBallotMessage(self._my_self, False)
        )


class ControllerFactory:
    @staticmethod
    def get_controller(
        browser: LobbyBrowser, event_sender: EventSender
    ) -> GameController:
        """Creates and returns a new GameController instance.

        Args:
            browser (LobbyBrowser): The lobby browser to use.
            event_sender (EventSender): The event sender to use.
        Returns:
            GameController: The created game controller.
        """
        return GameController(browser, event_sender)
