class GamePhaseError(Exception):
    """Raised when an action is attempted in an invalid game phase."""
    pass

class MissingPlayerError(Exception):
    """Raised when a specified player is not found in the game."""
    pass

class PlayerStatusError(Exception):
    """Raised when an action is performed by a player with an invalid status."""
    pass

class InvalidActionError(Exception):
    """Raised when a player attempts to perform an action they are not allowed to."""
    pass
