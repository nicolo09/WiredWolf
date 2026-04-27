from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, final, TypeVar, Type
from wiredwolf.model.game_phases import GamePhase, NightActionResult
from wiredwolf.model.player import Player, Status, Role, BasicRole
from wiredwolf.model.exceptions import *

# Type variable for generic decorator searching
T = TypeVar("T", bound="AbstractGameInfo")


@dataclass
class GameActionData:
    """
    Data class to hold the game action data, such as votes and role specific actions.
    """

    data: dict[str, Any]

    def compose(self, other: "GameActionData") -> "GameActionData":
        combined_data = self.data.copy()
        combined_data.update(other.data)
        return GameActionData(combined_data)


class AbstractGameInfo(ABC):
    """
    Abstract base class for managing game state, votes, and night actions.
    """

    @property
    @abstractmethod
    def accusation_votes(self) -> dict[Player, Player]:
        """Returns the current accusation votes."""

    @property
    @abstractmethod
    def ballot_votes(self) -> dict[Player, bool]:
        """Returns the current ballot votes."""

    @property
    @abstractmethod
    def werewolves_votes(self) -> dict[Player, Player]:
        """Returns the current werewolves votes."""

    @abstractmethod
    def get_game_data(self) -> GameActionData:
        """Returns a dictionary containing the game data."""

    @abstractmethod
    def reset_actions(self) -> None:
        """Clears all votes and night actions for a new round."""

    @abstractmethod
    def handle_accusation_vote(self, accuser: Player, accused: Player) -> None:
        """Handles an accusation vote from one player against another."""

    @abstractmethod
    def handle_ballot_vote(self, voter: Player, vote: bool) -> None:
        """Handles a ballot vote from a player."""

    @final
    def handle_night_actions(self, actor: Player, target: Player) -> NightActionResult:
        """
        Handles a night action performed by an actor on a target.

        Args:
            actor (Player): The player performing the action.
            target (Player): The player being targeted.


        Returns:
            NightActionResult: Result of the action contained in its message.
        """
        if actor.role not in self.get_all_handled_roles():
            raise ValueError(f"{actor.role} is unhandled.")
        return self._handle_night_actions(actor, target)

    @abstractmethod
    def _handle_night_actions(self, actor: Player, target: Player) -> NightActionResult:
        """Internal method for handling night actions. To be implemented by subclasses."""

    @abstractmethod
    def remove_player(self, player: Player, gamephase: GamePhase) -> None:
        """
        Removes a player from the game and manages the side effects based on the current game phase.

        Args:
            player (Player): The player to remove.
            gamephase (GamePhase): The current game phase.
        """

    @abstractmethod
    def end_game_conditions(self, players: list[Player]) -> GamePhase | None:
        """
        Checks if the game has ended and returns the winning phase if so.

        Args:
            players (list[Player]): List of all players.

        Returns:
            (GamePhase | None): The winning phase, or None if the game continues.
        """

    @abstractmethod
    def get_all_handled_roles(self) -> set[Role]:
        """Returns a set of roles handled by this game."""
        
    @abstractmethod
    def get_game_modules(self) -> set[str]:
        """Returns a set of module names that contain the components for this game."""
        
    @abstractmethod
    def get_possible_targets(self, role: Role, players: list[Player]) -> list[Player]:
        """Returns a list of possible targets for a given role."""

    def _find_decorator(
        self, decorator_type: Type[T], game_info: "AbstractGameInfo"
    ) -> T | None:
        """
        Recursively search through the decorator chain to find a decorator of the specified type.

        Args:
            decorator_type (Type[T]): The class type to search for
            game_info (AbstractGameInfo): The game info object to search in

        Returns:
            The decorator instance if found, None otherwise
        """
        if isinstance(game_info, decorator_type):
            return game_info
        elif hasattr(game_info, "_wrapped"):
            wrapped: Any = getattr(game_info, "_wrapped")
            if isinstance(wrapped, AbstractGameInfo):
                return self._find_decorator(decorator_type, wrapped)
        return None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractGameInfo):
            return False

        return (
            self.accusation_votes == other.accusation_votes
            and self.ballot_votes == other.ballot_votes
            and self.werewolves_votes == other.werewolves_votes
            and sorted(role.value for role in self.get_all_handled_roles())
            == sorted(role.value for role in other.get_all_handled_roles())
        )

class GameInfoBase(AbstractGameInfo):
    """
    The base for every game info implementation. Handles the core game mechanics
    without any special roles. It can be extended using decorators to
    add support for additional roles.
    """

    def __init__(
        self,
        game_data: GameActionData | None = None,
    ) -> None:
        """Initializes the SimpleGameInfo
        Args:
            game_data (GameActionData | None): Pre-existing game data to initialize from.
        """
        if game_data is not None:
            self._accusation_votes = game_data.data.get("accusation_votes", {})
            self._ballot_votes = game_data.data.get("ballot_votes", {})
            self._werewolves_votes = game_data.data.get("werewolves_votes", {})
        else:
            self._accusation_votes: dict[Player, Player] = {}
            self._ballot_votes: dict[Player, bool] = {}
            self._werewolves_votes: dict[Player, Player] = {}


    @property
    def accusation_votes(self) -> dict[Player, Player]:
        return self._accusation_votes

    @property
    def ballot_votes(self) -> dict[Player, bool]:
        return self._ballot_votes

    @property
    def werewolves_votes(self) -> dict[Player, Player]:
        return self._werewolves_votes

    def get_game_data(self) -> GameActionData:
        return GameActionData(
            {
                "accusation_votes": self._accusation_votes,
                "ballot_votes": self._ballot_votes,
                "werewolves_votes": self._werewolves_votes,
            }
        )

    def handle_accusation_vote(self, accuser: Player, accused: Player) -> None:
        if not accuser.is_alive():
            raise PlayerStatusError("Cannot accuse as dead player.")
        if not accused.is_alive():
            raise InvalidActionError("Cannot accuse dead player.")
        if accuser in self._accusation_votes:
            raise InvalidActionError(f"{accuser.id} has already voted.")
        self._accusation_votes[accuser] = accused

    def handle_ballot_vote(self, voter: Player, vote: bool) -> None:
        if not voter.is_alive():
            raise PlayerStatusError("Cannot vote as dead player.")
        if voter in self._ballot_votes:
            raise InvalidActionError(f"{voter.id} has already voted.")
        self._ballot_votes[voter] = vote

    def _handle_night_actions(self, actor: Player, target: Player) -> NightActionResult:
        if actor.role == BasicRole.WEREWOLF:
            if not actor.is_alive():
                raise PlayerStatusError(
                    f"{actor.role} cannot perform action as dead player."
                )
            if actor in self._werewolves_votes:
                raise InvalidActionError(f"{actor.id} has already voted.")
            if target.role == BasicRole.WEREWOLF:
                raise InvalidActionError("Werewolves cannot vote for other werewolves.")
            if not target.is_alive():
                raise InvalidActionError("Cannot vote for dead player.")
            self._werewolves_votes[actor] = target
        return NightActionResult(message=f"Werewolf {actor.name} voted for {target.name}.")

    def reset_actions(self) -> None:
        self._accusation_votes.clear()
        self._ballot_votes.clear()
        self._werewolves_votes.clear()

    def remove_player(self, player: Player, gamephase: GamePhase) -> None:
        match gamephase:
            case GamePhase.DAY_ACCUSING:
                if player in self._accusation_votes:
                    del self._accusation_votes[player]
                for accuser, accused in list(self._accusation_votes.items()):
                    if accused == player:
                        del self._accusation_votes[accuser]
            case GamePhase.DAY_BALLOT:
                if player in self._ballot_votes:
                    del self._ballot_votes[player]
            case GamePhase.NIGHT:
                if player.role == BasicRole.WEREWOLF and player in self._werewolves_votes:
                    del self._werewolves_votes[player]
                elif player.role != BasicRole.WEREWOLF:
                    for werewolf, target in list(self._werewolves_votes.items()):
                        if target == player:
                            del self._werewolves_votes[werewolf]
            case _:
                pass

        player.status = Status.DEAD

    def end_game_conditions(self, players: list[Player]) -> GamePhase | None:
        werewolves_alive = any(
            player.is_evil() and player.is_alive() for player in players
        )
        villagers_alive = any(
            not player.is_evil() and player.is_alive() for player in players
        )
        if not werewolves_alive:
            return GamePhase.VILLAGERS_VICTORY
        if not villagers_alive:
            return GamePhase.WEREWOLVES_VICTORY
        return None

    def get_all_handled_roles(self) -> set[Role]:
        return {BasicRole.VILLAGER, BasicRole.WEREWOLF}
    
    def get_game_modules(self) -> set[str]:
        return set()  # Base game has no specific modules, decorators will add their own
    
    def get_possible_targets(self, role: Role, players: list[Player]) -> list[Player]:
        if role == BasicRole.WEREWOLF:
            return [player for player in players if player.is_alive() and player.role != BasicRole.WEREWOLF]
        return []

class GameInfoDecorator(AbstractGameInfo):
    """
    Base decorator template for extending game functionality.
    """

    def __init__(self, wrapped: AbstractGameInfo) -> None:
        """Initializes the GameInfoDecorator with a wrapped AbstractGameInfo instance.
        Args:
            wrapped (AbstractGameInfo): The game info instance to be decorated.
        """
        self._check_roles_duplicates(wrapped)
        self._wrapped: AbstractGameInfo = wrapped

    @staticmethod
    @abstractmethod
    def get_decorator_roles() -> set[Role]:
        """
        Returns the set of roles specifically handled by this decorator.

        Returns:
            set[Role]: The roles managed by this specific decorator.

        Note:
            This method must be implemented by all concrete decorator classes.
        """

    @abstractmethod
    def get_decorator_data(self) -> GameActionData:
        """Returns a GameActionData specific to this decorator."""
        
    @abstractmethod
    def _compare_decorator(self, other: AbstractGameInfo) -> bool:
        """Utility method to compare the specific data of this decorator.
        
        Args:
            other (AbstractGameInfo): The other game info to compare against.
            
        Returns:
            bool: True if the specific data of this decorator matches the other, False otherwise.
            
        Note:
            This method is used by the __eq__ method.
        """

    @property
    def accusation_votes(self) -> dict[Player, Player]:
        return self._wrapped.accusation_votes

    @property
    def ballot_votes(self) -> dict[Player, bool]:
        return self._wrapped.ballot_votes

    @property
    def werewolves_votes(self) -> dict[Player, Player]:
        return self._wrapped.werewolves_votes

    def get_game_data(self) -> GameActionData:
        return self.get_decorator_data().compose(self._wrapped.get_game_data())

    def reset_actions(self) -> None:
        self._wrapped.reset_actions()

    def handle_accusation_vote(self, accuser: Player, accused: Player) -> None:
        self._wrapped.handle_accusation_vote(accuser, accused)

    def handle_ballot_vote(self, voter: Player, vote: bool) -> None:
        self._wrapped.handle_ballot_vote(voter, vote)

    def _handle_night_actions(self, actor: Player, target: Player) -> NightActionResult:
        return self._wrapped._handle_night_actions(actor, target)

    def remove_player(self, player: Player, gamephase: GamePhase) -> None:
        self._wrapped.remove_player(player, gamephase)

    def end_game_conditions(self, players: list[Player]) -> GamePhase | None:
        return self._wrapped.end_game_conditions(players)

    def get_all_handled_roles(self) -> set[Role]:
        return self._wrapped.get_all_handled_roles() | self.get_decorator_roles()
    
    def get_game_modules(self) -> set[str]:
        return self._wrapped.get_game_modules() | {self.__class__.__module__}

    def _check_roles_duplicates(self, wrapped: AbstractGameInfo) -> None:
        """Checks for duplicate roles between this decorator and the wrapped game info.

        Args:
            wrapped (AbstractGameInfo): The game info instance to check against.

        Raises:
            ValueError: If there are duplicate roles handled by both this decorator and the wrapped game info.
        """
        duplicate_roles: set[Role] = self.get_decorator_roles().intersection(
            wrapped.get_all_handled_roles()
        )

        if duplicate_roles:
            raise ValueError("Decorator roles already handled in wrapped game info.")
    
    @final
    def __eq__(self, other: object) -> bool:
        
        if not isinstance(other, AbstractGameInfo):
            return False
        
        if not super().__eq__(other):
            return False
        
        checking = self
        
        while isinstance(checking, GameInfoDecorator):
            other_decorator = self._find_decorator(type(checking), other)
            if other_decorator is None:
                return False

            if not checking._compare_decorator(other_decorator):
                return False
            
            checking = checking._wrapped

        return True
