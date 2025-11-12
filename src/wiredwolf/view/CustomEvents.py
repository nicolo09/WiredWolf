from abc import ABC, abstractmethod
from wiredwolf.view.Constants import EventType, Screens
import pygame


class AbstractEventType(ABC):
    """The abstract event sent to the gui"""
    #static field to standardize the dictionary key
    #field key has already been set as CUSTOM_EVENT
    s_event="event"

    def __init__(self)->None:
        self._event=EventType.NONE #Actual event is sent by the concrete class
    
    @property
    def event(self)->EventType:
        """Returns the type of event given"""
        return self._event
    
    @abstractmethod
    def as_dictionary(self)->dict:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        raise NotImplementedError("Please implement this method")
        
class ChangeScreenType(AbstractEventType):
    """An event of changing screen in the gui"""
    #static field name to standardize the dictionary key
    s_next_screen="next_screen"

    def __init__(self, next_screen: Screens)->None:
        self._event=EventType.CHANGE_SCREEN
        self._next_screen=next_screen
    
    @property
    def next_screen(self)->Screens:
        """Returns the screen the change screen events wants to change to"""
        return self._next_screen
    
    def as_dictionary(self) -> dict:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, ChangeScreenType.s_next_screen:self._next_screen}
    
class DiscoveredLobbyType(AbstractEventType):
    """An event of a new lobby name that has been discovered"""
    #static field name to standardize the dictionary key
    s_discovered_lobby="discovered_lobby"

    def __init__(self, discovered_lobby: str)->None:
        self._event=EventType.DISCOVERED_LOBBY
        self._discovered_lobby=discovered_lobby

    @property
    def discovered_lobby(self)->str:
        """Returns the name of the discovered lobby the event contains"""
        return self._discovered_lobby
    
    def as_dictionary(self) -> dict:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, DiscoveredLobbyType.s_discovered_lobby:self._discovered_lobby}
    
def create_change_screen_type(dict: dict)->ChangeScreenType:
    """Creates a changing screen type from a correct dictionary"""
    event=dict.get(ChangeScreenType.s_event)
    assert(event!=EventType.NONE and event!=None)
    next_screen=dict.get(ChangeScreenType.s_next_screen)
    assert(next_screen!=None)
    return ChangeScreenType(next_screen)

def create_discovered_lobby_type(dict: dict)->DiscoveredLobbyType:
    """Creates a discovered lobby type from a correct dictionary"""
    event=dict.get(DiscoveredLobbyType.s_event)
    assert(event!=EventType.NONE and event!=None)
    discovered_lobby=dict.get(DiscoveredLobbyType.s_discovered_lobby)
    assert(discovered_lobby!=None)
    return DiscoveredLobbyType(discovered_lobby)

def createCustomEventFromDict(dict:dict)->AbstractEventType:
    """Creates an event type from a dictionary by parsing the event field. If the event field doesn't match a Value error is thrown"""
    event=dict.get(AbstractEventType.s_event)
    if event!=None:
        if event==EventType.CHANGE_SCREEN:
            return create_change_screen_type(dict)
        else:
            if event==EventType.DISCOVERED_LOBBY:
                return create_discovered_lobby_type(dict)
            else:
                raise ValueError("Dictionary event must be one of the EventType enums")         
    else:
        raise ValueError("Dictionary must contain event key")
    

class CustomEventSender():
    """This class is used to send custom events to the GUI"""
    def __init__(self) -> None:
        pygame.init()
        self._custom_event=pygame.event.custom_type() #Set once by custom event sender initialization
    
    def send_event_go_day_voting(self)->None:
        """Sends a custom event to change screen to day_voting"""
        pygame.event.post(pygame.event.Event(self._custom_event, ChangeScreenType(Screens.DAY_VOTING).as_dictionary()))
    
    def send_event_discovered_new_lobby(self, lobby_name: str)->None:
        """Sends a custom event to change screen to day_voting"""
        pygame.event.post(pygame.event.Event(self._custom_event, DiscoveredLobbyType(lobby_name).as_dictionary()))

    @property
    def custom_event(self)->int:
        """Returns the id of custom events"""
        return self._custom_event

    def test(self)->None:
        """TODO: remove function, used for testing purpose"""
        #self.send_event_go_day_voting()
        self.send_event_discovered_new_lobby("Lobby A")

if __name__ == "__main__": 
    print("Hello world")
