from enum import Enum
import random

class Role(Enum):
    WEREWOLF = "Werewolf"
    VILLAGER = "Villager"
    ESCORT = "Escort"
    CLAIRVOYANT = "Clairvoyant"
    MEDIUM = "Medium"
    
    def is_evil(self) -> bool:
        """Returns True if this role is considered evil (part of the werewolf team)."""
        return self == Role.WEREWOLF
    
class Status(Enum):
    ALIVE = "Alive"
    PROTECTED = "Protected"
    DEAD = "Dead"

class Player:
    
    _id: str
    _role: Role
    _status: Status
    
    def __init__(self, id: str, role: Role):
        self._id = id
        self._status = Status.ALIVE
        self._role = role
        
    @property
    def id(self) -> str:
        return self._id

    @property
    def role(self) -> Role:
        return self._role

    @property
    def status(self) -> Status:
        return self._status

    @status.setter
    def status(self, new_status: Status) -> None:
        self._status = new_status
        
    def is_alive(self) -> bool:
        return self._status != Status.DEAD
    
    def is_evil(self) -> bool:
        return self._role.is_evil()
        
    def __str__(self) -> str:
        return f"Player(id={self._id}, role={self._role}, status={self._status})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, Player):
            return self._id == other._id and self._role == other._role and self._status == other._status
        return False

    def __hash__(self) -> int:
        return hash((self._id, self._role, self._status))
    
def create_players(ids: list[str], roles: set[Role]) -> list[Player]:
    """Creates a list of players with the given ids and assigns roles randomly.
    Args:
        ids (list[str]): A list of player IDs.
        special_roles (set[Role]): A set of special roles to assign to players.

    Returns:
        list[Player]: A list of Player objects with assigned roles.
        
    Raises:
        ValueError: If there are not enough players to assign the specified special roles and at least 2 werewolves.
        
    Note: villager and werewolf are handled by default 
    """
    
    players: list[Player] = []
    special_roles: set[Role] = roles - {Role.VILLAGER, Role.WEREWOLF}  # Create a local copy excluding default roles
    werewolves_number = max(2, len(ids) // 4)

    if len(ids) < len(special_roles) + werewolves_number:
        raise ValueError("Not enough players to assign the specified special roles and werewolves (minimum 2 werewolves required).")

    random.shuffle(ids)

    for id in ids:
        if special_roles:
            role = special_roles.pop()
        elif werewolves_number > 0:
            role = Role.WEREWOLF
            werewolves_number -= 1
        else:
            role = Role.VILLAGER
        players.append(Player(id, role))
        
    return players
