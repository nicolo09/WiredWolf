from abc import ABC, abstractmethod
from typing import Any
from wiredwolf.view.constants import EventType, Screens
import pygame
from dataclasses import dataclass

@dataclass
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
    def as_dictionary(self)->dict[Any, Any]:
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
    
    def as_dictionary(self) -> dict[Any, Any]:
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
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, DiscoveredLobbyType.s_discovered_lobby:self._discovered_lobby}
    
class UsersType(AbstractEventType):
    """An event regarding a user, with a given username"""
    #static field name to standardize the dictionary key
    s_username="username"

    def __init__(self, username: str)->None:
        self._event=EventType.USERNAME
        self._username=username

    @property
    def username(self)->str:
        """Returns the username contained in the event"""
        return self._username
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, UsersType.s_username:self._username}
    
class TimeOutType(AbstractEventType):
    """An event triggered after some time has passed"""

    def __init__(self)->None:
        self._event=EventType.TIMEOUT
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event}

class WaitingRoomType(AbstractEventType):
    """An event sent to update how many users are in a waiting room"""

    #static field name to standardize the dictionary key
    s_number="number"

    def __init__(self, number:int)->None:
        self._event=EventType.WAITING_ROOM
        self._number=number

    @property
    def number(self)->int:
        """Returns the number of waiting users contained in the event"""
        return self._number
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, WaitingRoomType.s_number:self._number}
    
class ChatMessageType(AbstractEventType):
    """An event sent containing a chat message"""

    #static field name to standardize the dictionary key
    s_message="message"

    def __init__(self, message:str)->None:
        self._event=EventType.CHAT_MESSAGE
        self._message=message

    @property
    def message(self)->str:
        """Returns the chat message contained in the event"""
        return self._message
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, ChatMessageType.s_message:self._message}

class GameRoleType(AbstractEventType):
    """An event sent containing a the player role"""
    #static field name to standardize the dictionary key
    s_role_name="role_name"
    s_role_descr="role_desc"

    def __init__(self, role:str, description:str)->None:
        self._event=EventType.GAME_ROLE
        self._role=role
        self._desc=description

    @property
    def role(self)->str:
        """Returns the role name contained in the event"""
        return self._role
    
    @property
    def role_description(self)->str:
        """Returns the role description contained in the event"""
        return self._desc
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, GameRoleType.s_role_name:self._role, GameRoleType.s_role_descr: self._desc}


def create_change_screen_type(dict: dict[Any, Any])->ChangeScreenType:
    """Creates a changing screen type from a correct dictionary"""
    event=dict.get(ChangeScreenType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.CHANGE_SCREEN)
    next_screen=dict.get(ChangeScreenType.s_next_screen)
    assert(next_screen!=None)
    return ChangeScreenType(next_screen)

def create_discovered_lobby_type(dict: dict[Any, Any])->DiscoveredLobbyType:
    """Creates a discovered lobby type from a correct dictionary"""
    event=dict.get(DiscoveredLobbyType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.DISCOVERED_LOBBY)
    discovered_lobby=dict.get(DiscoveredLobbyType.s_discovered_lobby)
    assert(discovered_lobby!=None)
    return DiscoveredLobbyType(discovered_lobby)

def create_users_type(dict: dict[Any, Any])->UsersType:
    """Creates a users type from a correct dictionary"""
    event=dict.get(UsersType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.USERNAME)
    username=dict.get(UsersType.s_username)
    assert(username!=None)
    return UsersType(username)

def create_timeout_type(dict:dict[Any, Any])->TimeOutType:
    """Creates a timeout type from a correct dictionary"""
    event=dict.get(TimeOutType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.TIMEOUT)
    return TimeOutType()

def create_waiting_room_type(dict:dict[Any, Any])->WaitingRoomType:
    """Creates a waiting room type from a correct dictionary"""
    event=dict.get(WaitingRoomType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.WAITING_ROOM)
    number=dict.get(WaitingRoomType.s_number)
    assert(number!=None)
    return WaitingRoomType(number)

def create_chat_message_type(dict:dict[Any, Any])->ChatMessageType:
    """Creates a chat message type from a correct dictionary"""
    event=dict.get(ChatMessageType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.CHAT_MESSAGE)
    message=dict.get(ChatMessageType.s_message)
    assert(message!=None)
    return ChatMessageType(message)

def create_game_role_type(dict:dict[Any, Any])->GameRoleType:
    """Creates a game role type from a correct dictionary"""
    event=dict.get(GameRoleType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.GAME_ROLE)
    role=dict.get(GameRoleType.s_role_name)
    assert(role!=None)
    desc=dict.get(GameRoleType.s_role_descr)
    assert(desc!=None)
    return GameRoleType(role, desc)

def create_custom_event_from_dict(dict:dict[Any, Any])->AbstractEventType:
    """Creates an event type from a dictionary by parsing the event field. If the event field doesn't match a Value error is thrown"""
    event=dict.get(AbstractEventType.s_event)
    if event!=None:
        match event:
            case EventType.CHANGE_SCREEN:
                return create_change_screen_type(dict)
            case EventType.DISCOVERED_LOBBY:
                return create_discovered_lobby_type(dict)
            case EventType.USERNAME:
                return create_users_type(dict)
            case EventType.TIMEOUT:
                return create_timeout_type(dict)
            case EventType.WAITING_ROOM:
                return create_waiting_room_type(dict)
            case EventType.CHAT_MESSAGE:
                return create_chat_message_type(dict)
            case EventType.GAME_ROLE:
                return create_game_role_type(dict)
            case _: #default case, no matches
                raise ValueError("Dictionary event must be one of the EventType enums")         
    else:
        raise ValueError("Dictionary must contain event key")
    

class EventSender(ABC):
    """Abstract interface to abstract the sending of events to the view"""

    @abstractmethod
    def discovered_lobbies(self, lobbies_list:list[str])->None:
        """The list of all discovered lobbies in the network"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def users_waiting_to_start_game(self, number:int)->None:
        """The number of how many users are waiting for the game to start"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def game_started_by_master(self)->None:
        """Communicates to the other players that the game was started by the master of the lobby"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def players_to_nominate_for_execution(self, players:list[str])->None:
        """The list of players possible to choose from when nominating for execution"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def start_voting_for_nominations(self)->None:
        """Players can start nominating for execution"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def start_voting_for_execution(self)->None:
        """Players can start voting for execution"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def user_to_nominated_for_execution(self, username:str)->None:
        """The user nominated to be executed"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def display_chat_message(self, message:str)->None:
        """Displays a chat message sent by another user"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def start_night(self, is_villager:bool)->None:
        """Starts the night screens"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def end_night(self)->None:
        """Ends the night screens"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def user_role(self, role_name:str, role_description:str)->None:
        """Sends the user role and a brief description to the view"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def can_use_powers_on(self, player_list:str)->None:
        """The list of users the player can use their powers on (ex: werewolves can't kill other werewolves)"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def villager_win(self)->None:
        """Tells the view that villagers won"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def villager_loss(self)->None:
        """Tells the view that villagers lost"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def werewolf_win(self)->None:
        """Tells the view that werewolves won"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def werewolf_loss(self)->None:
        """Tells the view that werewolves lost"""
        raise NotImplementedError("Please implement this method")

class CustomEventSender(EventSender):
    """This class is used to send custom events to the GUI"""
    def __init__(self, times:int=-1) -> None:
        pygame.init()
        self._custom_event=pygame.event.custom_type() #Set once by custom event sender initialization
        self._times=times
        self._counter=0
    
    def send_event_to_screen(self, screen:Screens)->None:
        """Sends a custom event to change screen to the given screen"""
        pygame.event.post(pygame.event.Event(self._custom_event, ChangeScreenType(screen).as_dictionary()))
    
    def send_event_discovered_new_lobby(self, lobby_name: str)->None:
        """Sends a custom event to add a new lobby"""
        pygame.event.post(pygame.event.Event(self._custom_event, DiscoveredLobbyType(lobby_name).as_dictionary()))

    def send_event_new_user(self, username:str)->None:
        """Sends a custom event to add a new user"""
        pygame.event.post(pygame.event.Event(self._custom_event, UsersType(username).as_dictionary()))

    def send_event_execute_or_spare_user(self, username:str)->None:
        """Sends a custom event to notify gui which player is to be spared or executed"""
        pygame.event.post(pygame.event.Event(self._custom_event, UsersType(username).as_dictionary()))

    def send_event_timeout(self)->None:
        """Sends a custom event to say that some time has passed"""
        pygame.event.post(pygame.event.Event(self._custom_event, TimeOutType().as_dictionary()))

    def send_event_waiting_room(self, number:int)->None:
        """Sends a custom event to say how many players are in the waiting room"""
        pygame.event.post(pygame.event.Event(self._custom_event, WaitingRoomType(number).as_dictionary()))

    def send_event_chat_message(self, message:str)->None:
        """Sends a custom event to send a chat message"""
        pygame.event.post(pygame.event.Event(self._custom_event, ChatMessageType(message).as_dictionary()))
    
    def send_event_game_role(self, role:str, description:str)->None:
        """Sends a custom event containing the game role"""
        pygame.event.post(pygame.event.Event(self._custom_event, GameRoleType(role, description).as_dictionary()))

    @property
    def custom_event(self)->int:
        """Returns the id of custom events"""
        return self._custom_event

    def test(self)->None:
        """TODO: remove function, used for testing purpose"""
        if self._counter!=self._times and self._times!=-1:
            #limit to avoid infinite events
            self._counter=self._counter+1
            #self.send_event_go_day_voting()
            #self.send_event_discovered_new_lobby("Lobby A")
            #self.send_event_new_user("Mario")
            #self.send_event_timeout()
            #self.send_event_waiting_room(10)
            #self.send_event_chat_message("Mario: ciao")
            self.send_event_execute_or_spare_user("Mario")
            self.send_event_game_role("werewolf", "kill people")
        if self._times==-1:
            #send event forever
            #self.send_event_new_user("Mario")
            #self.send_event_waiting_room(10)
            self.send_event_chat_message("Mario: ciao")

    def discovered_lobbies(self, lobbies_list: list[str]) -> None:
        for elem in lobbies_list:
            self.send_event_discovered_new_lobby(elem)

    def users_waiting_to_start_game(self, number: int) -> None:
        self.send_event_waiting_room(number)

    def game_started_by_master(self) -> None:
        self.send_event_to_screen(Screens.DAY_VOTING)

    def players_to_nominate_for_execution(self, players: list[str]) -> None:
        for elem in players:
            self.send_event_new_user(elem)

    def start_voting_for_nominations(self) -> None:
        self.send_event_timeout()

    def start_voting_for_execution(self) -> None:
        self.send_event_to_screen(Screens.DAY_EXECUTION)

    def user_to_nominated_for_execution(self, username: str) -> None:
        self.send_event_new_user(username)

    def display_chat_message(self, message: str) -> None:
        self.send_event_chat_message(message)

    def start_night(self, is_villager: bool) -> None:
        if is_villager==True:
            self.send_event_to_screen(Screens.NIGHT_VILLAGER)
        else:
            self.send_event_to_screen(Screens.NIGHT_ROLE)

    def end_night(self) -> None:
        self.send_event_to_screen(Screens.DAY_VOTING)

    def user_role(self, role_name: str, role_description: str) -> None:
        self.send_event_game_role(role_name, role_description)

    def can_use_powers_on(self, player_list: str) -> None:
        for elem in player_list:
            self.send_event_new_user(elem)

    def villager_win(self) -> None:
        self.send_event_to_screen(Screens.VILLAGER_WIN)

    def villager_loss(self) -> None:
        self.send_event_to_screen(Screens.VILLAGER_LOSS)

    def werewolf_win(self) -> None:
        self.send_event_to_screen(Screens.WOLF_WIN)

    def werewolf_loss(self) -> None:
        self.send_event_to_screen(Screens.WOLF_LOSS)

if __name__ == "__main__": 
    print("Hello world")
