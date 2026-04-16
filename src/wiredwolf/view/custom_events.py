from abc import ABC, abstractmethod
from typing import Any
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.lobbies import Lobby
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
    

def create_peer_dict(peers:set[Peer])->dict[str, str]:
    """Creates a dictionary of all peers joined into a lobby, with keys peer_joined_name_N: name and peer_joined_uuid_N : uuid"""
    peer_dictionary:dict[str, str]={}
    i=0
    for elem in peers:
        tmp=LobbyType.s_peer_joined_name+str(i)
        peer_dictionary[tmp]=elem.name
        tmp=LobbyType.s_peer_joined_uuid+str(i)
        peer_dictionary[tmp]=elem.uuid
        i=i+1
    return peer_dictionary

def create_peer_set(peers:dict[str, str], size:int)->set[Peer]:
    """Creates a list of all peers joined into a lobby, from a dictionary formatted with keys peer_joined_name_N: name and peer_joined_uuid_N : uuid"""
    peer_set:set[Peer]=set()
    for i in range(0, size):
        tmp=LobbyType.s_peer_joined_name+str(i)
        name=peers[tmp]
        tmp=LobbyType.s_peer_joined_uuid+str(i)
        uuid=peers[tmp]
        peer_set.add(Peer(name, uuid))
    return peer_set

class LobbyType(AbstractEventType):
    """An event of a new lobby name that has been discovered"""
    #static field name to standardize the dictionary key
    s_lobby_name="lobby_name"
    s_owner_name="owner_name"
    s_owner_uuid="owner_uuid"
    s_password="password"
    s_number_of_peers="n_peers"
    s_peer_joined_name="peer_joined_name_"
    s_peer_joined_uuid="peer_joined_uuid_"
    s_action="action"
    s_action_add="add"
    s_action_remove="remove"

    def __init__(self, lobby: Lobby, action:str)->None:
        self._event=EventType.LOBBY
        self._lobby=lobby
        self._action=action
        assert(action==self.s_action_add or  action==self.s_action_remove) #Only add or remove are legal actions

    @property
    def lobby(self)->Lobby:
        """Returns the name of the discovered lobby the event contains"""
        return self._lobby
    
    @property
    def action(self)->str:
        """Returns the action connected to the lobby"""
        return self._action
    
    def as_dictionary(self) -> dict[Any, Any]:
        """Returns all the fields of the event as a dictionary, used when creating the event in pygame.event.Event()"""
        n=len(self.lobby.peers)
        dictionary:dict[Any,Any]={AbstractEventType.s_event:self._event, LobbyType.s_lobby_name:self._lobby.name, 
                LobbyType.s_owner_name: self._lobby.owner.name, LobbyType.s_owner_uuid: self._lobby.owner.uuid,
                LobbyType.s_number_of_peers:str(n), 
                LobbyType.s_action: self._action}
        if n!=0:
            #If there are peers in the lobby
            peer_dict=create_peer_dict(self.lobby.peers)
            #Add peers to dictionary
            dictionary.update(peer_dict)
        if self._lobby.password!=None:
            #Password is set
            dictionary.update({LobbyType.s_password:self._lobby.password})
        else:
            dictionary.update({LobbyType.s_password:""})
        return dictionary
   
    
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

class WaitingRoomType(AbstractEventType):
    """An event sent to update how many users are in a waiting room"""
    #TODO: consider removal, unused

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

def create_lobby_type(dict: dict[Any, Any])->LobbyType:
    """Creates a discovered lobby type from a correct dictionary"""
    event=dict.get(LobbyType.s_event)
    assert(event!=EventType.NONE and event!=None and event==EventType.LOBBY)
    name_lobby=dict.get(LobbyType.s_lobby_name)
    assert(name_lobby!=None)
    action=dict.get(LobbyType.s_action)
    assert(action!=None and (action==LobbyType.s_action_add or action==LobbyType.s_action_remove))
    owner_name=dict.get(LobbyType.s_owner_name)
    assert(owner_name!=None)
    owner_uuid=dict.get(LobbyType.s_owner_uuid)
    assert(owner_uuid!=None)
    peer_n=dict.get(LobbyType.s_number_of_peers)
    assert(peer_n!=None)
    peer_n=int(peer_n)
    peer_set:set[Peer]=set() #List of peers
    if peer_n>0:
        peer_set=create_peer_set(dict, peer_n)
    assert(len(peer_set)==peer_n) #The new list of peers must be the same size of the original list
    password=dict.get(LobbyType.s_password)
    assert(password!=None)
    if password=="":
        #If no password is set, password field is set to None
        password=None
    lobby=Lobby(owner=Peer(owner_name, owner_uuid), password=password, name=name_lobby)
    for elem in peer_set:
        #Add peers to lobby
        lobby.peers.add(elem)
    return LobbyType(lobby, action)

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
            case EventType.WAITING_ROOM:
                return create_waiting_room_type(dict)
            case EventType.CHAT_MESSAGE:
                return create_chat_message_type(dict)
            case EventType.GAME_ROLE:
                return create_game_role_type(dict)
            case EventType.ERROR:
                return create_error_type(dict)
            case EventType.END_ERROR:
                return create_end_error_type(dict)
            case _: #default case, no matches
                raise ValueError("Dictionary event must be one of the EventType enums")         
    else:
        raise ValueError("Dictionary must contain event key")

class EventSender(ABC):
    """Abstract interface to abstract the sending of events to the view"""

    @abstractmethod
    def new_discovered_lobby(self, lobby:Lobby)->None:
        """Add a new discovered lobby to the view"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def remove_discovered_lobby(self, lobby:Lobby)->None:
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
    def start_first_day(self)->None:
        """After displaying the role screen, starts the game by displaying the first day screen"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def players_to_nominate_for_execution(self, players:list[Peer])->None:
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
    def can_use_powers_on(self, player_list:list[Peer])->None:
        """The list of users the player can use their powers on (ex: werewolves can't kill other werewolves)"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def villager_win(self)->None:
        """Tells the view that villagers won"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def werewolf_win(self)->None:
        """Tells the view that werewolves won"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def message_player_executed(self, user:str)->None:
        """Sends a message to the view telling the players that user was executed"""
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
        """Sends the end of error to the view"""
        raise NotImplementedError("Please implement this method")
    
    @abstractmethod
    def error_ended_go_to_screen(self, next_screen:Screens)->None:
        """Sends the end of error to the view and changes screen to the given one"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def start_voting_for_ballot(self)->None:
        """Starts the voting for guilty or innocent after a player has been nominated for execution"""
        raise NotImplementedError("Please implement this method")


class StatusMessages():
    """A simple class that constructs messages sent by the server. It keeps count of days"""
    def __init__(self, msg_sender:str="GameServer") -> None:
        self._day_count=1
        self._msg_sender=msg_sender
    
    def message_day(self)->str:
        """Returns the message containing how many days have passed"""
        return self._msg_sender+": Day "+str(self._day_count)
    
    def message_night(self)->str:
        """Returns the message containing how many nights have passed"""
        return self._msg_sender+": Night "+str(self._day_count)
    
    def next_day(self)->None:
        """A function that increments the day counter"""
        self._day_count=self._day_count+1

    def wolf_win(self)->str:
        """Returns the message that werewolves have won"""
        return self._msg_sender+": Werewolves won!"
    
    def villager_win(self)->str:
        """Returns the message that villagers have won"""
        return self._msg_sender+": Villagers won!"
    
    def user_executed(self, username:str)->str:
        """Returns the message that a user was executed"""
        return self._msg_sender+": "+username+" was executed and killed"
    
    def user_killed_during_night(self, username:str)->str:
        """Returns the message that a user was killed during the night"""
        return self._msg_sender+": "+username+" was killed during the night"

    @property
    def day_count(self)->int:
        """Returns the day count"""
        return self._day_count

class CustomEventSender(EventSender):
    """This class is used to send custom events to the GUI"""
    def __init__(self, times:int=-1) -> None:
        pygame.init()
        self._custom_event=pygame.event.custom_type() #Set once by custom event sender initialization
        self._times=times
        self._counter=0
        self._status_messages=StatusMessages()
    
    def send_event_to_screen(self, screen:Screens)->None:
        """Sends a custom event to change screen to the given screen"""
        pygame.event.post(pygame.event.Event(self._custom_event, ChangeScreenType(screen).as_dictionary()))
    
    def send_event_new_lobby(self, lobby: Lobby)->None:
        """Sends a custom event to add a new lobby"""
        pygame.event.post(pygame.event.Event(self._custom_event, LobbyType(lobby, LobbyType.s_action_add).as_dictionary()))

    def send_event_removed_lobby(self, lobby: Lobby)->None:
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

    def send_event_waiting_room(self, number:int)->None:
        """Sends a custom event to say how many players are in the waiting room"""
        pygame.event.post(pygame.event.Event(self._custom_event, WaitingRoomType(number).as_dictionary()))

    def send_event_chat_message(self, message:str)->None:
        """Sends a custom event to send a chat message"""
        pygame.event.post(pygame.event.Event(self._custom_event, ChatMessageType(message).as_dictionary()))
    
    def send_event_game_role(self, role:str, description:str)->None:
        """Sends a custom event containing the game role"""
        pygame.event.post(pygame.event.Event(self._custom_event, GameRoleType(role, description).as_dictionary()))
    
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

    def new_discovered_lobby(self, lobby: Lobby) -> None:
        self.send_event_new_lobby(lobby)

    def remove_discovered_lobby(self, lobby:Lobby)->None:
        self.send_event_removed_lobby(lobby)

    def new_user_in_lobby(self, user:Peer) -> None:
        self.send_event_add_user(user)

    def remove_user_in_lobby(self, user:Peer) -> None:
        self.send_event_remove_user(user)

    def game_started_by_master(self) -> None:
        self.send_event_to_screen(Screens.ROLE_DISPLAY)

    def players_to_nominate_for_execution(self, players: list[Peer]) -> None:
        for elem in players:
            self.send_event_add_user(elem)
        self.start_voting_for_nominations()

    def start_voting_for_nominations(self) -> None:
        self.send_event_timeout()
        #TODO: message?

    def user_to_nominated_for_ballot(self, user:Peer) -> None:
        self.send_event_to_screen(Screens.DAY_EXECUTION)
        self.send_event_add_user(user)

    def display_chat_message(self, message: str) -> None:
        self.send_event_chat_message(message)

    def start_night(self, is_villager: bool) -> None:
        if is_villager==True:
            self.send_event_to_screen(Screens.NIGHT_VILLAGER)
        else:
            self.send_event_chat_message(self._status_messages.message_night())
            self.send_event_to_screen(Screens.NIGHT_ROLE)

    def end_night(self) -> None:
        self.send_event_to_screen(Screens.DAY_VOTING)
        self._status_messages.next_day()
        self.day_message()
    
    def start_first_day(self)->None:
        self.send_event_to_screen(Screens.DAY_VOTING)
        self.day_message()

    def user_role(self, role_name: str, role_description: str) -> None:
        self.send_event_game_role(role_name, role_description)

    def can_use_powers_on(self, player_list: list[Peer]) -> None:
        for elem in player_list:
            self.send_event_add_user(elem)

    def villager_win(self) -> None:
       self.send_event_chat_message(self._status_messages.villager_win())

    def werewolf_win(self) -> None:
        self.send_event_chat_message(self._status_messages.wolf_win())

    def day_message(self)->None:
        self.send_event_chat_message(self._status_messages.message_day())
        
    def message_player_executed(self, user:str)->None:
        self.send_event_chat_message(self._status_messages.user_executed(user))
    
    def message_player_killed_during_night(self, user:str)->None:
        self.send_event_chat_message(self._status_messages.user_killed_during_night(user))

    def error_occurred(self, title:str, message:str)->None:
        self.send_event_error(title, message)
    
    def error_ended(self)->None:
        self.send_event_end_error()

    def error_ended_go_to_screen(self, next_screen:Screens)->None:
        self.send_event_end_error(next_screen)

