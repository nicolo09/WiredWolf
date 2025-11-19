from dataclasses import dataclass
from enum import Enum

from wiredwolf.model.player import Player


class GamePhase(Enum):
    DAY_DISCUSSION = 1
    DAY_ACCUSING = 2
    DAY_BALLOT = 3
    NIGHT = 4
    VILLAGERS_VICTORY = 5
    WEREWOLVES_VICTORY = 6


class GamePhaseOutcome:
    """
    Represents the outcome of a game phase transition.
    Attributes:
        new_phase (GamePhase): The new phase after the transition.
        deaths (list[Player]): List of players who died because of the phase transition.
    """

    def __init__(self, new_phase: GamePhase, deaths: list[Player] = []):
        self.new_phase: GamePhase = new_phase
        self.deaths: list[Player] = deaths

    def someone_died(self) -> bool:
        return len(self.deaths) > 0


@dataclass
class NightActionResult:
    """
    Contains a message for the player who performed a night action to let them know the result.
    """

    message: str
