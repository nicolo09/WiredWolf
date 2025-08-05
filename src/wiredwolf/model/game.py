from enum import Enum
from collections import Counter
from wiredwolf.model.player import Player, Status, Role

class GamePhase(Enum):
    DAY_DISCUSSION = 1
    DAY_ACCUSING = 2
    DAY_BALLOT = 3
    NIGHT = 4
    VILLAGERS_VICTORY = 5
    WEREWOLVES_VICTORY = 6
    
from wiredwolf.model.game_modifiers import AbstractGameInfo

class GameStatus:
    """
    Represents the status of the game, including the current phase, players and game information.
    """

    def __init__(self, players: list[Player], game_info: AbstractGameInfo, phase: GamePhase = GamePhase.DAY_DISCUSSION):
        self._players = players
        self._game_info = game_info
        self.phase = phase
        
    @property
    def players(self) -> list[Player]:
        """        
        Returns:
            list[Player]: The players in the game.
        """
        return self._players
    
    @property
    def game_info(self) -> AbstractGameInfo:
        """
        Returns:
            AbstractGameInfo: The game information handling rules, votes, and actions.
        """
        return self._game_info
    


# TODO: add reference to controller so it can be notified of changes
# or does the controller only consult the model?
# TODO: should the game check for the right number of players/roles? I think not
# TODO: revise documentation
class Game:
    """
    Represents the main game logic and state for a game of WiredWolf.

    This class manages the list of players, the current phase, and delegates
    rule-specific logic to the provided AbstractGameInfo instance. It provides
    methods to advance the game phase, handle player actions, accusations, voting,
    and player elimination.
    """
    def __init__(self, players: list[Player], game_info: AbstractGameInfo, phase: GamePhase = GamePhase.DAY_DISCUSSION):
        """
        Initialize a new game instance.

        Args:
            players (list[Player]): List of Player objects participating in the game.
            game_info (AbstractGameInfo): The information to handle game rules, votes, and actions.
        """
        self._players: list[Player] = players
        self._phase: GamePhase = phase
        self._game_info: AbstractGameInfo = game_info

        self._current_accusation: Player | None = None
        
    @classmethod
    def from_game_status(cls, game_status: GameStatus) -> "Game":
        """
        Create a Game instance from a GameStatus object.

        Args:
            game_status (GameStatus): The game status to initialize the Game instance.

        Returns:
            Game: A new Game instance initialized with the provided game status.
        """
        return cls(game_status.players, game_status.game_info, game_status.phase)

    @property
    def phase(self) -> GamePhase:
        """Get the current game phase."""
        return self._phase

    @property
    def players(self) -> list[Player]:
        """Return a copy of the players list."""
        return self._players.copy()


    def advance_phase(self) -> GamePhase:
        """
        Advance to the next game phase based on current state.
        
        - DAY_DISCUSSION -> DAY_ACCUSING
        - DAY_ACCUSING -> DAY_BALLOT (if single player has most votes) or NIGHT (if tie/no votes)
        - DAY_BALLOT -> NIGHT (after processing execution vote)
        - NIGHT -> DAY_DISCUSSION (after processing werewolf attacks and resetting for new day)
        
        Returns:
            The new game phase after advancement.
        """

        match self._phase:
            case GamePhase.DAY_DISCUSSION:
                self._phase = GamePhase.DAY_ACCUSING

            case GamePhase.DAY_ACCUSING:
                # Get the player with the most votes (or None if tie/no votes)
                accused_player = self.__get_most_voted_player(self._game_info.accusation_votes)
                
                if accused_player is not None:
                    self._phase = GamePhase.DAY_BALLOT
                    self._current_accusation = accused_player
                else:
                    # No votes or tie in accusations, skip to night
                    self._phase = GamePhase.NIGHT

            case GamePhase.DAY_BALLOT:
                if self._current_accusation is not None:
                    # If the ballot votes are more than half of the voting players, the accused player is killed
                    voting_count = len(self._game_info.ballot_votes)
                    confirm_ballot_votes = sum(
                        1 for vote in self._game_info.ballot_votes.values() if vote
                    )
                    if voting_count > 0 and confirm_ballot_votes > voting_count / 2:
                        self._current_accusation.status = Status.DEAD
                    self._current_accusation = None
                self._phase = GamePhase.NIGHT

            case GamePhase.NIGHT:
                # Get the most voted victim by werewolves (or None if tie/no votes)
                victim = self.__get_most_voted_player(self._game_info.werewolves_votes)
                
                if victim is not None and victim.status != Status.PROTECTED:
                    victim.status = Status.DEAD
                    
                self._game_info.reset_actions()
                self._phase = GamePhase.DAY_DISCUSSION
            case _:
                return self._phase

        game_over: GamePhase | None = self._game_info.end_game_conditions(self._players)
        if game_over:
            self._phase = game_over
            
        return self._phase

    def perform_night_action(self, actor_id: str, target_id: str) -> bool | None:
        """
        Perform a night action for a given actor and target, according to their roles.

        Args:
            actor_id (str): The ID of the player performing the action.
            target_id (str): The ID of the target player.

        Returns:
            True/False for clairvoyant/medium actions, None for others.

        Raises:
            ValueError: If not in NIGHT phase, or if actor/target does not exist.
        """
        if self._phase != GamePhase.NIGHT:
            raise ValueError("Night actions can only be performed during the NIGHT phase.")

        actor: Player | None = self.__get_player_from_id(actor_id)
        if actor is None:
            raise ValueError(f"Player with ID {actor_id} does not exist.")
        
        target: Player | None = self.__get_player_from_id(target_id)
        if target is None:
            raise ValueError(f"Target with ID {target_id} does not exist.")

        return self._game_info.handle_night_actions(actor, target)

    def accuse_player(self, voter_id: str, target_id: str) -> None:
        """
        Cast an accusation vote against a player during the accusing phase.

        Args:
            voter_id (str): The ID of the player casting the vote.
            target_id (str): The ID of the player to accuse.

        Raises:
            ValueError: If not in DAY_ACCUSING phase, or if voter/target does not exist.
        """
        if self._phase != GamePhase.DAY_ACCUSING:
            raise ValueError("Accusations can only be made during the DAY_ACCUSING phase.")
        
        voter: Player | None = self.__get_player_from_id(voter_id)
        
        if voter is None:
            raise ValueError(f"Voter with ID {voter_id} does not exist.")

        target: Player | None = self.__get_player_from_id(target_id)
        
        if target is None:
            raise ValueError(f"Target with ID {target_id} does not exist.")
        
        self._game_info.handle_accusation_vote(voter, target)

    def ballot_vote(self, voter_id: str, vote: bool) -> None:
        """
        Cast a confirmation vote during the ballot phase.

        Args:
            voter_id (str): The ID of the player voting.
            vote (bool): True to confirm the accusation, False to reject.

        Raises:
            ValueError: If not in DAY_BALLOT phase, or if voter does not exist.
        """
        if self._phase != GamePhase.DAY_BALLOT:
            raise ValueError("Ballots can only be confirmed during the DAY_BALLOT phase.")
        
        voter: Player | None = self.__get_player_from_id(voter_id)
        
        if voter is None:
            raise ValueError(f"Player with ID {voter_id} does not exist or is not alive.")
        
        self._game_info.handle_ballot_vote(voter, vote)

    def kill_player(self, player_id: str) -> None:
        """
        Kills a player in any moment of the game.
        If the player has already cast a vote or performed an action this will not be canceled.

        Should only be used by the game controller to remove a player from the game.
        Args:
            player_id: ID of the player to kill.
        """
        # TODO: This shouldn't be here, probably should be in the controller
        player: Player | None = self.__get_player_from_id(player_id)
        if player and player.is_alive():
            match self._phase:
                case GamePhase.DAY_DISCUSSION:
                    player.status = Status.DEAD
                case GamePhase.DAY_ACCUSING:
                    # Remove the player from the accusing votes
                    if player in self._game_info.accusation_votes:
                        del self._game_info.accusation_votes[player]
                    for voter in self._players:
                        if self._game_info.accusation_votes.get(voter) == player:
                            del self._game_info.accusation_votes[voter]
                case GamePhase.DAY_BALLOT:
                    if player == self._current_accusation:
                        self._current_accusation = None
                        self._phase = GamePhase.NIGHT #FIXME: should happen here?
                    else:
                        del self._game_info.ballot_votes[player]
                case GamePhase.NIGHT:
                    if player.role == Role.WEREWOLF and player in self._game_info.werewolves_votes:
                        del self._game_info.werewolves_votes[player]
                    for werewolf in self._game_info.werewolves_votes:
                        if self._game_info.werewolves_votes[werewolf] == player:
                            del self._game_info.werewolves_votes[werewolf]
                    if player == self._protected_player:
                        self._protected_player = None
                        
            player.status = Status.DEAD
            
            game_over: GamePhase | None = self._game_info.end_game_conditions(self._players)
            if game_over:
                self._phase = game_over    
            
    def __get_player_from_id(self, player_id: str) -> Player | None:
        """
        Get a player by their ID.

        Args:
            player_id: The ID of the player to retrieve.

        Returns:
            The Player object if found, None otherwise.
        """
        return next((player for player in self._players if player.id == player_id), None)
    
    def __get_most_voted_player(self, votes: dict[Player, Player]) -> Player | None:
        """
        Get the player with the most votes from a voting dictionary.
        
        Args:
            votes: Dictionary mapping voters to their chosen targets.
            
        Returns:
            The player with the most votes, or None if there's a tie or no votes were cast.
        """
        if not votes:
            return None
            
        # Count votes for each target
        vote_counts = Counter(votes.values())
        
        # Find the maximum vote count
        max_votes = max(vote_counts.values())
        
        # Get all players with the maximum vote count
        most_voted_players = [player for player, count in vote_counts.items() if count == max_votes]
        
        # Return the player only if there's exactly one winner
        return most_voted_players[0] if len(most_voted_players) == 1 else None
