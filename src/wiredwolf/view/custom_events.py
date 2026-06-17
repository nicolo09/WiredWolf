from abc import ABC, abstractmethod
from typing import Any
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.lobbies import LobbyInfo
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

class LobbyType(AbstractEventType):
    """An event of a new lobby info that has been discovered"""
    #static field name to standardize the dictionary key
    s_lobby_name="lobby_name"
    s_has_password="has_password"
    s_number_of_peers="n_peers"
    s_max_peers="max_peers"
    s_uuid="uuid"
    s_action="action"
    s_action_add="add"
    s_action_remove="remove"

    def __init__(self, lobby: LobbyInfo, action:str)->None:
        self._event=EventType.LOBBY
        self._lobby=lobby
        self._action=action
        assert(action==self.s_action_add or  action==self.s_action_remove) #Only add or remove are legal actions

    @property
    def lobby_info(self)->LobbyInfo:
        """Returns the lobby info of the discovered lobby the event contains"""
        return self._lobby
    
    @property
    def action(self)->str:
        """Returns the action connected to the lobby"""
        return self._action
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, LobbyType.s_lobby_name:self._lobby.name, LobbyType.s_has_password: self._lobby.has_password, 
                LobbyType.s_number_of_peers: self._lobby.peers_number, LobbyType.s_max_peers: self._lobby.max_peers, 
                LobbyType.s_uuid: self._lobby.uuid, LobbyType.s_action: self._action}
   
    
class UsersType(AbstractEventType):
    """An event regarding a user, with a given username and an action"""
    #static field name to standardize the dictionary key
    s_user_name="user_name"
    s_user_id="user_id"
    s_action="action"
    s_action_add="add"
    s_action_remove="remove"

    def __init__(self, user: Peer, action:str)->None:
        self._event=EventType.USERNAME
        self._user=user
        self._action=action
        assert(action==self.s_action_add or  action==self.s_action_remove)

    @property
    def user(self)->Peer:
        """Returns the user contained in the event"""
        return self._user
    
    @property
    def action(self)->str:
        """Returns the action connected to the username"""
        return self._action
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, UsersType.s_user_name:self._user.name, UsersType.s_user_id:self._user.uuid, UsersType.s_action: self._action}
    
class TimeOutType(AbstractEventType):
    """An event triggered after some time has passed"""

    def __init__(self)->None:
        self._event=EventType.TIMEOUT
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event}

class DeadPlayerType(AbstractEventType):
    """An event triggered when the player is killed"""

    def __init__(self)->None:
        self._event=EventType.DEAD_PLAYER
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event}
    
class ErrorType(AbstractEventType):
    """An event sent to go to the error screen"""

    #static field name to standardize the dictionary key
    s_title="title"
    s_message="message"

    def __init__(self, title:str, message:str)->None:
        self._event=EventType.ERROR
        self._title=title
        self._message=message

    @property
    def title(self)->str:
        """Returns the title of the error contained in the event"""
        return self._title
    
    @property
    def message(self)->str:
        """Returns the message of the error contained in the event"""
        return self._message
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, ErrorType.s_title:self._title, ErrorType.s_message:self._message}
     
class EndErrorType(AbstractEventType):
    """An event sent to exit the error screen"""

    s_next_screen="next_screen"

    def __init__(self, next_screen:Screens=Screens.NONE)->None:
        self._event=EventType.END_ERROR
        self._next_screen=next_screen
    
    @property
    def next_screen(self)->Screens:
        """Returns the next screen of the end error message"""
        return self._next_screen
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event, EndErrorType.s_next_screen:self._next_screen}

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
    """An event sent containing informing the view that the game role has been set"""
    #static field name to standardize the dictionary key

    def __init__(self)->None:
        self._event=EventType.GAME_ROLE
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        return {AbstractEventType.s_event:self._event}


def create_change_screen_type(dict: dict[Any, Any])->ChangeScreenType:
    """Creates a changing screen type from a correct dictionary"""
    event=dict.get(ChangeScreenType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.CHANGE_SCREEN)
    next_screen=dict.get(ChangeScreenType.s_next_screen)
    assert(next_screen!=None)
    return ChangeScreenType(next_screen)

def create_lobby_type(dict: dict[Any, Any])->LobbyType:
    """Creates a discovered lobby type from a correct dictionary"""
    event=dict.get(LobbyType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.LOBBY)
    name_lobby=dict.get(LobbyType.s_lobby_name)
    assert(name_lobby!=None)
    action=dict.get(LobbyType.s_action)
    assert(action!=None and (action==LobbyType.s_action_add or action==LobbyType.s_action_remove))
    has_password=dict.get(LobbyType.s_has_password)
    assert(has_password!=None)
    n_peers=dict.get(LobbyType.s_number_of_peers)
    assert(n_peers!=None)
    n_peers=int(n_peers)
    max_peers=dict.get(LobbyType.s_max_peers)
    assert(max_peers!=None)
    uuid=dict.get(LobbyType.s_uuid)
    assert(uuid!=None)
    return LobbyType(LobbyInfo(name=name_lobby, peers_number=n_peers, max_peers=max_peers, has_password=has_password, uuid=uuid), action)

def create_users_type(dict: dict[Any, Any])->UsersType:
    """Creates a users type from a correct dictionary"""
    event=dict.get(UsersType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.USERNAME)
    username=dict.get(UsersType.s_user_name)
    assert(username!=None)
    user_id=dict.get(UsersType.s_user_id)
    assert(user_id!=None)
    action=dict.get(UsersType.s_action)
    assert(action!=None and (action==UsersType.s_action_add or action==UsersType.s_action_remove))
    return UsersType(Peer(username, user_id), action)

def create_timeout_type(dict:dict[Any, Any])->TimeOutType:
    """Creates a timeout type from a correct dictionary"""
    event=dict.get(TimeOutType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.TIMEOUT)
    return TimeOutType()

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
    return GameRoleType()

def create_error_type(dict:dict[Any, Any])->ErrorType:
    """Creates a error type from a correct dictionary"""
    event=dict.get(ErrorType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.ERROR)
    title=dict.get(ErrorType.s_title)
    assert(title!=None)
    message=dict.get(ErrorType.s_message)
    assert(message!=None)
    return ErrorType(title, message)

def create_end_error_type(dict:dict[Any, Any])->EndErrorType:
    """Creates a end error type from a correct dictionary"""
    event=dict.get(EndErrorType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.END_ERROR)
    next_screen=dict.get(EndErrorType.s_next_screen)
    assert(next_screen!=None)
    return EndErrorType(next_screen)

def create_dead_player_type(dict:dict[Any, Any])->DeadPlayerType:
    event=dict.get(DeadPlayerType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.DEAD_PLAYER)
    return DeadPlayerType()

def create_custom_event_from_dict(dict:dict[Any, Any])->AbstractEventType:
    """Creates an event type from a dictionary by parsing the event field. If the event field doesn't match a Value error is thrown"""
    event=dict.get(AbstractEventType.s_event)
    if event!=None:
        match event:
            case EventType.CHANGE_SCREEN:
                return create_change_screen_type(dict)
            case EventType.LOBBY:
                return create_lobby_type(dict)
            case EventType.USERNAME:
                return create_users_type(dict)
            case EventType.TIMEOUT:
                return create_timeout_type(dict)
            case EventType.CHAT_MESSAGE:
                return create_chat_message_type(dict)
            case EventType.GAME_ROLE:
                return create_game_role_type(dict)
            case EventType.ERROR:
                return create_error_type(dict)
            case EventType.END_ERROR:
                return create_end_error_type(dict)
            case EventType.DEAD_PLAYER:
                return create_dead_player_type(dict)
            case _: #default case, no matches
                raise ValueError("Dictionary event must be one of the EventType enums")         
    else:
        raise ValueError("Dictionary must contain event key")

class EventSender(ABC):
    """Abstract interface to abstract the sending of events to the view"""

    @abstractmethod
    def new_discovered_lobby(self, lobby:LobbyInfo)->None:
        """Add a new discovered lobby to the view"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def remove_discovered_lobby(self, lobby:LobbyInfo)->None:
        """Remove a new discovered lobby to the view"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def new_user_in_lobby(self, user:Peer)->None:
        """The username of a user that joined a lobby waiting for the game to start"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def remove_user_in_lobby(self, user:Peer)->None:
        """The username of a user that exited a lobby waiting for the game to start"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def game_started_by_master(self)->None:
        """Communicates to the other players that the game was started by the master of the lobby, goes to role screen"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def game_started_by_master_with_role(self)->None:
        """Communicates to the other players that the game was started by the master of the lobby, goes to role screen and fetches information about the role"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def start_first_day(self)->None:
        """After displaying the role screen, starts the game by displaying the first day screen"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def start_nomination_for_execution(self, players:list[Peer])->None: 
        """The list of players possible to choose from when nominating for execution and starts voting"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def user_to_nominated_for_ballot(self, user:Peer)->None:
        """Changes the screen and displays the user nominated to be executed"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def display_chat_message(self, message:str)->None:
        """Displays a chat message sent by a user"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def start_night(self, is_villager:bool, number_night:int)->None:
        """Starts the night screens"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def end_night(self, number_day:int)->None:
        """Ends the night screens"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def user_role(self)->None:
        """Sends a message to the view to fetch the game role"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def can_use_powers_on(self, player_list:list[Peer])->None:
        """The list of users the player can use their powers on (ex: werewolves can't kill other werewolves)"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def villager_win(self)->None:
        """Tells the view that villagers won and goes to the end day screen"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def werewolf_win(self)->None:
        """Tells the view that werewolves won and goes to the end day screen"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def message_player_executed(self, user:str)->None:
        """Sends a message to the view telling the players that user was executed"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def message_player_spared(self, user:str)->None:
        """Sends a message to the view telling the players that user was spared"""
        raise NotImplementedError("Please implement this method")
    @abstractmethod
    def message_player_killed_during_night(self, user:str)->None:
        """Sends a message to the view telling the players that user was killed during the night"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def error_occurred(self, title:str, message:str)->None:
        """Sends the error to the view"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def error_ended(self)->None:
        """Sends the end of error to the view. Gets from the controller the game phase and decides which screen to go to"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def error_ended_go_to_screen(self, next_screen:Screens)->None:
        """Sends the end of error to the view and changes screen to the given one"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def error_ended_go_to_home(self)->None:
        """Sends the end of error to the view and changes screen to the home screen. Controller needs to call view.reset to properly reset the view"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def player_is_dead(self)->None:
        """Triggers ghost player view, called after player is executed or if player is killed by werewolves at night"""
        raise NotImplementedError("Please implement this method")

class StatusMessages():
    """A simple class that constructs messages sent by the server, like winning and users killed"""
    def __init__(self, msg_sender:str="GameServer") -> None:
        self._msg_sender=msg_sender
    
    def message_day(self, day:int)->str:
        """Returns the message containing how many days have passed"""
        return self._msg_sender+": Day "+str(day)
    
    def message_night(self, night:int)->str:
        """Returns the message containing how many nights have passed"""
        return self._msg_sender+": Night "+str(night)

    def wolf_win(self)->str:
        """Returns the message that werewolves have won"""
        return self._msg_sender+": Werewolves won!"
    
    def villager_win(self)->str:
        """Returns the message that villagers have won"""
        return self._msg_sender+": Villagers won!"
    
    def user_executed(self, username:str)->str:
        """Returns the message that a user was executed"""
        return self._msg_sender+": "+username+" was executed and killed"

    def user_spared(self, username:str)->str:
        """Returns the message that a user was spared"""
        return self._msg_sender+": "+username+" was spared"
    
    def user_killed_during_night(self, username:str)->str:
        """Returns the message that a user was killed during the night"""
        return self._msg_sender+": "+username+" was killed during the night"

class CustomEventSender(EventSender):
    """This class is used to send custom events to the GUI"""
    def __init__(self, times:int=-1) -> None:
        pygame.init()
        self._custom_event=pygame.event.custom_type() #Set once by custom event sender initialization
        self._status_messages=StatusMessages()
    
    def send_event_to_screen(self, screen:Screens)->None:
        """Sends a custom event to change screen to the given screen"""
        pygame.event.post(pygame.event.Event(self._custom_event, ChangeScreenType(screen).as_dictionary()))
    
    def send_event_new_lobby(self, lobby: LobbyInfo)->None:
        """Sends a custom event to add a new lobby"""
        pygame.event.post(pygame.event.Event(self._custom_event, LobbyType(lobby, LobbyType.s_action_add).as_dictionary()))

    def send_event_removed_lobby(self, lobby: LobbyInfo)->None:
        """Sends a custom event to remove a lobby"""
        pygame.event.post(pygame.event.Event(self._custom_event, LobbyType(lobby, LobbyType.s_action_remove).as_dictionary()))

    def send_event_add_user(self, user:Peer)->None:
        """Sends a custom event to add a new user"""
        pygame.event.post(pygame.event.Event(self._custom_event, UsersType(user, UsersType.s_action_add).as_dictionary()))

    def send_event_execute_or_spare_user(self, user:Peer)->None:
        """Sends a custom event to notify gui which player is to be spared or executed"""
        pygame.event.post(pygame.event.Event(self._custom_event, UsersType(user, UsersType.s_action_add).as_dictionary()))
    
    def send_event_remove_user(self, user:Peer)->None:
        """Sends a custom event to remove a user"""
        pygame.event.post(pygame.event.Event(self._custom_event, UsersType(user, UsersType.s_action_remove).as_dictionary()))

    def send_event_timeout(self)->None:
        """Sends a custom event to say that some time has passed"""
        pygame.event.post(pygame.event.Event(self._custom_event, TimeOutType().as_dictionary()))

    def send_event_dead_player(self)->None:
        """Sends a custom event to say that the player has died"""
        pygame.event.post(pygame.event.Event(self._custom_event, DeadPlayerType().as_dictionary()))

    def send_event_chat_message(self, message:str)->None:
        """Sends a custom event to send a chat message"""
        pygame.event.post(pygame.event.Event(self._custom_event, ChatMessageType(message).as_dictionary()))
    
    def send_event_game_role(self)->None:
        """Sends a custom event telling the view that the game role has been set"""
        pygame.event.post(pygame.event.Event(self._custom_event, GameRoleType().as_dictionary()))
    
    def send_event_error(self, title:str, message:str)->None:
        """Sends a custom event containing the error message"""
        pygame.event.post(pygame.event.Event(self._custom_event, ErrorType(title, message).as_dictionary()))

    def send_event_end_error(self, next_screen:Screens=Screens.NONE)->None:
        """Sends a custom event containing the end of the error"""
        pygame.event.post(pygame.event.Event(self._custom_event, EndErrorType(next_screen).as_dictionary())) 

    @property
    def custom_event(self)->int:
        """Returns the id of custom events"""
        return self._custom_event

    def new_discovered_lobby(self, lobby: LobbyInfo) -> None:
        self.send_event_new_lobby(lobby)

    def remove_discovered_lobby(self, lobby:LobbyInfo)->None:
        self.send_event_removed_lobby(lobby)

    def new_user_in_lobby(self, user:Peer) -> None:
        self.send_event_add_user(user)

    def remove_user_in_lobby(self, user:Peer) -> None:
        self.send_event_remove_user(user)

    def game_started_by_master(self) -> None:
        self.send_event_to_screen(Screens.ROLE_DISPLAY)

    def game_started_by_master_with_role(self) -> None:
        self.send_event_to_screen(Screens.ROLE_DISPLAY)
        self.send_event_game_role()

    def start_nomination_for_execution(self, players: list[Peer]) -> None:
        #Day message not needed, as the chat is shared with day chat
        for elem in players:
            self.send_event_add_user(elem)
        self.start_voting_for_nominations()

    def start_voting_for_nominations(self) -> None:
        self.send_event_timeout()
        #TODO: message?

    def user_to_nominated_for_ballot(self, user:Peer) -> None:
        #TODO: num day?
        self.send_event_to_screen(Screens.DAY_EXECUTION)
        self.send_event_add_user(user)

    def display_chat_message(self, message: str) -> None:
        self.send_event_chat_message(message)

    def start_night(self, is_villager: bool, number_night:int) -> None:
        if is_villager==True:
            self.send_event_to_screen(Screens.NIGHT_VILLAGER)
        else:
            self.send_event_to_screen(Screens.NIGHT_ROLE)
        self.night_message(number_night)

    def end_night(self, number_day:int) -> None:
        self.send_event_to_screen(Screens.DAY_VOTING)
        self.day_message(number_day)
    
    def start_first_day(self)->None:
        self.send_event_to_screen(Screens.DAY_VOTING)
        self.day_message(1) #Day inferred

    def user_role(self) -> None:
        self.send_event_game_role()

    def can_use_powers_on(self, player_list: list[Peer]) -> None:
        for elem in player_list:
            self.send_event_add_user(elem)
        #Added timeout to signify the end of allowed players and the start of searching for disabled players
        self.send_event_timeout()

    def villager_win(self) -> None:
       #Goes to end day screen
       self.send_event_to_screen(Screens.DAY_END)
       self.send_event_chat_message(self._status_messages.villager_win())

    def werewolf_win(self) -> None:
        #Goes to end day screen
        self.send_event_to_screen(Screens.DAY_END)
        self.send_event_chat_message(self._status_messages.wolf_win())

    def day_message(self, day:int)->None:
        self.send_event_chat_message(self._status_messages.message_day(day))
    
    def night_message(self, night:int)->None:
        self.send_event_chat_message(self._status_messages.message_night(night))
        
    def message_player_executed(self, user:str)->None:
        self.send_event_chat_message(self._status_messages.user_executed(user))
    
    def message_player_spared(self, user:str)->None:
        self.send_event_chat_message(self._status_messages.user_spared(user))
    
    def message_player_killed_during_night(self, user:str)->None:
        self.send_event_chat_message(self._status_messages.user_killed_during_night(user))

    def error_occurred(self, title:str, message:str)->None:
        self.send_event_error(title, message)
    
    def error_ended(self)->None:
        self.send_event_end_error()

    def error_ended_go_to_screen(self, next_screen:Screens)->None:
        self.send_event_end_error(next_screen)
    
    def error_ended_go_to_home(self)->None:
        self.send_event_end_error(Screens.HOME)

    def player_is_dead(self)->None:
        self.send_event_dead_player()

