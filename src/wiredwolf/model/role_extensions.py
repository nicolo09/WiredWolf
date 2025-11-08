from wiredwolf.model.game_phases import GamePhase, NightActionResult
from wiredwolf.model.player import Player, Status, Role
from wiredwolf.model.exceptions import *
from wiredwolf.model.game_template import *


class ClairvoyantDecorator(GameInfoDecorator):
    """
    Adds Clairvoyant role support.

    The Clairvoyant can investigate one player per night to determine
    if they are evil (part of the werewolf team).
    """

    def __init__(
        self, wrapped: AbstractGameInfo, game_data: GameActionData | None = None
    ) -> None:
        super().__init__(wrapped)
        if game_data is not None and "clairvoyant_acted" in game_data.data:
            self._clairvoyant_acted: bool = game_data.data["clairvoyant_acted"]
        else:
            self._clairvoyant_acted: bool = False

    @staticmethod
    def get_decorator_roles() -> set[Role]:
        return {Role.CLAIRVOYANT}

    def get_decorator_data(self) -> GameActionData:
        return GameActionData(
            {
                "clairvoyant_acted": self._clairvoyant_acted,
            }
        )

    def reset_actions(self) -> None:
        super().reset_actions()
        self._clairvoyant_acted = False

    def _handle_night_actions(self, actor: Player, target: Player) -> NightActionResult:
        if actor.role == Role.CLAIRVOYANT:
            if not actor.is_alive():
                raise InvalidActionError(
                    f"{actor.role} cannot perform action as dead player."
                )
            if self._clairvoyant_acted:
                raise InvalidActionError("Clairvoyant has already acted this night.")
            if not target.is_alive():
                raise InvalidActionError("Clairvoyant cannot target dead players.")
            self._clairvoyant_acted = True
            return NightActionResult(
                f"Clairvoyant investigated {target.id}: {target.get_alignment()}."
            )
        return super()._handle_night_actions(actor, target)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractGameInfo):
            return False

        other_clairvoyant = self._find_decorator(ClairvoyantDecorator, other)
        if other_clairvoyant is None:
            return False

        if self._clairvoyant_acted != other_clairvoyant._clairvoyant_acted:
            return False

        return super().__eq__(other)


class EscortDecorator(GameInfoDecorator):
    """
    Adds Escort role support.

    The Escort can protect one player per night from werewolf attacks.
    """
#FIXME: When recreating from GameActionData, the player must be the same instance as in the players list
# even though it should be already set as protected in the player status
    def __init__(
        self,
        wrapped: AbstractGameInfo,
        game_data: GameActionData | None = None
    ) -> None:
        super().__init__(wrapped)
        if game_data is not None and "protected_player" in game_data.data:
            self._escort_acted: bool = True
            self._protected_player: Player | None = game_data.data["protected_player"]
        else:
            self._escort_acted: bool = False
            self._protected_player: Player | None = None

    @staticmethod
    def get_decorator_roles() -> set[Role]:
        return {Role.ESCORT}

    def get_decorator_data(self) -> GameActionData:
        return GameActionData(
            {
                "protected_player": self._protected_player,
            }
        )

    def reset_actions(self) -> None:
        super().reset_actions()
        self._escort_acted = False
        if self._protected_player is not None:
            self._protected_player.status = Status.ALIVE
            self._protected_player = None

    def _handle_night_actions(self, actor: Player, target: Player) -> NightActionResult:
        if actor.role == Role.ESCORT:
            if not actor.is_alive():
                raise PlayerStatusError(
                    f"{actor.role} cannot perform action as dead player."
                )
            if self._escort_acted:
                raise InvalidActionError("Escort has already acted this night.")
            if not target.is_alive():
                raise InvalidActionError("Escort cannot target dead players.")
            self._escort_acted = True
            target.status = Status.PROTECTED
            self._protected_player = target
            return NightActionResult(message=f"Escort protected {target.id}.")
        return super()._handle_night_actions(actor, target)

    def remove_player(self, player: Player, gamephase: GamePhase) -> None:
        if gamephase == GamePhase.NIGHT:
            if player == self._protected_player:
                self._protected_player = None
                self._escort_acted = False
            elif player.role == Role.ESCORT and self._protected_player is not None:
                self._protected_player.status = Status.ALIVE
                self._protected_player = None
                self._escort_acted = False
        super().remove_player(player, gamephase)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractGameInfo):
            return False

        other_escort = self._find_decorator(EscortDecorator, other)
        if other_escort is None:
            return False

        if (
            self._escort_acted != other_escort._escort_acted
            or self._protected_player != other_escort._protected_player
        ):
            return False

        return super().__eq__(other)


class MediumDecorator(GameInfoDecorator):
    """
    Adds Medium role support.

    The Medium can communicate with dead players to determine if they
    were evil (part of the werewolf team).
    """

    def __init__(self, wrapped: AbstractGameInfo, game_data: GameActionData | None = None) -> None:
        super().__init__(wrapped)
        if game_data is not None and "medium_acted" in game_data.data:
            self._medium_acted: bool = game_data.data["medium_acted"]
        else:
            self._medium_acted: bool = False

    @staticmethod
    def get_decorator_roles() -> set[Role]:
        return {Role.MEDIUM}

    def get_decorator_data(self) -> GameActionData:
        return GameActionData(
            {
                "medium_acted": self._medium_acted,
            }
        )

    def reset_actions(self) -> None:
        super().reset_actions()
        self._medium_acted = False

    def _handle_night_actions(self, actor: Player, target: Player) -> NightActionResult:
        if actor.role == Role.MEDIUM:
            if not actor.is_alive():
                raise PlayerStatusError(
                    f"{actor.role} cannot perform action as dead player."
                )
            if self._medium_acted:
                raise InvalidActionError("Medium has already acted this night.")
            if target.is_alive():
                raise InvalidActionError("Medium cannot target alive players.")
            self._medium_acted = True
            return NightActionResult(
                f"Medium communicated with {target.id}: {target.get_alignment()}."
            )
        return super()._handle_night_actions(actor, target)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AbstractGameInfo):
            return False

        other_medium = self._find_decorator(MediumDecorator, other)
        if other_medium is None:
            return False

        if self._medium_acted != other_medium._medium_acted:
            return False

        return super().__eq__(other)


class BasicGameInfoBuilder:
    """
    Builder for creating game configurations with specific role support.
    """

    def __init__(self, game_info: AbstractGameInfo, game_data: GameActionData | None = None) -> None:
        self._game_info: AbstractGameInfo = game_info
        self._game_data: GameActionData | None = game_data
    
    @classmethod
    def default(cls) -> "BasicGameInfoBuilder":
        """
        Create a builder with basic game support (Villager and Werewolf).

        Returns:
            BasicGameInfoBuilder: A new builder with basic functionality.
        """
        return cls(SimpleGameInfo())

    @classmethod
    def with_game_data(cls, game_data: GameActionData) -> "BasicGameInfoBuilder":
        """
        Create a builder with the specified game data.

        Args:
            game_data (GameActionData): The game data to use.

        Returns:
            BasicGameInfoBuilder: A new builder with the specified game data.
        """
        return cls(SimpleGameInfo(game_data), game_data)

    def with_clairvoyant(self) -> "BasicGameInfoBuilder":
        """
        Add Clairvoyant role support.

        Returns:
            BasicGameInfoBuilder: This builder.
        """
        if Role.CLAIRVOYANT not in self._game_info.get_all_handled_roles():
            self._game_info = ClairvoyantDecorator(self._game_info, self._game_data)
        return self

    def with_escort(self) -> "BasicGameInfoBuilder":
        """
        Add Escort role support.

        Returns:
            BasicGameInfoBuilder: This builder.
        """
        if Role.ESCORT not in self._game_info.get_all_handled_roles():
            self._game_info = EscortDecorator(self._game_info, self._game_data)
        return self

    def with_medium(self) -> "BasicGameInfoBuilder":
        """
        Add Medium role support.

        Returns:
            BasicGameInfoBuilder: This builder.
        """
        if Role.MEDIUM not in self._game_info.get_all_handled_roles():
            self._game_info = MediumDecorator(self._game_info, self._game_data)
        return self

    def with_roles(self, roles: set[Role]) -> "BasicGameInfoBuilder":
        """
        Add multiple roles at once.

        Args:
            *roles: Variable number of Role enum values to add.

        Returns:
            BasicGameInfoBuilder: This builder.
        """
        for role in roles:
            if role == Role.CLAIRVOYANT:
                self.with_clairvoyant()
            elif role == Role.ESCORT:
                self.with_escort()
            elif role == Role.MEDIUM:
                self.with_medium()

        return self

    def build(self) -> AbstractGameInfo:
        """
        Build and return the configured game instance.

        Returns:
            AbstractGameInfo: The configured game with all requested roles.
        """
        return self._game_info


def create_standard_game() -> AbstractGameInfo:
    """
    Create a new standard game with all available roles.

    Returns:
        AbstractGameInfo: A game supporting all roles.
    """
    return (
        BasicGameInfoBuilder.default()
        .with_clairvoyant()
        .with_escort()
        .with_medium()
        .build()
    )
