import importlib
import inspect
import logging

from typing import Any
from wiredwolf.model.exceptions import GameDecoratorError
from wiredwolf.model.game_template import AbstractGameInfo, GameActionData, GameInfoBase, GameInfoDecorator
from wiredwolf.model.role_extensions import ClairvoyantDecorator, EscortDecorator, MediumDecorator
from wiredwolf.model.player import Player, Role, BasicRole

WIREDWOLF_DECORATOR_MODULE = "wiredwolf.model.role_extensions"
DECORATOR_CLASS_SUFFIX = "Decorator"

class GameInfoBuilder:
    """
    Builder for creating game configurations with specific role support.
    """
    _logger = logging.getLogger(__name__)

    def __init__(
        self,
        game_info: AbstractGameInfo,
        game_data: GameActionData | None = None,
        players: list[Player] = [],
        decorator_modules: set[str] = {WIREDWOLF_DECORATOR_MODULE},
    ) -> None:
        self._game_info: AbstractGameInfo = game_info
        self._game_data: GameActionData | None = game_data
        self._players: list[Player] = players
        self._decorator_modules: set[str] = decorator_modules
        self._handled_roles: set[Role] = set()

    @classmethod
    def new(cls) -> "GameInfoBuilder":
        """
        Create a builder with basic game support (Villager and Werewolf).

        Returns:
            BasicGameInfoBuilder: A new builder with basic functionality.
        """
        return cls(GameInfoBase())

    @classmethod
    def with_game_data(
        cls, game_data: GameActionData, players: list[Player]
    ) -> "GameInfoBuilder":
        """
        Create a builder with a given game data which will be used to initialize the game.

        Args:
            game_data (GameActionData): The game data to use.

        Returns:
            BasicGameInfoBuilder: A new builder with the specified game data.
        """
        return cls(GameInfoBase(game_data), game_data, players)
    
    def add_decorator_module(self, *module_name: str) -> "GameInfoBuilder":
        """
        Add modules to search for decorators when adding roles.

        Args:
            module_name (str): The name of the modules to add.
        """
        self._decorator_modules.update(module_name)
        return self

    
    def with_roles(self, roles: set[Role]) -> "GameInfoBuilder":
        """
        Add multiple roles at once.

        Args:
            roles (set[Role]): The set of roles to add.

        Returns:
            GameInfoBuilder: This builder.
        """
        self._handled_roles.update(roles)
        return self
    
    def __find_decorator_for_role(self, role: Role) -> GameInfoDecorator:
        """
        Utility method to find the appropriate decorator for a given role if it exists.
        
        Args:
            role (Role): The role for which to find a decorator.
            
        Raises:
            ValueError: If no decorator is found for the role.
        """
        for module_name in self._decorator_modules:
            decorator_class_name: str = f"{role.role_name}{DECORATOR_CLASS_SUFFIX}"
            try:
                module = importlib.import_module(module_name)
                decorator_class: Any = getattr(module, decorator_class_name)
                
                # Check if decorator
                if not issubclass(decorator_class, GameInfoDecorator):
                    self._logger.warning(f"Class {decorator_class_name} found in module {module_name} is not a valid GameInfoDecorator. Checking next module.")
                    continue

                # Select Arguments
                init_signature = inspect.signature(decorator_class.__init__)
                constructor_params = [
                    param
                    for name, param in init_signature.parameters.items()
                    if name != "self"
                    and param.kind in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    )
                ]

                if len(constructor_params) < 2 or len(constructor_params) > 3:
                    self._logger.warning(f"Decorator class {decorator_class_name} found in module {module_name} requires {len(constructor_params)} arguments, but 2 or 3 are expected. Checking next module.")
                    continue
                cons_args: list[Any] = [self._game_info, self._game_data]
                if len(constructor_params) == 3:
                    cons_args.append(self._players)

                return decorator_class(*cons_args)
            except (ImportError, AttributeError):
                self._logger.warning(f"No decorator found for role {role} in module {module_name}. Checking next module.")
            
        raise GameDecoratorError(f"No decorator found for role {role} in any of the specified modules")



    def build(self) -> AbstractGameInfo:
        """
        Build and return the configured game instance.

        Returns:
            AbstractGameInfo: The configured game with all requested roles.
        """
        for role in self._handled_roles:
            match role:
                case BasicRole.VILLAGER | BasicRole.WEREWOLF:
                    continue  # Basic roles are already supported by GameInfoBase
                case BasicRole.CLAIRVOYANT:
                    self._game_info = ClairvoyantDecorator(self._game_info, self._game_data)
                case BasicRole.ESCORT:
                    self._game_info = EscortDecorator(self._game_info, self._game_data, self._players)
                case BasicRole.MEDIUM:
                    self._game_info = MediumDecorator(self._game_info, self._game_data)
                case _:
                    decorator = self.__find_decorator_for_role(role)
                    self._game_info = decorator
                    
        return self._game_info
