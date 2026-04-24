from enum import Enum
import random

class Alignment(Enum):
    GOOD_ALIGNMENT = "Good"
    EVIL_ALIGNMENT = "Evil"

class Role(Enum):
    """Template for defining roles in the game. Each role has a name and an alignment (good or evil)."""

    def __init__(self, role_name: str, alignment: Alignment):
        self.role_name = role_name
        self.alignment = alignment

    def is_evil(self) -> bool:
        """Returns True if this role is considered evil (part of the werewolf team)."""
        return self.alignment == Alignment.EVIL_ALIGNMENT

    def __str__(self) -> str:
        return self.role_name
    
class BasicRole(Role):
    """Basic supported roles in the game."""
    
    WEREWOLF = ("Werewolf", Alignment.EVIL_ALIGNMENT)
    VILLAGER = ("Villager", Alignment.GOOD_ALIGNMENT)
    ESCORT = ("Escort", Alignment.GOOD_ALIGNMENT)
    CLAIRVOYANT = ("Clairvoyant", Alignment.GOOD_ALIGNMENT)
    MEDIUM = ("Medium", Alignment.GOOD_ALIGNMENT)


class Status(Enum):
    """Enumeration of possible player statuses in the game."""

    ALIVE = "Alive"
    PROTECTED = "Protected"
    DEAD = "Dead"


class Player:
    """Represents a player in the game with an ID, name, role, and status."""

    def __init__(self, id: str, name: str, role: Role):
        """Initializes a new player with the given ID, name, and role.
           All players start with the status set to ALIVE.
        Args:
            id (str): The unique identifier for the player.
            name (str): The name of the player.
            role (Role): The role assigned to the player.
        """
        self._id: str = id
        self._name: str = name
        self._status: Status = Status.ALIVE
        self._role: Role = role

    @property
    def id(self) -> str:
        return self._id
    
    @property
    def name(self) -> str:
        return self._name

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
        """Returns True if the player status is not set to dead."""
        return self._status != Status.DEAD

    def is_evil(self) -> bool:
        """Returns True if the player's role is considered evil (part of the werewolf team)."""
        return self._role.is_evil()

    def get_alignment(self) -> str:
        """Returns the alignment of the player's role."""
        return self._role.alignment.value

    def __str__(self) -> str:
        return f"Player(id={self._id}, name={self._name}, role={self._role}, status={self._status})"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Player):
            return (
                self._id == other._id
                and self._name == other._name
                and self._role == other._role
                and self._status == other._status
            )
        return False

    def __hash__(self) -> int:
        return hash((self._id, self._name, self._role))


def create_players(ids: dict[str, str], roles: set[Role]) -> list[Player]:
    """Creates a list of players with the given ids and assigns roles randomly.
    Args:
        ids (dict[str, str]): A dictionary mapping player IDs to player names.
        roles (set[Role]): A set of roles to assign to players.

    Returns:
        list[Player]: A list of Player objects with assigned roles.

    Raises:
        ValueError: If there are not enough players to assign the specified roles and at least 2 werewolves.

    Note: villager and werewolf are handled by default
    """

    players: list[Player] = []
    special_roles: set[Role] = roles - {
        BasicRole.VILLAGER,
        BasicRole.WEREWOLF,
    }  # Create a local copy excluding default roles
    werewolves_number = max(2, len(ids) // 4)

    if len(ids) < len(special_roles) + werewolves_number:
        raise ValueError(
            "Not enough players to assign the specified special roles and werewolves (minimum 2 werewolves required)."
        )

    id_list = list(ids.keys())
    random.shuffle(id_list)

    for id in id_list:
        if special_roles:
            role = special_roles.pop()
        elif werewolves_number > 0:
            role = BasicRole.WEREWOLF
            werewolves_number -= 1
        else:
            role = BasicRole.VILLAGER
        players.append(Player(id, ids[id], role))

    return players
