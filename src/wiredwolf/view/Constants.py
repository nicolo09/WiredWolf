from enum import Enum

import pygame
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