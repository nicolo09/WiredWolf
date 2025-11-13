import textwrap
from typing import List
import pygame
from abc import ABC, abstractmethod
from wiredwolf.view.CustomEvents import ChangeScreenType, CustomEventSender, DiscoveredLobbyType, TimeOutType, UsersType, create_custom_event_from_dict
from wiredwolf.view.Components import SelectorButton, VContainer, HContainer
from wiredwolf.view.Constants import BACKGROUND_COLOR, CHAT_BACKGROUND, FontSize, Screens
from functools import partial

FPS=60
username=""
lobby_name=""
voted_user=""
executed_user=""
WRAP_LINE_WIDTH=25
MAX_MESSAGES_DISPLAYED=10
CONTAINER_FACTOR=14 #this value is chosen by testing with different font sizes which value * wrap line withd fits all texts
CUSTOM_EVENT=0

class GameStateManager:
    """The game state manager internally stores which scene is displayed"""
    _current_state:Screens

    def __init__(self, start_screen:Screens) -> None:
        self._current_state=start_screen

    @property
    def current_state(self)->Screens:
        """Returns the screen the app game is on"""
        return self._current_state
    
    @current_state.setter
    def current_state(self, screen:Screens)->None:
        """Sets the current game state as the parameter given"""
        self._current_state=screen

    def change_screen(self, target_screen:Screens)->None:
        """A function to change the application screen to the given one"""
        self.current_state=target_screen

class AbstractScreen(ABC):
    """A screen abstraction, handling the base work of any screen implementation"""

    _display:pygame.Surface
    _game_state_manager:GameStateManager

    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        self._display=display
        self._game_state_manager=game_state_manager
    
    @abstractmethod
    def run(self, event:pygame.event.Event | None)->None:
        """This is where your screen is displayed"""
        raise NotImplementedError("Please implement this method")

class App:
    """The main window for the Wiredwolf game"""

    def __init__(self)-> None:
        pygame.init() #initializes pygame modules
        self._size=(640, 400) #default starting values
        self._icon = pygame.image.load('resources/icon.png') #load image from file
        pygame.display.set_icon(self._icon) #set image as window icon
        self._display_screen = pygame.display.set_mode(self._size, pygame.RESIZABLE) #the window is resizable
        pygame.display.set_caption("Wirewolf") #window title
        self._running = True
        self._game_state_manager=GameStateManager(Screens.HOME)
        self._start_screen=StartScreen(self._display_screen, self._game_state_manager)
        self._new_lobby_screen=NewLobbyScreen(self._display_screen, self._game_state_manager)
        self._search_lobby_screen=SearchLobbyScreen(self._display_screen, self._game_state_manager)
        self._waiting_lobby_screen=WaitingLobbyScreen(self._display_screen, self._game_state_manager)
        self._day_voting_screen=DayVotingScreen(self._display_screen, self._game_state_manager)
        self._day_execution_screen=DayExecutionScreen(self._display_screen, self._game_state_manager)
        self._night_villager_screen=NightVillagerScreen(self._display_screen, self._game_state_manager)
        self._night_role_screen=NightRoleScreen(self._display_screen, self._game_state_manager)
        self._villager_win_screen=VillagerWinScreen(self._display_screen, self._game_state_manager)
        self._villager_loss_screen=VillagerLossScreen(self._display_screen, self._game_state_manager)
        self._wolf_win_screen=WolfWinScreen(self._display_screen, self._game_state_manager)
        self._wolf_loss_screen=WolfLossScreen(self._display_screen, self._game_state_manager)
        self._dictionary={Screens.HOME: self._start_screen,
                          Screens.NEW_LOBBY:self._new_lobby_screen, 
                          Screens.SEARCH_LOBBY:self._search_lobby_screen, 
                          Screens.LOBBY_WAITING:self._waiting_lobby_screen,
                          Screens.DAY_VOTING:self._day_voting_screen,
                          Screens.DAY_EXECUTION: self._day_execution_screen,
                          Screens.NIGHT_VILLAGER: self._night_villager_screen,
                          Screens.NIGHT_ROLE: self._night_role_screen,
                          Screens.VILLAGER_WIN: self._villager_win_screen,
                          Screens.VILLAGER_LOSS: self._villager_loss_screen,
                          Screens.WOLF_WIN: self._wolf_win_screen,
                          Screens.WOLF_LOSS: self._wolf_loss_screen}
        self._clock = pygame.time.Clock()
        self._next_event=None
        
    @property
    def screen(self)->pygame.Surface:
        """Returns the surface of the application"""
        return self._display_screen

    @property
    def screen_size(self)->tuple[int, int]:
        """Returns the size of the window"""
        return self._size
    
    @property
    def app_running(self)->bool:
        """Returns true if the window is running"""
        return self._running

    def _on_event(self, event: pygame.event.Event)-> None:
        """Handles events generated by the user"""
        if event.type == pygame.QUIT:
            #closes the window
            self._running = False
            pygame.quit()
        else:
            if event.type == pygame.WINDOWRESIZED:
                #when the window is resized, the local variable value is changed
                self._size=pygame.display.get_surface().get_size()
            else:
                #event is saved and may be handled by the specific screen
                self._next_event=event

    def update_display(self)->None:
        """Called inside the event loop, handles framerate limiting, event handling and scene switching"""
        pygame.display.update() #necessary or the screen won't draw at all
        self._dictionary[self._game_state_manager.current_state].run(self._next_event)
        self._next_event=None
        for event in pygame.event.get():
            self._on_event(event) #handles generated events 
        self._clock.tick(FPS)

class StartScreen(AbstractScreen):
    """The start screen, the first screen showed at startup"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import CallbackButton, Text, TextField
        go_new_lobby=partial(self._game_state_manager.change_screen, Screens.NEW_LOBBY)
        new_lobby_button=CallbackButton(go_new_lobby, 'New Lobby', 250, 50) 
        go_search_lobby=partial(self._game_state_manager.change_screen, Screens.SEARCH_LOBBY)
        search_lobby_button=CallbackButton(go_search_lobby, 'Search for lobbies', 250, 50) 
        self._field=TextField(250, 50)
        username_enter=Text("Insert username:", font=FontSize.H2)
        list=[username_enter, self._field, new_lobby_button, search_lobby_button]
        self._v_container=VContainer(10, list, self._display.get_size())
        self._title_container=VContainer(0, [Text("Wiredwolf", (0, 10))], self._display.get_size(), (50, 15))
        
    def run(self,event:pygame.event.Event | None)->None:
        """The start screen, the first screen showed at startup"""
        self._display.fill(BACKGROUND_COLOR) #fills the background color for the application
        self._v_container.draw(self._display)
        self._title_container.draw(self._display)
        if event is not None:
            self._field.handle_event(event)
            tmp=self._field.text
            global username
            if len(tmp)>0 and str.isspace(tmp)==False: #the username field is filled by chars, not empty or only whitespaces
                username=self._field.text #save username in global variable
            else:
                username="username" #default username
                #TODO: communicate username to controller

class NewLobbyScreen(AbstractScreen):
    """A simple new lobby screen"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import CallbackButton, Text, TextField, EnabledButton
        self._title=VContainer(10,[Text("Create a new lobby")], self._display.get_size(),(50,20))
        lobby_name=Text("Insert the new lobby name", font=FontSize.H2)
        self._field=TextField(300, 50)
        create_lobby=partial(self._game_state_manager.change_screen, Screens.LOBBY_WAITING)
        self._create_lobby_button=EnabledButton(create_lobby, 'Create the new lobby!', 300, 50,font=FontSize.H2)
        go_home=partial(self._game_state_manager.change_screen, Screens.HOME)
        go_home_button=CallbackButton(go_home, 'Go back to start screen', 300, 50,font=FontSize.H2)
        self._button_container=VContainer(10, [lobby_name, self._field, self._create_lobby_button], self._display.get_size())
        self._button_back=VContainer(10, [go_home_button], self._display.get_size(), (50, 80))
    
    def run(self,event:pygame.event.Event | None)->None:
        """The new lobby screen, to create a new lobby"""
        self._display.fill(BACKGROUND_COLOR)
        self._title.draw(self._display)
        self._button_container.draw(self._display)
        self._button_back.draw(self._display)
        if event is not None:
            self._field.handle_event(event)
            tmp=self._field.text
            global lobby_name
            if len(tmp)>0 and str.isspace(tmp)==False: #the lobby name field is filled by chars, not empty or only whitespaces
                lobby_name=self._field.text #save new lobby name in global variable
                self._create_lobby_button.is_enabled=True
                #TODO: communicate lobby name to controller
            else:
                self._create_lobby_button.is_enabled=False
                lobby_name=""

class SearchLobbyScreen(AbstractScreen):
    """A simple search lobby screen"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import CallbackButton, Text, SelectorGroup, EnabledButton
        self._title=VContainer(0, [Text("Search for an existing lobby")], self._display.get_size(), (50, 10))
        self._selector=SelectorGroup([]) #This handles how the selectors BEHAVE as a group
        self._lobby_group=VContainer(20, [], self._display.get_size()) #This handles how the selectors are DISPLAYED
        go_home=partial(self._game_state_manager.change_screen, Screens.HOME)
        join_lobby=partial(self._game_state_manager.change_screen, Screens.LOBBY_WAITING)
        self._join_button=EnabledButton(join_lobby, 'Join selected lobby', 300, 50,font=FontSize.H2)
        self._buttons=HContainer(10, [CallbackButton(go_home, 'Go back to start screen', 300, 50,font=FontSize.H2), self._join_button], self._display.get_size(), (50, 80))
    
    def run(self,event:pygame.event.Event | None)->None:
        """The search lobby screen, to search for existing lobbies"""
        self._display.fill(BACKGROUND_COLOR)
        self._title.draw(self._display)
        self._lobby_group.draw(self._display)
        self._buttons.draw(self._display)
        global lobby_name
        tmp=self._selector.selected_text()
        if len(tmp)>0:
            self._join_button._is_enabled=True
            if lobby_name!=tmp:
                lobby_name=tmp
                #TODO: communicate which lobby the player joined to the controller
        else:
            self._join_button._is_enabled=False
        if event is not None:
            global CUSTOM_EVENT
            #Recived a custom event
            if event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, DiscoveredLobbyType):
                    #This screen only interacts with Discovered Lobby Events
                    button=SelectorButton(e.discovered_lobby, 100, 20)
                    self._selector.add_selector_button(button)
                    self._lobby_group.add_element(button)

class WaitingLobbyScreen(AbstractScreen):
    """The waiting room after joining a lobby"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import Text
        global lobby_name
        self._local_lobby=lobby_name
        self._title=Text("Waiting for other players to join "+self._local_lobby+" lobby")
        self._title_container=VContainer(0, [self._title], self._display.get_size(), (50,20))
        self._waiting=VContainer(0,[Text("1 player connected...", font=FontSize.H2)], self._display.get_size()) #TODO: how many connected users are waiting?
        
    def run(self,event:pygame.event.Event | None)->None:
        """A simple waiting screen"""
        global lobby_name
        if lobby_name!=self._local_lobby:
            #Since this screen is started before the lobby is chosen, this updates the display
            self._local_lobby=lobby_name
            self._title.text="Waiting for other players to join "+self._local_lobby+" lobby"
            self._title_container.update_on_next_draw() #Once this component is drawn the size of the text box has yet to change, so a manual update after draw is needed
        self._display.fill(BACKGROUND_COLOR) #fills the background color for the application
        self._title_container.draw(self._display)
        self._waiting.draw(self._display)
        if event is not None:
            global CUSTOM_EVENT
            #Recived a custom event
            if event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #This screen only interacts with ChangeScreen Events
                    #Should go to Day Voting Screen
                    self._game_state_manager.change_screen(e.next_screen)

class DayVotingScreen(AbstractScreen):
    """The screens where users chat and choose which players to nominate for an execution"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import MultipleTexts,LimitedList, MemoryTextField,Text,SelectorButton, SelectorGroup,EnabledButton
        self._title=VContainer(0, [Text("Day")], self._display.get_size(), (50, 5))
        self._my_limited_list=LimitedList(MAX_MESSAGES_DISPLAYED) #This is where the messages are stored, up to MAX_MESSAGES DISPLAYED
        self._multiple_texts=MultipleTexts(self._my_limited_list, 5, self._display.get_size(), (70, 45), CONTAINER_FACTOR*WRAP_LINE_WIDTH, CHAT_BACKGROUND) #This is where the messages are displayed vertically
        self._text_box=MemoryTextField(300, 50) #This is where the new messages are entered
        self._container_text=VContainer(0, [self._text_box], self._display.get_size(), (70,90))
        self._last_message=""
        self._selector=SelectorGroup([]) #This handles how the selectors BEHAVE as a group
        self._selector.set_enabled(False)
        change_player_voted=partial(self._set_voted_player)
        self._vote_player=EnabledButton(change_player_voted, 'Vote to execute player', 250, 50,font=FontSize.H2, enabled=False) #Necessary so users can't vote instantly
        self._vote_player_group=VContainer(0, [self._vote_player], self._display.get_size(), (20, 90))
        self._players=VContainer(20, [], self._display.get_size(), (20, 50)) #This handles how the selectors are DISPLAYED
        self._voted_text=Text("You haven't voted", font=FontSize.H3)
        self._voted_container=HContainer(0, [self._voted_text], self._display.get_size(), (20, 80))

    def run(self,event:pygame.event.Event | None)->None:
        """A day waiting and voting screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._multiple_texts.draw(self._display)
        self._container_text.draw(self._display)
        self._title.draw(self._display)
        self._players.draw(self._display)
        self._vote_player_group.draw(self._display)
        self._voted_container.draw(self._display)
        
        global CUSTOM_EVENT
        if event is not None:
            if event.type!=CUSTOM_EVENT:
                #pygame event, text box handles it
                self._text_box.handle_event(event) #Textbox handles key input
                tmp=self._text_box.last_input #get last message sent (if it's not already handled)
                if len(tmp)>0 and str.isspace(tmp)==False:
                    #if the message is not the last message sent and it's not empty, then send the new message
                    self._text_box.reset_last_input() #clear internal memory
                    global username
                    message=textwrap.wrap(username+":"+tmp, width=WRAP_LINE_WIDTH) #username: message
                    #too long messages will be split on multiple lines
                    for elem in message:
                        self._my_limited_list.add_element(elem) #adds message to messages sent
                    self._multiple_texts.on_list_change() #displays the new message(s)
            if event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, UsersType):
                    #Add new username
                    button=SelectorButton(e.username, 100, 20)
                    self._selector.add_selector_button(button)
                    self._players.add_element(button)
                if isinstance(e, TimeOutType):
                    #Starts voting
                    self._selector.set_enabled(True)
                    self._vote_player.is_enabled=True
                if isinstance(e, ChangeScreenType):
                    #End of voting, changing screen to DayExecutionScreen
                    self._game_state_manager.change_screen(e.next_screen)
            

    def _set_voted_player(self)->None:
        """Function called when the user chooses who to nominate for execution"""
        get_voted_player=self._selector.selected_text() #gets the chosen player
        global voted_user
        self._vote_player_group.update_on_next_draw() #This is necessary to update the container size on the next draw
        if len(get_voted_player)>0:
            #can only vote a player if one is selected
            voted_user=get_voted_player
            self._voted_text.text="You voted for "+voted_user
        else:
            voted_user="" #deselects player voted to be executed
            self._voted_text.text="You haven't voted"

class DayExecutionScreen(AbstractScreen):
    """The screen where users chat and choose if the player nominated for execution should be spared or not"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import MultipleTexts,LimitedList, MemoryTextField,Text,EnabledButton, CallbackButton
        self._title=VContainer(0, [Text("Day: execution")], self._display.get_size(), (50, 5))
        self._my_limited_list=LimitedList(MAX_MESSAGES_DISPLAYED) #This is where the messages are stored, up to MAX_MESSAGES DISPLAYED
        self._multiple_texts=MultipleTexts(self._my_limited_list, 5, self._display.get_size(), (70, 45), CONTAINER_FACTOR*WRAP_LINE_WIDTH, CHAT_BACKGROUND) #This is where the messages are displayed vertically
        self._text_box=MemoryTextField(300, 50) #This is where the new messages are entered
        self._container_text=VContainer(0, [self._text_box], self._display.get_size(), (70,90))
        self._last_message=""
        self._vote_to_execute=None #Saved outcome of user voting, if None->not voted, True->executed, False->Spared
        global executed_user
        executed_user="Mario" #TODO: get username from controller
        executed=partial(self._spare_or_execute, True)
        spared=partial(self._spare_or_execute, False)
        self._execute_button=EnabledButton(executed, "Vote to execute "+executed_user, 300, 50, enabled=True)
        self._spare_button=EnabledButton(spared, "Vote to spare "+executed_user, 300, 50, enabled=True)
        self._button_container=VContainer(20, [self._execute_button, self._spare_button], self._display.get_size(), (20, 50))

    def run(self,event:pygame.event.Event | None)->None:
        """A day execution screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._multiple_texts.draw(self._display)
        self._container_text.draw(self._display)
        self._title.draw(self._display)
        self._button_container.draw(self._display)
        global CUSTOM_EVENT
        if event is not None:
            if event.type!=CUSTOM_EVENT:
                self._text_box.handle_event(event) #Textbox handles key input
                tmp=self._text_box.last_input #get last message sent (if it's not already handled)
                if len(tmp)>0 and str.isspace(tmp)==False:
                    #if the message is not the last message sent and it's not empty, then send the new message
                    self._text_box.reset_last_input() #clear internal memory
                    global username
                    message=textwrap.wrap(username+":"+tmp, width=WRAP_LINE_WIDTH) #username: message
                    #too long messages will be split on multiple lines
                    for elem in message:
                        self._my_limited_list.add_element(elem) #adds message to messages sent
                    self._multiple_texts.on_list_change() #displays the new message(s)
            if event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of day, changing screen to Night villager or night role, according to user role
                    self._game_state_manager.change_screen(e.next_screen)
    
    def _spare_or_execute(self, outcome:bool)->None:
        """The function called when the buttons are pressed, to save the outcome of the voting"""
        #Can only vote once, disabling buttons
        self._execute_button.is_enabled=False
        self._spare_button.is_enabled=False
        self._vote_to_execute=outcome

class NightVillagerScreen(AbstractScreen):
    """The screen where villager role users wait for the night to end"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import Text
        self._title=VContainer(0, [Text("Night")], self._display.get_size(), (50, 5))
        self._villager=VContainer(0, [Text("Wait for the night to end...")], self._display.get_size())

    def run(self,event:pygame.event.Event | None)->None:
        """A night villager screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._title.draw(self._display)
        self._villager.draw(self._display)
        if event is not None and event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of night, changing screen to day voting
                    self._game_state_manager.change_screen(e.next_screen)

class NightRoleScreen(AbstractScreen):
    """The screen where non villager role users act during the night"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import Text, SelectorGroup, EnabledButton
        self._title=VContainer(0, [Text("Night")], self._display.get_size(), (50, 5))
        self._role=VContainer(0, [Text("Use your power, special role")], self._display.get_size()) #TODO: get role from controller to customize text
        self._selector_group=SelectorGroup([]) #Added dynamically via events
        self._users=VContainer(10, [], self._display.get_size()) #TODO: position
        act_on=partial(self._act_on_player)
        self._execute=EnabledButton(act_on, "Act on this player", 300, 50, enabled=True) #TODO: get role from controller to customize text
        self._execute_container=VContainer(0, [self._execute], self._display.get_size()) #TODO: position

    def run(self,event:pygame.event.Event | None)->None:
        """A night non villager role screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._title.draw(self._display)
        self._role.draw(self._display)
        self._users.draw(self._display)
        self._execute_container.draw(self._display)
        if event is not None and event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of night, changing screen to day voting
                    self._game_state_manager.change_screen(e.next_screen)
                if isinstance(e, UsersType):
                    #Add username to users you can act on (ex: werewolfs can only kill non werewolves ecc)
                    button=SelectorButton(e.username, 100, 20)
                    self._selector_group.add_selector_button(button)
                    self._users.add_element(button)
    
    def _act_on_player(self)->None:
        """The function called when the button is pressed, to save who you acted on"""
        #Can only act once, disabling buttons
        self._execute.is_enabled=False
        voted_player=self._selector_group.selected_text() #gets the chosen player
        if voted_player!=None:
            #TODO: communicate to controller that user acted on given player
            pass
        #TODO: if anything selected->enable button->vote->disable all
        #if nothing selected->all enabled


class VillagerWinScreen(AbstractScreen):
    """The winning screen for villager users"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import Text
        self._title=VContainer(0, [Text("Villagers have won!")], self._display.get_size())

    def run(self, event:pygame.event.Event | None)->None:
        """A winning screen for villager users"""
        self._display.fill(BACKGROUND_COLOR)
        self._title.draw(self._display)
        if event is not None and event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of winning screen, go to home?
                    self._game_state_manager.change_screen(e.next_screen)

class VillagerLossScreen(AbstractScreen):
    """The losing screen for villager users"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import Text
        self._title=VContainer(0, [Text("Villagers have lost")], self._display.get_size())

    def run(self, event:pygame.event.Event | None)->None:
        """A losing screen for villager users"""
        self._display.fill(BACKGROUND_COLOR)
        self._title.draw(self._display)
        if event is not None and event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of winning screen, go to home?
                    self._game_state_manager.change_screen(e.next_screen)

class WolfWinScreen(AbstractScreen):
    """The winning screen for werewolf users"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import Text
        self._title=VContainer(0, [Text("Werewolves have won!")], self._display.get_size())

    def run(self, event:pygame.event.Event | None)->None:
        """A winning screen for werewolf users"""
        self._display.fill(BACKGROUND_COLOR)
        self._title.draw(self._display)
        if event is not None and event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of winning screen, go to home?
                    self._game_state_manager.change_screen(e.next_screen)

class WolfLossScreen(AbstractScreen):
    """The losing screen for werewolf users"""
    def __init__(self, display: pygame.Surface, game_state_manager:GameStateManager) -> None:
        super().__init__(display, game_state_manager)
        from wiredwolf.view.Components import Text
        self._title=VContainer(0, [Text("Werewolves have lost")], self._display.get_size())

    def run(self, event:pygame.event.Event | None)->None:
        """A losing screen for werewolf users"""
        self._display.fill(BACKGROUND_COLOR)
        self._title.draw(self._display)
        if event is not None and event.type==CUSTOM_EVENT:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of winning screen, go to home?
                    self._game_state_manager.change_screen(e.next_screen)

if __name__ == "__main__":
    my_app=App()
    custom=CustomEventSender()
    CUSTOM_EVENT=custom.custom_event #Save value of custom events
    while my_app.app_running:
        custom.test()
        my_app.update_display()
