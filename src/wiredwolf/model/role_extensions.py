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

    def __init__(self, wrapped: AbstractGameInfo) -> None:
        super().__init__(wrapped)
        self._clairvoyant_acted: bool = False

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
            return NightActionResult( f"Clairvoyant investigated {target.id}: {target.get_alignment()}.")
        return super()._handle_night_actions(actor, target)

    def get_handled_roles(self) -> list[Role]:
        return super().get_handled_roles() + [Role.CLAIRVOYANT]

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

    def __init__(self, wrapped: AbstractGameInfo) -> None:
        super().__init__(wrapped)
        self._escort_acted: bool = False
        self._protected_player: Player | None = None

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
            elif player.role == Role.ESCORT:
                player.status = Status.ALIVE
                self._escort_acted = False
        super().remove_player(player, gamephase)

    def get_handled_roles(self) -> list[Role]:
        return super().get_handled_roles() + [Role.ESCORT]

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

    def __init__(self, wrapped: AbstractGameInfo) -> None:
        super().__init__(wrapped)
        self._medium_acted: bool = False

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
            return NightActionResult(f"Medium communicated with {target.id}: {target.get_alignment()}.")
        return super()._handle_night_actions(actor, target)

    def get_handled_roles(self) -> list[Role]:
        return super().get_handled_roles() + [Role.MEDIUM]

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

    def __init__(self, game_info: AbstractGameInfo):
        self._game_info: AbstractGameInfo = game_info

    @classmethod
    def default(cls) -> "BasicGameInfoBuilder":
        """
        Create a builder with basic game support (Villager and Werewolf).

        Returns:
            BasicGameInfoBuilder: A new builder with basic functionality.
        """
        return cls(SimpleGameInfo())

    def with_clairvoyant(self) -> "BasicGameInfoBuilder":
        """
        Add Clairvoyant role support.

        Returns:
            BasicGameInfoBuilder: This builder.
        """
        if Role.CLAIRVOYANT not in self._game_info.get_handled_roles():
            self._game_info = ClairvoyantDecorator(self._game_info)
        return self

    def with_escort(self) -> "BasicGameInfoBuilder":
        """
        Add Escort role support.

        Returns:
            BasicGameInfoBuilder: This builder.
        """
        if Role.ESCORT not in self._game_info.get_handled_roles():
            self._game_info = EscortDecorator(self._game_info)
        return self

    def with_medium(self) -> "BasicGameInfoBuilder":
        """
        Add Medium role support.

        Returns:
            BasicGameInfoBuilder: This builder.
        """
        if Role.MEDIUM not in self._game_info.get_handled_roles():
            self._game_info = MediumDecorator(self._game_info)
        return self

    def with_roles(self, *roles: Role) -> "BasicGameInfoBuilder":
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
    Create a standard game with all available roles.

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
