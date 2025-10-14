class GamePhaseError(Exception):
    """Raised when an action is attempted in an invalid game phase."""
    
class MissingPlayerError(Exception):
    """Raised when a specified player is not found in the game."""
    

class PlayerStatusError(Exception):
    """Raised when an action is performed by a player with an invalid status."""
    

class InvalidActionError(Exception):
    """Raised when a player attempts to perform an action they are not allowed to."""
