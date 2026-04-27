from wiredwolf.model.game_phases import GamePhase, NightActionResult
from wiredwolf.model.game_template import AbstractGameInfo
from wiredwolf.model.player import Player, Status, Role
from wiredwolf.model.exceptions import *
from wiredwolf.model.game_template import *

####################################################################################################################################
# This module contains decorators for adding support for specific roles to the game info.                                          #
# To add support for a new role, create a new decorator class that extends GameInfoDecorator and implements the required methods.  #
# The class must be named <RoleName>Decorator otherwise it won't be automatically used by the builder.                             #
# The builder will automatically add the correct decorators based on the specified roles when building the game info.              #
# Variaton of already existing role decorators should be considered as new roles and implemented as new decorators.                #                                                             # 
####################################################################################################################################

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
        return {BasicRole.CLAIRVOYANT}

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
        if actor.role == BasicRole.CLAIRVOYANT:
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
                f"Clairvoyant investigated {target.name}: {target.get_alignment()}."
            )
        return super()._handle_night_actions(actor, target)

    def get_possible_targets(self, role: Role, players: list[Player]) -> list[Player]:
        if role == BasicRole.CLAIRVOYANT:
            return [player for player in players if player.is_alive()]
        return self._wrapped.get_possible_targets(role, players)
    
    def _compare_decorator(self, other: AbstractGameInfo) -> bool:
        if not isinstance(other, ClairvoyantDecorator):
            return False
        return self._clairvoyant_acted == other._clairvoyant_acted


class EscortDecorator(GameInfoDecorator):
    """
    Adds Escort role support.

    The Escort can protect one player per night from werewolf attacks.
    """

    def __init__(
        self,
        wrapped: AbstractGameInfo,
        game_data: GameActionData | None = None,
        players: list[Player] = [],
    ) -> None:
        super().__init__(wrapped)
        if (
            game_data is not None
            and len(players) > 0
            and "protected_player" in game_data.data
        ):
            self._escort_acted: bool = True
            protected_id = game_data.data["protected_player"]
            self._protected_player: Player | None = next(
                (p for p in players if p.id == protected_id), None
            )
        else:
            self._escort_acted: bool = False
            self._protected_player: Player | None = None

    @staticmethod
    def get_decorator_roles() -> set[Role]:
        return {BasicRole.ESCORT}

    def get_decorator_data(self) -> GameActionData:
        return GameActionData(
            {
                "protected_player": self._protected_player.id,
            }
            if self._protected_player is not None
            else {}
        )

    def reset_actions(self) -> None:
        super().reset_actions()
        self._escort_acted = False
        if self._protected_player is not None:
            self._protected_player.status = Status.ALIVE
            self._protected_player = None

    def _handle_night_actions(self, actor: Player, target: Player) -> NightActionResult:
        if actor.role == BasicRole.ESCORT:
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
            return NightActionResult(message=f"Escort protected {target.name}.")
        return super()._handle_night_actions(actor, target)

    def remove_player(self, player: Player, gamephase: GamePhase) -> None:
        if gamephase == GamePhase.NIGHT:
            if player == self._protected_player:
                self._protected_player = None
                self._escort_acted = False
            elif player.role == BasicRole.ESCORT and self._protected_player is not None:
                self._protected_player.status = Status.ALIVE
                self._protected_player = None
                self._escort_acted = False
        super().remove_player(player, gamephase)

    def get_possible_targets(self, role: Role, players: list[Player]) -> list[Player]:
        if role == BasicRole.ESCORT:
            return [player for player in players if player.is_alive()]
        return self._wrapped.get_possible_targets(role, players)
    
    def _compare_decorator(self, other: AbstractGameInfo) -> bool:
        if not isinstance(other, EscortDecorator):
            return False
        return (
            self._escort_acted == other._escort_acted
            and self._protected_player == other._protected_player
        )


class MediumDecorator(GameInfoDecorator):
    """
    Adds Medium role support.

    The Medium can communicate with dead players to determine if they
    were evil (part of the werewolf team).
    """

    def __init__(
        self, wrapped: AbstractGameInfo, game_data: GameActionData | None = None
    ) -> None:
        super().__init__(wrapped)
        if game_data is not None and "medium_acted" in game_data.data:
            self._medium_acted: bool = game_data.data["medium_acted"]
        else:
            self._medium_acted: bool = False

    @staticmethod
    def get_decorator_roles() -> set[Role]:
        return {BasicRole.MEDIUM}

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
        if actor.role == BasicRole.MEDIUM:
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
                f"Medium communicated with {target.name}: {target.get_alignment()}."
            )
        return super()._handle_night_actions(actor, target)

    def get_possible_targets(self, role: Role, players: list[Player]) -> list[Player]:
        if role == BasicRole.MEDIUM:
            return [player for player in players if not player.is_alive()]
        return self._wrapped.get_possible_targets(role, players)
    
    def _compare_decorator(self, other: AbstractGameInfo) -> bool:
        if not isinstance(other, MediumDecorator):
            return False
        return self._medium_acted == other._medium_acted

