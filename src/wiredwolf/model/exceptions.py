#GAME EXCEPTIONS

class GamePhaseError(Exception):
    """Raised when an action is attempted in an invalid game phase."""
    
class MissingPlayerError(Exception):
    """Raised when a specified player is not found in the game."""
    

class PlayerStatusError(Exception):
    """Raised when an action is performed by a player with an invalid status."""
    

class InvalidActionError(Exception):
    """Raised when a player attempts to perform an action they are not allowed to."""

#GAME BUILDER EXCEPTIONS

class GameDecoratorError(Exception):
    """Raised when there is an error related to game decorators, such as missing or incompatible decorators."""
