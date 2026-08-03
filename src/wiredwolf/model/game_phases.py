from dataclasses import dataclass
from enum import Enum

from wiredwolf.model.player import Player

class GamePhase(Enum):
    FIRST_DAY = 0
    DAY_DISCUSSION = 1
    DAY_ACCUSING = 2
    DAY_BALLOT = 3
    BALLOT_RESULT = 4
    NIGHT = 5
    VILLAGERS_VICTORY = 6
    WEREWOLVES_VICTORY = 7


class GamePhaseOutcome:
    """
    Represents the outcome of a game phase transition.
    Attributes:
        new_phase (GamePhase): The new phase after the transition.
        deaths (list[Player]): List of players who died because of the phase transition.
        accused_player (Player | None): The player who was accused during the day accusing phase, if applicable.
    """

    def __init__(self, new_phase: GamePhase, deaths: list[Player] = [], accused_player: Player | None = None):
        self.new_phase: GamePhase = new_phase
        self.deaths: list[Player] = deaths
        self._accused_player: Player | None = accused_player

    def someone_died(self) -> bool:
        return len(self.deaths) > 0

    def get_accused_player(self) -> Player | None:
        return self._accused_player
    
class GamePhaseOutcomeBuilder:
    """
    Builder for creating GamePhaseOutcome instances.
    """

    def __init__(self):
        self._new_phase: GamePhase | None = None
        self._deaths: list[Player] = []
        self._accused_player: Player | None = None

    def set_new_phase(self, new_phase: GamePhase) -> "GamePhaseOutcomeBuilder":
        """Sets the new phase for the GamePhaseOutcome being built.
        Args:
            new_phase (GamePhase): The new phase to set.
        Returns:
            GamePhaseOutcomeBuilder: The builder instance for chaining.
        """
        self._new_phase = new_phase
        return self

    def add_death(self, player: Player) -> "GamePhaseOutcomeBuilder":
        """Adds a player to the list of deaths for the GamePhaseOutcome being built.
        Args:
            player (Player): The player who died.
        Returns:
            GamePhaseOutcomeBuilder: The builder instance for chaining.
        """
        self._deaths.append(player)
        return self

    def set_accused_player(self, player: Player) -> "GamePhaseOutcomeBuilder":
        """Sets the accused player for the GamePhaseOutcome being built.
        Args:
            player (Player): The player who was accused.
        Returns:
            GamePhaseOutcomeBuilder: The builder instance for chaining.
        """
        self._accused_player = player
        return self

    def build(self) -> GamePhaseOutcome:
        """Builds and returns a GamePhaseOutcome instance based on the current state of the builder.
        Returns:
            GamePhaseOutcome: The constructed GamePhaseOutcome instance.
        Raises:
            ValueError: If the new phase has not been set before calling this method.
        """
        if self._new_phase is None:
            raise ValueError("New phase must be set before building GamePhaseOutcome.")
        return GamePhaseOutcome(
            new_phase=self._new_phase,
            deaths=self._deaths,
            accused_player=self._accused_player,
        )
        
    def reset(self) -> None:
        """Resets the builder to its initial state."""
        self._new_phase = None
        self._deaths = []
        self._accused_player = None


@dataclass
class NightActionResult:
    """
    Contains a message for the player who performed a night action to let them know the result.
    """

    message: str
