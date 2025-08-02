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


# TODO: add reference to controller so it can be notified of changes
# or does the controller only consult the model?
# TODO: should the game check for the right number of players/roles?
# TODO: move role logic to "GameRules" class
class Game:
    def __init__(self, players: list[Player]):
        """
        Initialize a new game instance.

        Args:
            players: List of Player objects.
        """
        self._players: list[Player] = players
        self._phase: GamePhase = GamePhase.DAY_DISCUSSION

        self._accusing_votes: dict[Player, Player] = {}
        self._current_accusation: Player | None = None
        self._protected_player: Player | None = None
        self._wolves_votes: dict[Player, Player] = {}
        self._ballot_votes: dict[Player, bool] = {}

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
        Advance to the next game phase based on current state and game logic.
        
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
                # Get the player, or players, with the most votes

                # Count occurrences of each voted player
                vote_counts: Counter = Counter(self._accusing_votes.values())
                if not vote_counts:
                    # No votes cast, skip to night
                    self._phase = GamePhase.NIGHT
                    return self._phase

                # FIXME: implement this better
                max_votes: int = max(vote_counts.values())
                accused_players: list[Player] = [
                    name for name, count in vote_counts.items() if count == max_votes
                ]

                if len(accused_players) == 1:
                    self._phase = GamePhase.DAY_BALLOT
                    self._current_accusation = accused_players[0]
                else:
                    # Tie in accusations, skip to night
                    self._phase = GamePhase.NIGHT

            case GamePhase.DAY_BALLOT:
                if self._current_accusation is not None:
                    # If the ballot votes are more than half of the voting players, the accused player is killed
                    voting_count = len(self._ballot_votes)
                    confirm_ballot_votes = sum(
                        1 for vote in self._ballot_votes.values() if vote
                    )
                    if voting_count > 0 and confirm_ballot_votes >= voting_count / 2:
                        self._current_accusation.status = Status.DEAD
                    self._current_accusation = None
                self._phase = GamePhase.NIGHT

            case GamePhase.NIGHT:
                vote_counts: Counter = Counter(self._wolves_votes.values())
                if vote_counts:
                    max_votes: int = max(vote_counts.values())
                    if max_votes > 0:
                        wolves_victims = [
                            name
                            for name, votes in vote_counts.items()
                            if votes == max_votes
                        ]
                        if len(wolves_victims) == 1:
                            victim = wolves_victims[0]
                            if victim.status != Status.PROTECTED:
                                victim.status = Status.DEAD
                self.__setup_new_day()
                self._phase = GamePhase.DAY_DISCUSSION
            case _:
                pass

        self.__check_victory_conditions()
        return self._phase

    def __setup_new_day(self) -> None:
        """
        Reset game state for a new day phase.

        Resets all voting counters and removes protection status from any protected player.
        """
        # Resetting votes and accusations for the new day phase
        self._accusing_votes = {}
        self._wolves_votes = {}
        self._ballot_votes = {}

        # Protected players are no longer protected
        if self._protected_player is not None:
            self._protected_player.status = Status.ALIVE
            self._protected_player = None

    def perform_night_action(self, actor_id: str, target_id: str) -> bool | None:
        """
        Perform a night action based on the actor's role.
        
        Args:
            actor_id: ID of the player performing the action.
            target_id: ID of the target player.
        
        Returns:
            - True/False for clairvoyant/medium actions (indicating if target is/was werewolf)
            - None for werewolf/escort actions
        
        Raises:
            ValueError: If not in NIGHT phase, actor doesn't exist/is dead, or invalid target.
        """
        
        if self._phase != GamePhase.NIGHT:
            raise ValueError("Night actions can only be performed during the NIGHT phase.")

        actor: Player | None = self.__get_player_from_id(actor_id)
        if (actor is None or not actor.is_alive()):
            raise ValueError(f"Player with ID {actor_id} does not exist or is not alive.")

        match actor.role:
            case Role.WEREWOLF:
                self.__werewolf_action(target_id, actor)
            case Role.ESCORT:
                self.__escort_action(target_id)
            case Role.CLAIRVOYANT:
                return self.__clairvoyant_action(target_id)
            case Role.MEDIUM:
                return self.__medium_action(target_id)
            case _:
                raise ValueError(f"Unknown role: {actor.role}")
        
        return None

    def accuse_player(self, voter_id: str, target_id: str) -> None:
        """
        Cast an accusation vote against a player during the accusing phase.
        Each alive player can cast one vote to accuse another alive player.

        Args:
            voter_id: ID of the player casting the accusation vote.
            target_id: ID of the player being accused.

        Raises:
            ValueError: If not in DAY_ACCUSING phase, voter/target doesn't exist,
                    voter is dead, target is dead, or voter has already voted.
        """
        # FIXME: better separate checks and get right voter entry
        if self._phase == GamePhase.DAY_ACCUSING:
            voter: Player | None = self.__get_player_from_id(voter_id)
            target: Player | None = self.__get_player_from_id(target_id)
            if voter is not None and target is not None:
                if (voter not in self._accusing_votes and voter.is_alive() and target.is_alive()):
                    self._accusing_votes[voter] = target
                else:
                    raise ValueError(f"Voter is dead or target cannot be accused.")
            else:
                raise ValueError(f"Voter and/or target's id does not exist.")
        else:
            raise ValueError("Accusations can only be made during the DAY_ACCUSING phase.")

    def ballot_vote(self, voter_id: str, vote: bool) -> None:
        """
        Cast a confirmation vote during the ballot phase to decide the accused player's fate.
        Each alive player can vote once to confirm (True) or reject (False) the execution.

        Args:
            voter_id: ID of the player casting the ballot vote.
            vote: True to confirm execution, False to reject.

        Raises:
            ValueError: If not in DAY_BALLOT phase, voter doesn't exist,
                    voter is dead, or voter has already voted.
        """
        # TODO: accused should automatically vote "reject" or is he excluded from voting?
        # FIXME: better separate checks
        if self._phase == GamePhase.DAY_BALLOT:
            voter: Player | None = self.__get_player_from_id(voter_id)
            if voter and voter not in self._ballot_votes and voter.is_alive():
                self._ballot_votes[voter] = vote
            else:
                raise ValueError(f"Player with ID {voter_id} does not exist or is not alive.")
        else:
            raise ValueError("Ballots can only be confirmed during the DAY_BALLOT phase.")

    def kill_player(self, player_id: str) -> None:
        """
        Immediately kill a player and clean up their votes/actions in the current phase.
        This method handles the removal of the player from all active voting processes
        and updates game state accordingly.

        Args:
            player_id: ID of the player to kill.
            
        Note:
            Should only be used by the game controller to remove a player from the game.
            Automatically checks victory conditions after killing the player.
        """
        player: Player | None = self.__get_player_from_id(player_id)
        if player and player.is_alive():
            match self._phase:
                case GamePhase.DAY_DISCUSSION:
                    player.status = Status.DEAD
                case GamePhase.DAY_ACCUSING:
                    # Remove the player from the accusing votes
                    if player in self._accusing_votes:
                        del self._accusing_votes[player]
                    for voter in self._players:
                        if self._accusing_votes.get(voter) == player:
                            del self._accusing_votes[voter]
                case GamePhase.DAY_BALLOT:
                    if player == self._current_accusation:
                        self._current_accusation = None
                        self._phase = GamePhase.NIGHT #FIXME: should happen here?
                    else:
                        del self._ballot_votes[player]
                case GamePhase.NIGHT:
                    if player.role == Role.WEREWOLF and player in self._wolves_votes:
                        del self._wolves_votes[player]
                    for werewolf in self._wolves_votes:
                        if self._wolves_votes[werewolf] == player:
                            del self._wolves_votes[werewolf]
                    if player == self._protected_player:
                        self._protected_player = None
                        
            player.status = Status.DEAD
            self.__check_victory_conditions()

    #TODO: if possible move action methods to own file

    def __werewolf_action(self, target_id: str, werewolf: Player) -> None:
        """
        Record a werewolf's vote to kill the selected player during the night phase.
        Each werewolf can vote once per night to kill a non-werewolf player.

        Args:
            target_id: ID of the player to vote to kill.
            werewolf: The werewolf player casting the vote.

        Raises:
            ValueError: If target doesn't exist, is dead, is a werewolf,
                    or the werewolf has already voted.
        """
        if werewolf not in self._wolves_votes:
            target: Player | None = self.__get_player_from_id(target_id)
            if target and target.is_alive() and target.role != Role.WEREWOLF:
                self._wolves_votes[werewolf] = target
            else:
                raise ValueError(f"Player {target_id} cannot be killed or does not exist.")

    def __escort_action(self, target_id: str) -> None:
        """
        Protect a player from werewolf attacks for the current night.
        Only one player can be protected per night, and protection lasts until the next day.

        Args:
            target_id: ID of the player to protect.

        Raises:
            ValueError: If target doesn't exist, is dead, or a player is already protected.
        """
        target: Player | None = self.__get_player_from_id(target_id)
        if target and target.status == Status.ALIVE and self._protected_player is None:
            target.status = Status.PROTECTED
            self._protected_player = target
        else:
            raise ValueError(f"Player with ID {target_id} cannot be protected or does not exist.")

    def __clairvoyant_action(self, target_id: str) -> bool:
        """
        Check if a living player is a werewolf.

        Args:
            target_id: ID of the alive player to investigate.

        Returns:
            True if the target player is a werewolf, False otherwise.

        Raises:
            ValueError: If target doesn't exist or is not alive.
        """
        target: Player | None = self.__get_player_from_id(target_id)
        if target and target.is_alive():
            return target.role == Role.WEREWOLF
        else:
            raise ValueError(f"Player with ID {target_id} cannot be checked or does not exist.")

    def __medium_action(self, target_id: str) -> bool:
        """
        Check if a dead player was a werewolf.

        Args:
            target_id: ID of the dead player to investigate.

        Returns:
            True if the dead player was a werewolf, False otherwise.

        Raises:
            ValueError: If target doesn't exist or is not dead.
        """
        target: Player | None = self.__get_player_from_id(target_id)
        if target and target.status == Status.DEAD:
            return target.role == Role.WEREWOLF
        else:
            raise ValueError(f"Player with ID {target_id} cannot be checked or does not exist.")

    def __check_victory_conditions(self) -> None:
        """
        Evaluate current game state to determine if victory conditions are met.
        Sets the game phase to VILLAGERS_VICTORY if no werewolves remain alive,
        or WEREWOLVES_VICTORY if no villagers remain alive or protected.
        """
        if self._phase not in (GamePhase.VILLAGERS_VICTORY, GamePhase.WEREWOLVES_VICTORY):
            werewolves: list[Player] = [
                player
                for player in self._players
                if player.role == Role.WEREWOLF and player.status == Status.ALIVE
            ]
            villagers: list[Player] = [
                player
                for player in self._players
                if player.role != Role.WEREWOLF and (player.status == Status.ALIVE or player.status == Status.PROTECTED)
            ]

            if not werewolves:
                self._phase = GamePhase.VILLAGERS_VICTORY
            elif not villagers:
                self._phase = GamePhase.WEREWOLVES_VICTORY
            
    def __get_player_from_id(self, player_id: str) -> Player | None:
        """
        Get a player by their ID.

        Args:
            player_id: The ID of the player to retrieve.

        Returns:
            The Player object if found, None otherwise.
        """
        return next((player for player in self._players if player.id == player_id), None)
