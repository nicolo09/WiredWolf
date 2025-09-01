from enum import Enum

import pygame
class Screens(Enum):
    HOME='home'
    NEW_LOBBY='new lobby'
    SEARCH_LOBBY='search lobby'
    LOBBY_WAITING='lobby waiting'
    DAY_CHAT='day chat'
    DAY_VOTING='day voting'
    DAY_EXECUTION='day execution'
    NIGHT_VILLAGER='night'
    NIGHT_ROLE='night role'
    TEST='test'

#App colors
BACKGROUND_COLOR="#C5C5BF"
TEXT_COLOR="#1A1A1A"
BUTTON_COLOR="#F3A6A6"
BUTTON_HOVER_COLOR="#DA0000"
SELECTED_COLOR="#CC02FF"

def h1Font()->pygame.font.Font:
    pygame.font.init()
    return pygame.font.Font(None, 35)

def h2Font()->pygame.font.Font:
    pygame.font.init()
    return pygame.font.Font(None, 30)

class FontSize(Enum):
    H1=h1Font()
    H2=h2Font()