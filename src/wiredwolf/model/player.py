from enum import Enum

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