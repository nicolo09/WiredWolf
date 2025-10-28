from wiredwolf.controller.connections import ClientConnectionHandler
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser
from wiredwolf.controller.lobbies import Lobby
from wiredwolf.controller.messages import ChatMessage
from wiredwolf.controller.server import GameServer
from wiredwolf.controller.commons import DEFAULT_SERVER_PORT, Peer


class GameController:
    """Handles the game logic and player interactions. This controller is implemented by means of
    TCP connections and mDNS for lobby discovery.
    """

    def __init__(self):
        self._lobby_browser: TcpMdnsLobbyBrowser = TcpMdnsLobbyBrowser()
        self._lobby: Lobby | None = None
        self._server: GameServer | None = None
        # TODO: Default name, should be set by user
        self._my_self: Peer = Peer("Player")
        self._client_connection_handler: ClientConnectionHandler | None = None

    def create_lobby(self, name: str, password: str | None = None):
        """Creates a new lobby.

        Args:
            name (str): The name of the lobby.
            password (str | None, optional): The lobby password or None if no password is set.

        Raises:
            RuntimeError: If the lobby could not be created.

        Returns:
            Lobby: The created lobby.
        """
        self._lobby = Lobby(name=name, password=password)
        self._server = GameServer(self._lobby)
        self._lobby_browser.publish_lobby(self._lobby.name, DEFAULT_SERVER_PORT)
        return self._lobby

    async def join_lobby(self, lobby_name: str, lobby_password: str | None):
        """Joins a lobby by its name.

        Args:
            lobby_name (str): The name of the lobby to join.
            lobby_password (str | None): The password for the lobby or None if no password is set.
        """
        self._client_connection_handler, self._lobby = await (
            self._lobby_browser.connect_to_lobby_by_name(
                self._my_self, lobby_name, lobby_password
            )
        )

    @property
    def lobby_browser(self) -> TcpMdnsLobbyBrowser:
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

    def send_chat_message(self, message: str):
        """Sends a chat message to all peers in the lobby.

        Args:
            message (str): The chat message to send.
        """
        if self._client_connection_handler is None:
            raise RuntimeError("Not connected to a lobby.")
        self._client_connection_handler.send_obj(ChatMessage(self._my_self, message))

    def choose_player(self, player: Peer):
        """Votes a player in the lobby. This method may be called only during a voting phase.

        Args:
            player (Peer): The player to choose.
        """
        # TODO: Implement player selection logic
        pass

    def vote_guilty(self):
        """Votes for the selected player to be guilty. This method may be called only during a
        guilty decision voting phase."""
        # TODO: Implement voting logic
        pass

    def vote_innocent(self):
        """Votes for the selected player to be innocent. This method may be called only during a
        guilty decision voting phase."""
        # TODO: Implement voting logic
        pass
