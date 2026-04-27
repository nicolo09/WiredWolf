from enum import Enum

import pygame

from wiredwolf.model.game_phases import GamePhase
class Screens(Enum):
    HOME='home'
    NEW_LOBBY='new lobby'
    SEARCH_LOBBY='search lobby'
    LOBBY_WAITING='lobby waiting'
    DAY_VOTING='day voting'
    DAY_EXECUTION='day execution'
    NIGHT_VILLAGER='night'
    NIGHT_ROLE='night role'
    ROLE_DISPLAY='role display'
    LOADING_LOBBY='loading lobby'
    LOADING_GAME='loading game'
    ERROR_SCREEN='error'
    NONE="none" 

#A simple dictionary that associates the game phase with the corresponding screens
game_phase_screens_dict:dict[GamePhase, Screens]={
                    GamePhase.DAY_DISCUSSION: Screens.DAY_VOTING, 
                    GamePhase.DAY_ACCUSING: Screens.DAY_VOTING, 
                    GamePhase.DAY_BALLOT: Screens.DAY_EXECUTION, 
                    GamePhase.NIGHT: Screens.NIGHT_VILLAGER, #TODO: this isn't exactly right, the night screen changes based on the role
                    GamePhase.VILLAGERS_VICTORY: Screens.HOME,
                    GamePhase.WEREWOLVES_VICTORY: Screens.HOME} #TODO: what to do if game phase is victory? There's no specific victory screen displayed
class EventType(Enum): #Used to easily identify the type of event sent
    CHANGE_SCREEN='change-screen'
    LOBBY='lobby'
    USERNAME='username'
    TIMEOUT='timeout'
    WAITING_ROOM='waiting-room'
    CHAT_MESSAGE='chat-message'
    GAME_ROLE='game-role'
    ERROR="error"
    END_ERROR="end-error"
    DEAD_PLAYER="dead-player"
    NONE=""

def h1Font()->pygame.font.Font:
    pygame.font.init()
    return pygame.font.Font(None, 35)

def h2Font()->pygame.font.Font:
    pygame.font.init()
    return pygame.font.Font(None, 30)

def h3Font()->pygame.font.Font:
    pygame.font.init()
    return pygame.font.Font(None, 25)

class FontSize(Enum):
    H1=h1Font()
    H2=h2Font()
    H3=h3Font()