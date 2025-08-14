from abc import ABC, abstractmethod
from wiredwolf.model.game import GamePhase
from wiredwolf.model.player import Player, Status, Role
from typing import final

#TODO: implement a ActionOutcome class to better handle the results of actions?
class AbstractGameInfo(ABC):
    """
    Abstract base class for managing game state, votes, and night actions.

    Subclasses must implement methods for handling votes, night actions,
    end game conditions, and supported roles.
    """

    @property
    @abstractmethod
    def accusation_votes(self) -> dict[Player, Player]:
        """Returns the current accusation votes."""
        pass

    @property
    @abstractmethod
    def ballot_votes(self) -> dict[Player, bool]:
        """Returns the current ballot votes."""
        pass

    @property
    @abstractmethod
    def werewolves_votes(self) -> dict[Player, Player]:
        """Returns the current werewolves votes."""
        pass

    @abstractmethod
    def reset_actions(self):
        """Clears all votes and night actions for a new round."""
        pass

    @abstractmethod
    def handle_accusation_vote(self, accuser: Player, accused: Player):
        """Handles an accusation vote from one player against another."""
        pass

    @abstractmethod
    def handle_ballot_vote(self, voter: Player, vote: bool):
        """Handles a ballot vote from a player."""
        pass

    @final
    def handle_night_actions(self, actor: Player, target: Player) -> bool | None:
        """
        Handles a night action performed by an actor on a target.

        Args:
            target (Player): The player being targeted.
            actor (Player): The player performing the action.

        Returns:
            bool | None: Result of the action, if applicable.
        """
        if actor.role not in self.get_handled_roles():
            raise ValueError(f"{actor.role} is unhandled.")
        return self._handle_night_actions(actor, target)

    @abstractmethod
    def _handle_night_actions(self, actor: Player, target: Player) -> bool | None:
        """Internal method for handling night actions. To be implemented by subclasses."""
        pass

    @abstractmethod
    def end_game_conditions(self, players: list[Player]) -> GamePhase | None:
        """
        Checks if the game has ended and returns the winning phase if so.

        Args:
            players (list[Player]): List of all players.

        Returns:
            The winning phase, or None if the game continues.
        """
        pass

    @abstractmethod
    def get_handled_roles(self) -> list[Role]:
        """Returns a list of roles handled by this game."""
        pass

# Minimal implementation: handles Villager, Werewolf, and end game conditions
class MinimalGameInfo(AbstractGameInfo):

    def __init__(self):
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

    def handle_accusation_vote(self, accuser: Player, accused: Player):
        if not accuser.is_alive():
            raise ValueError("Cannot accuse as dead player.")
        if not accused.is_alive():
            raise ValueError("Cannot accuse dead player.")
        if accuser in self._accusation_votes:
            raise ValueError(f"{accuser.id} has already voted.")
        self._accusation_votes[accuser] = accused

    def handle_ballot_vote(self, voter: Player, vote: bool):
        if not voter.is_alive():
            raise ValueError("Cannot vote as dead player.")
        if voter in self._ballot_votes:
            raise ValueError(f"{voter.id} has already voted.")
        self._ballot_votes[voter] = vote

    def _handle_night_actions(self, actor: Player, target: Player) -> bool | None:
        if actor.role == Role.WEREWOLF:
            if not actor.is_alive():
                raise ValueError(f"{actor.role} cannot perform action as dead player.")
            if actor in self._werewolves_votes:
                raise ValueError(f"{actor.id} has already voted.")
            if target.role == Role.WEREWOLF:
                raise ValueError("Werewolves cannot vote for other werewolves.")
            if not target.is_alive():
                raise ValueError("Cannot vote for dead player.")
            self._werewolves_votes[actor] = target
        return None
    
    def reset_actions(self):
        self._accusation_votes.clear()
        self._ballot_votes.clear()
        self._werewolves_votes.clear()

    def end_game_conditions(self, players: list[Player]) -> GamePhase | None:
        werewolves_alive = any(player.is_evil() and player.is_alive() for player in players)
        villagers_alive = any(not player.is_evil() and player.is_alive() for player in players)
        if not werewolves_alive:
            return GamePhase.VILLAGERS_VICTORY
        if not villagers_alive:
            return GamePhase.WEREWOLVES_VICTORY
        return None

    def get_handled_roles(self) -> list[Role]:
        return [Role.VILLAGER, Role.WEREWOLF]

# Decorator base class
class GameInfoDecorator(AbstractGameInfo):
    def __init__(self, wrapped: AbstractGameInfo):
        self._wrapped = wrapped

    @property
    def accusation_votes(self):
        return self._wrapped.accusation_votes

    @property
    def ballot_votes(self):
        return self._wrapped.ballot_votes

    @property
    def werewolves_votes(self):
        return self._wrapped.werewolves_votes

    def reset_actions(self):
        self._wrapped.reset_actions()

    def handle_accusation_vote(self, accuser: Player, accused: Player):
        self._wrapped.handle_accusation_vote(accuser, accused)

    def handle_ballot_vote(self, voter: Player, vote: bool):
        self._wrapped.handle_ballot_vote(voter, vote)

    def _handle_night_actions(self, actor: Player, target: Player) -> bool | None:
        return self._wrapped._handle_night_actions(actor, target)

    def end_game_conditions(self, players: list[Player]) -> GamePhase | None:
        return self._wrapped.end_game_conditions(players)

    def get_handled_roles(self) -> list[Role]:
        return self._wrapped.get_handled_roles()

# Decorator for Clairvoyant role
class ClairvoyantGameInfoDecorator(GameInfoDecorator):
    def __init__(self, wrapped):
        super().__init__(wrapped)
        self._clairvoyant_acted = False

    def reset_actions(self):
        super().reset_actions()
        self._clairvoyant_acted = False

    def _handle_night_actions(self, actor: Player, target: Player) -> bool | None:
        if actor.role == Role.CLAIRVOYANT:
            if not actor.is_alive():
                raise ValueError(f"{actor.role} cannot perform action as dead player.")
            if self._clairvoyant_acted:
                raise ValueError("Clairvoyant has already acted this night.")
            if not target.is_alive():
                raise ValueError("Clairvoyant cannot target dead players.")
            self._clairvoyant_acted = True
            return target.is_evil()
        return super()._handle_night_actions(actor, target)

    def get_handled_roles(self) -> list[Role]:
        return super().get_handled_roles() + [Role.CLAIRVOYANT]

# Decorator for Escort role
class EscortGameInfoDecorator(GameInfoDecorator):
    def __init__(self, wrapped):
        super().__init__(wrapped)
        self._escort_acted = False
        self._protected_player: Player | None = None

    def reset_actions(self):
        super().reset_actions()
        self._escort_acted = False
        if self._protected_player is not None:
            self._protected_player.status = Status.ALIVE
            self._protected_player = None 

    def _handle_night_actions(self, actor: Player, target: Player) -> bool | None:
        if actor.role == Role.ESCORT:
            if not actor.is_alive():
                raise ValueError(f"{actor.role} cannot perform action as dead player.")
            if self._escort_acted:
                raise ValueError("Escort has already acted this night.")
            if not target.is_alive():
                raise ValueError("Escort cannot target dead players.")
            self._escort_acted = True
            target.status = Status.PROTECTED
            self._protected_player = target
            return
        return super()._handle_night_actions(actor, target)

    def get_handled_roles(self) -> list[Role]:
        return super().get_handled_roles() + [Role.ESCORT]

# Decorator for Medium role
class MediumGameInfoDecorator(GameInfoDecorator):
    def __init__(self, wrapped):
        super().__init__(wrapped)
        self._medium_acted = False

    def reset_actions(self):
        super().reset_actions()
        self._medium_acted = False

    def _handle_night_actions(self, actor: Player, target: Player) -> bool | None:
        if actor.role == Role.MEDIUM:
            if not actor.is_alive():
                raise ValueError(f"{actor.role} cannot perform action as dead player.")
            if self._medium_acted:
                raise ValueError("Medium has already acted this night.")
            if target.is_alive():
                raise ValueError("Medium cannot target alive players.")
            self._medium_acted = True
            return target.is_evil()
        return super()._handle_night_actions(actor, target)

    def get_handled_roles(self) -> list[Role]:
        return super().get_handled_roles() + [Role.MEDIUM]

# Factory to build the basic rule set of wiredwolf
class BasicGameInfoFactory:
    @staticmethod
    def build():
        rules = MinimalGameInfo()
        rules = ClairvoyantGameInfoDecorator(rules)
        rules = EscortGameInfoDecorator(rules)
        rules = MediumGameInfoDecorator(rules)
        return rules