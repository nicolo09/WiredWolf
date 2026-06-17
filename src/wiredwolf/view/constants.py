from enum import Enum

import pygame

from wiredwolf.model.player import Role, BasicRole
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
    DAY_END='day end'
    NONE="none" 

class EventType(Enum): #Used to easily identify the type of event sent
    CHANGE_SCREEN='change-screen'
    LOBBY='lobby'
    USERNAME='username'
    TIMEOUT='timeout'
    CHAT_MESSAGE='chat-message'
    GAME_ROLE='game-role'
    ERROR="error"
    END_ERROR="end-error"
    DEAD_PLAYER="dead-player"
    NONE=""

#Used to get a brief description of the role to display
ROLE_DESCRIPTION_DICT:dict[Role, str]={ 
    BasicRole.WEREWOLF: "Every night decide who to kill, try to not get found out",
    BasicRole.VILLAGER: "Vote out the werewolves and try to survive",
    BasicRole.CLAIRVOYANT: "Secretly learn if one alive player is good or bad each night",
    BasicRole.ESCORT: "Prevent the player chosen from being killed by the werewolves",
    BasicRole.MEDIUM: "Secretly learn if a dead player was good or bad when he was alive each night"
}

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