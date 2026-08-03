from wiredwolf.model.game_phases import *
from wiredwolf.model.player import *
from wiredwolf.model.exceptions import *
from wiredwolf.model.game_template import AbstractGameInfo, GameActionData
from wiredwolf.model.game_builder import GameInfoBuilder


@dataclass(frozen=True)
class GameStatus:
    """
    Represents the status of the game, containing the current phase, players and game information.
    """

    players: list[Player]
    roles: set[Role]
    modules: set[str] 
    game_data: GameActionData
    phase: GamePhase
    day_count: int


# TODO: revise documentation (remove at the end)
class Game:
    """
    Represents the main game logic and state for a game of WiredWolf.

    This class manages the list of players, the current phase, and delegates
    rule-specific logic to the provided AbstractGameInfo instance. It provides
    methods to advance the game phase, handle player actions, accusations, voting,
    and player elimination.
    """

    def __init__(
        self,
        players: list[Player],
        game_info: AbstractGameInfo,
        phase: GamePhase = GamePhase.FIRST_DAY,
        day_count: int = 1,
    ):
        """
        Initialize a new game instance.

        Args:
            players (list[Player]): List of Player objects participating in the game.
            game_info (AbstractGameInfo): The information to handle game rules, votes, and actions.
            phase (GamePhase): The starting phase of the game. Defaults to FIRST_DAY.
            day_count (int): The current day count. Defaults to 1.
        """
        self._players: list[Player] = players
        self._phase: GamePhase = phase
        self._game_info: AbstractGameInfo = game_info
        self._day_count: int = day_count
        self._phase_outcome_builder: GamePhaseOutcomeBuilder = GamePhaseOutcomeBuilder()
        self._snapshot: GameStatus = self.get_game_status()

    @classmethod
    def from_game_status(cls, game_status: GameStatus) -> "Game":
        """
        Create a Game instance from a GameStatus object.

        Args:
            game_status (GameStatus): The game status to initialize the Game instance.

        Returns:
            Game: A new Game instance initialized with the provided game status.
        """
        return cls(
            game_status.players,
            GameInfoBuilder.with_game_data(
                game_status.game_data, game_status.players
            )
            .add_decorator_module(*game_status.modules)
            .with_roles(game_status.roles)
            .build(),
            game_status.phase,
            game_status.day_count,
        )

    @property
    def phase(self) -> GamePhase:
        """Get the current game phase."""
        return self._phase

    @property
    def players(self) -> list[Player]:
        """Return a copy of the players list."""
        return self._players.copy()
    
    @property
    def day_count(self) -> int:
        """Get the current day count."""
        return self._day_count

    def get_game_status(self) -> GameStatus:
        """
        Creates a GameStatus object representing the current state of the game.

        Returns:
            GameStatus: The current game status.
        """
        return GameStatus(
            self._players.copy(),
            self._game_info.get_all_handled_roles(),
            self._game_info.get_game_modules(),
            self._game_info.get_game_data(),
            self._phase,
            self._day_count,
        )
    
    def get_game_snapshot(self) -> GameStatus:
        """
        Get the last stable state of the game.
        Snapshot is updated at the start of each phase, before any actions are performed.

        Returns:
            GameStatus: The last saved snapshot of the game status.
        """
        return self._snapshot


    def advance_phase(self) -> GamePhaseOutcome:
        """
        Advance to the next game phase based on current state.

        - FIRST_DAY -> NIGHT
        - DAY_DISCUSSION -> DAY_ACCUSING
        - DAY_ACCUSING -> DAY_BALLOT (if single player has most votes) or NIGHT (if tie/no votes)
        - DAY_BALLOT -> BALLOT_RESULT (after processing ballot votes)
        - BALLOT_RESULT -> NIGHT 
        - NIGHT -> DAY_DISCUSSION (after processing werewolf attacks and resetting for new day)

        Returns:
            GamePhaseOutcome: contains the new game phase and any deaths that occurred during the transition.
        """
        self._snapshot = self.get_game_status()

        match self._phase:
            case GamePhase.FIRST_DAY:
                self._phase = GamePhase.NIGHT
            case GamePhase.DAY_DISCUSSION:
                self._phase = GamePhase.DAY_ACCUSING

            case GamePhase.DAY_ACCUSING:

                accused_player: Player | None = self.__get_most_voted_player(
                    self._game_info.accusation_votes
                )
                
                if (accused_player is not None):
                    self._phase = GamePhase.DAY_BALLOT
                    self._phase_outcome_builder.set_accused_player(accused_player)
                else:
                    # No votes or tie in accusations, skip to night
                    self._phase = GamePhase.NIGHT

            case GamePhase.DAY_BALLOT:

                accused_player: Player | None = self.__get_most_voted_player(
                    self._game_info.accusation_votes
                )

                if accused_player is not None:
                    # If the ballot votes are more than half of the voting players, the accused player is killed
                    self._phase_outcome_builder.set_accused_player(accused_player)
                    voting_count = len(self._game_info.ballot_votes)
                    confirm_ballot_votes = sum(
                        1 for vote in self._game_info.ballot_votes.values() if vote
                    )
                    if voting_count > 0 and confirm_ballot_votes > voting_count / 2:
                        accused_player.status = Status.DEAD
                        self._phase_outcome_builder.add_death(accused_player)
                self._phase = GamePhase.BALLOT_RESULT
                
            case GamePhase.BALLOT_RESULT:
                # This phase is just a transition to NIGHT, no actions are performed here.
                self._phase = GamePhase.NIGHT

            case GamePhase.NIGHT:
                # Get the most voted victim by werewolves (or None if tie/no votes)
                victim = self.__get_most_voted_player(self._game_info.werewolves_votes)

                if victim is not None and victim.status != Status.PROTECTED:
                    victim.status = Status.DEAD
                    self._phase_outcome_builder.add_death(victim)

                self._game_info.reset_actions()
                self._phase = GamePhase.DAY_DISCUSSION
                self._day_count += 1
                
            case _:
                # Game is over, no further phase advancement
                return GamePhaseOutcome(self._phase)

        game_over: GamePhase | None = self._game_info.end_game_conditions(self._players)
        if game_over:
            self._phase = game_over

        outcome = self._phase_outcome_builder.set_new_phase(self._phase).build()
        self._phase_outcome_builder.reset()  # Reset the builder for the next phase
        return outcome

    def perform_night_action(self, actor_id: str, target_id: str) -> NightActionResult:
        """
        Perform a night action for a given actor and target, according to their roles.

        Args:
            actor_id (str): The ID of the player performing the action.
            target_id (str): The ID of the target player.

        Returns:
            NightActionResult: Result of the action, containing success status and optionally a message.

        Raises:
            GamePhaseError: If not in NIGHT phase
            MissingPlayerError: If actor or target does not exist.
        """
        if self._phase != GamePhase.NIGHT:
            raise GamePhaseError(
                f"Night actions can only be performed during the NIGHT phase. Now is {self._phase}."
            )

        actor: Player | None = self.__get_player_from_id(actor_id)
        if actor is None:
            raise MissingPlayerError(f"Player with ID {actor_id} does not exist.")

        target: Player | None = self.__get_player_from_id(target_id)
        if target is None:
            raise MissingPlayerError(f"Target with ID {target_id} does not exist.")

        return self._game_info.handle_night_actions(actor, target)

    def accuse_player(self, voter_id: str, target_id: str) -> None:
        """
        Cast an accusation vote against a player during the accusing phase.

        Args:
            voter_id (str): The ID of the player casting the vote.
            target_id (str): The ID of the player to accuse.

        Raises:
            GamePhaseError: If not in DAY_ACCUSING phase
            MissingPlayerError: If voter/target does not exist.
        """
        if self._phase != GamePhase.DAY_ACCUSING:
            raise GamePhaseError(
                f"Accusations can only be made during the DAY_ACCUSING phase. Now is {self._phase}."
            )

        voter: Player | None = self.__get_player_from_id(voter_id)

        if voter is None:
            raise MissingPlayerError(f"Voter with ID {voter_id} does not exist.")

        target: Player | None = self.__get_player_from_id(target_id)

        if target is None:
            raise MissingPlayerError(f"Target with ID {target_id} does not exist.")

        self._game_info.handle_accusation_vote(voter, target)

    def ballot_vote(self, voter_id: str, vote: bool) -> None:
        """
        Cast a confirmation vote during the ballot phase.

        Args:
            voter_id (str): The ID of the player voting.
            vote (bool): True to confirm the accusation, False to reject.

        Raises:
            GamePhaseError: If not in DAY_BALLOT phase
            MissingPlayerError: If voter does not exist or is not alive.
        """
        if self._phase != GamePhase.DAY_BALLOT:
            raise GamePhaseError(
                f"Ballots can only be confirmed during the DAY_BALLOT phase. Now is {self._phase}."
            )

        voter: Player | None = self.__get_player_from_id(voter_id)

        if voter is None:
            raise MissingPlayerError(
                f"Player with ID {voter_id} does not exist or is not alive."
            )

        self._game_info.handle_ballot_vote(voter, vote)

    def kill_player(self, player_id: str) -> GamePhase: #TODO: this method must be called AFTER calling advance_phase of the snapshot, otherwise valid actions would be removed
        """
        Kills a player in any moment of the game and cancels any action performed by that player in the current phase.
        How the elimination is handled is defined by the GameInfo object.

        Should only be used by the game controller to remove a player from the game.
        Args:
            player_id: ID of the player to kill.

        Returns:
            GamePhase: The new game phase after the player has been killed.

        Raises:
            MissingPlayerError: If player does not exist.
        """
        player: Player | None = self.__get_player_from_id(player_id)

        if not player:
            raise MissingPlayerError(f"Player with ID {player_id} does not exist.")

        if player.is_alive():

            self._game_info.remove_player(player, self._phase)
            if (
                self._phase == GamePhase.DAY_BALLOT
                and player
                == self.__get_most_voted_player(self._game_info.accusation_votes)
            ):
                self._phase = GamePhase.NIGHT

            game_over: GamePhase | None = self._game_info.end_game_conditions(
                self._players
            )
            if game_over:
                self._phase = game_over
                
        self._phase_outcome_builder.add_death(player)
        return self._phase
    
    def set_player_as_dead(self, player_id: str) -> None:
        """
        Sets a player's status to DEAD, but doesn't cancel any actions performed by that player in the current phase.

        Args:
            player_id (str): The ID of the player to set as dead.

        Raises:
            MissingPlayerError: If player does not exist.
        """
        player: Player | None = self.__get_player_from_id(player_id)

        if not player:
            raise MissingPlayerError(f"Player with ID {player_id} does not exist.")

        player.status = Status.DEAD
        self._phase_outcome_builder.add_death(player)

    def __get_player_from_id(self, player_id: str) -> Player | None:
        """
        Get a player by their ID.

        Args:
            player_id (str): The ID of the player to retrieve.

        Returns:
            (Player | None): The Player object if found, None otherwise.
        """
        return next(
            (player for player in self._players if player.id == player_id), None
        )

    def __get_most_voted_player(self, votes: dict[Player, Player]) -> Player | None:
        """
        Get the player with the most votes from a voting dictionary.

        Args:
            votes (dict[Player, Player]): Dictionary mapping voters to their chosen targets.

        Returns:
            (Player | None): The player with the most votes, or None if there's a tie or no votes were cast.
        """
        if not votes:
            return None

        # Count votes for each target
        from collections import Counter

        vote_counts = Counter(votes.values())

        # Find the maximum vote count
        max_votes = max(vote_counts.values())

        # Get all players with the maximum vote count
        most_voted_players = [
            player for player, count in vote_counts.items() if count == max_votes
        ]

        # Return the player only if there's exactly one winner
        return most_voted_players[0] if len(most_voted_players) == 1 else None


def can_perform_action_on(player: Player, game_status: GameStatus) -> list[Player]:
    """Helper function to determine possible targets for a player's night action based on their role and the current game status.

    Args:
        player (Player): The player for whom to determine possible action targets.
        game_status (GameStatus): The current status of the game.

    Returns:
        list[Player]: A list of players that the given player can target with their night action.
    """

    game_info: AbstractGameInfo = (
        GameInfoBuilder.with_game_data(game_status.game_data, game_status.players)
        .with_roles(game_status.roles)
        .build()
    )
    return game_info.get_possible_targets(player.role, game_status.players)
