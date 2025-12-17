import textwrap
import pygame
import pygame_gui
from abc import ABC, abstractmethod
from wiredwolf.view.CustomEvents import ChangeScreenType, ChatMessageType, CustomEventSender, DiscoveredLobbyType, EventSender, GameRoleType, TimeOutType, UsersType, WaitingRoomType, create_custom_event_from_dict
from wiredwolf.view.Components import LimitedList, MultipleTexts, SelectorButton, VContainer, HContainer
from wiredwolf.view.Constants import FontSize, Screens
from functools import partial
from wiredwolf.view.ViewConstants import *
from pygame_gui.core.interfaces import IUIElementInterface

FPS=60
username=""
lobby_name=""
voted_user=""
WRAP_LINE_WIDTH=24
MAX_MESSAGES_DISPLAYED=12
CONTAINER_FACTOR=14 #this value is chosen by testing with different font sizes which value * wrap line withd fits all texts
custom_event=0 #custom event id, to be set by event sender

def message_sender_util(message:str, list: LimitedList, multiple_text_display:MultipleTexts)->None:
    """A message sender util that handles message splitting into multiple lines and updates the display given"""
    split_message=textwrap.wrap(message, width=WRAP_LINE_WIDTH)
    for elem in split_message:
        list.add_element(elem) #adds message to messages displayed
    multiple_text_display.on_list_change() #displays the new message(s)

class PanelHandler():
    """A class to handle all panel creations and hiding/showing"""

    def __init__(self, gui_manager:pygame_gui.UIManager)->None:
        self._gui_manager=gui_manager
        self._panel_dictionary:dict[Screens,list]={} #TODO: what type of element in list?
        #this dictionary stores all existing panels according to the screen they are shown on

    def create_panel(self, screen:Screens, relative_rect:pygame.Rect, anchors:dict[str, str | IUIElementInterface], starting_height:int=10,)->pygame_gui.elements.UIPanel:
        """Creates a hidden pygame_gui UIPanel with the given parameters. Saves a reference to the panel together with the screen it's shown on for future use"""
        panel=pygame_gui.elements.UIPanel(relative_rect=relative_rect, starting_height=starting_height, manager=self._gui_manager, anchors=anchors)
        panel.hide() #starts panel as hidden
        if screen in self._panel_dictionary:
            #already another panel of the same screen has been created
            self._panel_dictionary[screen].append(panel)
        else:
            #first panel of this screen
            self._panel_dictionary[screen]=[panel]
        return panel
    
    def create_scrolling_panel(self, screen:Screens, relative_rect:pygame.Rect, anchors:dict[str, str | IUIElementInterface], starting_height:int=10,)->pygame_gui.elements.UIScrollingContainer:
        """Creates a hidden pygame_gui UIScrollingContainer with the given parameters. Saves a reference to the panel together with the screen it's shown on for future use"""
        panel=pygame_gui.elements.UIScrollingContainer(relative_rect=relative_rect, starting_height=starting_height, manager=self._gui_manager, anchors=anchors, allow_scroll_x=False)
        panel.hide() #starts panel as hidden
        if screen in self._panel_dictionary:
            #already another panel of the same screen has been created
            self._panel_dictionary[screen].append(panel)
        else:
            #first panel of this screen
            self._panel_dictionary[screen]=[panel]
        return panel

    def show_screens(self, screen:Screens)->None:
        """Shows all panels of a given screen"""
        if screen in self._panel_dictionary:
            for element in self._panel_dictionary[screen]:
                element.show()
    
    def hide_screens(self, screen:Screens)->None:
        """Hides all panels of a given screen"""
        if screen in self._panel_dictionary:
            for element in self._panel_dictionary[screen]:
                element.hide()

class GameStateManager:
    """The game state manager internally stores which scene is displayed"""

    def __init__(self, start_screen:Screens, panel_handler:PanelHandler) -> None:
        self._current_state=start_screen
        self._panel_handler=panel_handler

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
        self._panel_handler.hide_screens(self._current_state) #hides old screen panels
        self._current_state=target_screen
        self._panel_handler.show_screens(target_screen) #shows new screen panels

class AbstractScreen(ABC):
    """A screen abstraction, handling the base work of any screen implementation"""

    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        self._display=display
        self._game_state_manager=game_state_manager
        self._gui_manager=gui_manager
        self._panel_handler=panel_handler
        self._screen_id=screen
    
    @property
    def screen(self)->Screens:
        """Returns the Screen enum of the displayed screen"""
        return self._screen_id
    
    @abstractmethod
    def reset_screen(self)->None:
        """This is where your screen is reset, it should look like the fist draw"""
        raise NotImplementedError("Please implement this method")

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
        self._gui_manager=pygame_gui.UIManager(self._size, theme_path='resources/theme.json')
        self._panel_handler=PanelHandler(self._gui_manager)
        self._game_state_manager=GameStateManager(Screens.HOME, self._panel_handler)
        self._start_screen=StartScreen(Screens.HOME, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._new_lobby_screen=NewLobbyScreen(Screens.NEW_LOBBY, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._search_lobby_screen=SearchLobbyScreen(Screens.SEARCH_LOBBY, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._waiting_lobby_screen=WaitingLobbyScreen(Screens.LOBBY_WAITING, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._day_voting_screen=DayVotingScreen(Screens.DAY_VOTING, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._day_execution_screen=DayExecutionScreen(Screens.DAY_EXECUTION, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._night_villager_screen=NightVillagerScreen(Screens.NIGHT_VILLAGER, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._night_role_screen=NightRoleScreen(Screens.NIGHT_ROLE, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._villager_win_screen=VillagerWinScreen(Screens.VILLAGER_WIN, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._villager_loss_screen=VillagerLossScreen(Screens.VILLAGER_LOSS, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._wolf_win_screen=WolfWinScreen(Screens.WOLF_WIN, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._wolf_loss_screen=WolfLossScreen(Screens.WOLF_LOSS, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._role_display_screen=RoleDisplayScreen(Screens.ROLE_DISPLAY, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._dictionary:dict[Screens, AbstractScreen]={self._start_screen.screen: self._start_screen,
                          self._new_lobby_screen.screen:self._new_lobby_screen, 
                          self._search_lobby_screen.screen:self._search_lobby_screen, 
                          self._waiting_lobby_screen.screen:self._waiting_lobby_screen,
                          self._day_voting_screen.screen:self._day_voting_screen,
                          self._day_execution_screen.screen: self._day_execution_screen,
                          self._night_villager_screen.screen: self._night_villager_screen,
                          self._night_role_screen.screen: self._night_role_screen,
                          self._villager_win_screen.screen: self._villager_win_screen,
                          self._villager_loss_screen.screen: self._villager_loss_screen,
                          self._wolf_win_screen.screen: self._wolf_win_screen,
                          self._wolf_loss_screen.screen: self._wolf_loss_screen,
                          self._role_display_screen.screen: self._role_display_screen}
        self._clock = pygame.time.Clock()
        self._next_event=None
        #Sets custom event sender
        self._event_sender=CustomEventSender()
        global custom_event
        custom_event=self._event_sender.custom_event

    @property
    def event_sender(self)->EventSender:
        """Returns the event sender object"""
        return self._event_sender
        
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
                #Update the manager with the new window size
                self._gui_manager.set_window_resolution((event.x, event.y))
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
            self._gui_manager.process_events(event) #processes pygame_gui events
        tick=self._clock.tick(FPS)
        self._gui_manager.update(tick/1000.0) #gui manager needs to know how much time has passed since the last update in milliseconds

class StartScreen(AbstractScreen):
    """The start screen, the first screen showed at startup"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager,gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import CallbackButton, Text, TextField, DrawableComponent
        go_new_lobby=partial(self._game_state_manager.change_screen, Screens.NEW_LOBBY)
        new_lobby_button=CallbackButton(go_new_lobby, 'New Lobby', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT) 
        go_search_lobby=partial(self._game_state_manager.change_screen, Screens.SEARCH_LOBBY)
        search_lobby_button=CallbackButton(go_search_lobby, 'Search for lobbies', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT) 
        self._field=TextField(LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT)
        username_enter=Text("Insert username:", font=FontSize.H2)
        list_buttons:list[DrawableComponent]=[username_enter, self._field, new_lobby_button, search_lobby_button]
        self._v_container=VContainer(MEDIUM_ELEMENT_DIV, list_buttons, self._display.get_size())
        self._title_container=VContainer(SINGLE_ELEMENT_DIV, [Text("Wiredwolf")], self._display.get_size(), (50, 15))
        
    def run(self,event:pygame.event.Event | None)->None:
        """The start screen, the first screen showed at startup"""
        self._display.fill(BACKGROUND_COLOR) #fills the background color for the application
        self._gui_manager.draw_ui(self._display)
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
    
    def reset_screen(self) -> None:
        #TODO: implement
        pass

class NewLobbyScreen(AbstractScreen):
    """A simple new lobby screen"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import CallbackButton, Text, TextField, EnabledButton
        self._title=VContainer(SINGLE_ELEMENT_DIV,[Text("Create a new lobby")], self._display.get_size(), (50,20))
        lobby_name=Text("Insert the new lobby name", font=FontSize.H2)
        self._field=TextField(LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT)
        create_lobby=partial(self._game_state_manager.change_screen, Screens.LOBBY_WAITING)
        self._create_lobby_button=EnabledButton(create_lobby, 'Create the new lobby!', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT,font=FontSize.H2)
        go_home=partial(self._game_state_manager.change_screen, Screens.HOME)
        go_home_button=CallbackButton(go_home, 'Go back to start screen', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT ,font=FontSize.H2)
        self._button_container=VContainer(MEDIUM_ELEMENT_DIV, [lobby_name, self._field, self._create_lobby_button], self._display.get_size())
        self._button_back=VContainer(SINGLE_ELEMENT_DIV, [go_home_button], self._display.get_size(), (50, 80))
    
    def run(self,event:pygame.event.Event | None)->None:
        """The new lobby screen, to create a new lobby"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
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
            
    def reset_screen(self) -> None:
        #TODO: implement
        pass

class SearchLobbyScreen(AbstractScreen):
    """A simple search lobby screen"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import CallbackButton, Text, SelectorGroup, EnabledButton
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Search for an existing lobby")], self._display.get_size(), (50, 10))
        self._selector=SelectorGroup([]) #This handles how the selectors BEHAVE as a group
        self._lobby_group=VContainer(MEDIUM_ELEMENT_DIV, [], self._display.get_size(), (50, 45)) #This handles how the selectors are DISPLAYED
        go_home=partial(self._game_state_manager.change_screen, Screens.HOME)
        join_lobby=partial(self._game_state_manager.change_screen, Screens.LOBBY_WAITING)
        self._join_button=EnabledButton(join_lobby, 'Join selected lobby', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT,font=FontSize.H2)
        self._buttons=HContainer(MEDIUM_ELEMENT_DIV, [CallbackButton(go_home, 'Go back to start screen', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, font=FontSize.H2), self._join_button], self._display.get_size(), (50, 85))
    
    def run(self,event:pygame.event.Event | None)->None:
        """The search lobby screen, to search for existing lobbies"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        self._lobby_group.draw(self._display)
        self._buttons.draw(self._display)
        global lobby_name
        tmp=self._selector.selected_text()
        if len(tmp)>0:
            self._join_button.is_enabled=True
            if lobby_name!=tmp:
                lobby_name=tmp
                #TODO: communicate which lobby the player joined to the controller
        else:
            self._join_button.is_enabled=False
        if event is not None:
            #Recived a custom event
            if event.type==custom_event:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, DiscoveredLobbyType):
                    #This screen only interacts with Discovered Lobby Events
                    button=SelectorButton(e.discovered_lobby, SMALL_BTN_WIDTH, SMALL_BTN_HEIGHT)
                    self._selector.add_selector_button(button)
                    self._lobby_group.add_element(button)
        
    def reset_screen(self) -> None:
        #TODO: implement
        pass

class WaitingLobbyScreen(AbstractScreen):
    """The waiting room after joining a lobby"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import Text
        global lobby_name
        self._local_lobby=lobby_name
        self._title=Text("Waiting for other players to join "+self._local_lobby+" lobby")
        self._title_container=VContainer(SINGLE_ELEMENT_DIV, [self._title], self._display.get_size(), (50,20))
        self._text_number=Text("1 player connected...", font=FontSize.H2) #Updated count via custom events
        self._waiting=VContainer(SINGLE_ELEMENT_DIV,[self._text_number], self._display.get_size())
        
    def run(self,event:pygame.event.Event | None)->None:
        """A simple waiting screen"""
        global lobby_name
        if lobby_name!=self._local_lobby:
            #Since this screen is started before the lobby is chosen, this updates the display
            self._local_lobby=lobby_name
            self._title.text="Waiting for other players to join "+self._local_lobby+" lobby"
            self._title_container.update_on_next_draw() #Once this component is drawn the size of the text box has yet to change, so a manual update after draw is needed
        self._display.fill(BACKGROUND_COLOR) #fills the background color for the application
        self._gui_manager.draw_ui(self._display)
        self._title_container.draw(self._display)
        self._waiting.draw(self._display)
        if event is not None:
            #Recived a custom event
            if event.type==custom_event:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #This screen only interacts ChangeScreen Events
                    #Should go to Day Voting Screen
                    self._game_state_manager.change_screen(e.next_screen)
                if isinstance(e, WaitingRoomType):
                    #Updates the number of players in the waiting room
                    self._text_number.text=str(e.number) +" player connected..."
                    self._waiting.update_on_next_draw()
    
    def reset_screen(self) -> None:
        #TODO: implement
        pass


class DayVotingScreen(AbstractScreen):
    """The screens where users chat and choose which players to nominate for an execution"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import MultipleTexts,LimitedList, MemoryTextField,Text, SelectorGroup,EnabledButton
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Day")], self._display.get_size(), (50, 5))
        self._my_limited_list=LimitedList(MAX_MESSAGES_DISPLAYED) #This is where the messages are stored, up to MAX_MESSAGES DISPLAYED
        self._multiple_texts=MultipleTexts(self._my_limited_list, SMALL_ELEMENT_DIV, self._display.get_size(), (70, 45), CONTAINER_FACTOR*WRAP_LINE_WIDTH, CHAT_BACKGROUND, font=FontSize.H3) #This is where the messages are displayed vertically
        self._text_box=MemoryTextField(LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, font=FontSize.H3) #This is where the new messages are entered
        self._container_text=VContainer(SINGLE_ELEMENT_DIV, [self._text_box], self._display.get_size(), (70,90))
        self._last_message=""
        self._selector=SelectorGroup([]) #This handles how the selectors BEHAVE as a group
        change_player_voted=partial(self._set_voted_player)
        self._vote_player=EnabledButton(change_player_voted, 'Vote to execute player', MEDIUM_BTN_WIDTH, LARGE_BTN_HEIGHT,font=FontSize.H2, enabled=False) #Necessary so users can't vote instantly
        self._vote_player_group=VContainer(SINGLE_ELEMENT_DIV, [self._vote_player], self._display.get_size(), (20, 90))
        self._players=VContainer(MEDIUM_ELEMENT_DIV, [], self._display.get_size(), (20, 40)) #This handles how the selectors are DISPLAYED
        self._voted_text=Text("You haven't voted", font=FontSize.H3)
        self._voted_container=HContainer(SINGLE_ELEMENT_DIV, [self._voted_text], self._display.get_size(), (20, 80))

    def run(self,event:pygame.event.Event | None)->None:
        """A day waiting and voting screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._multiple_texts.draw(self._display)
        self._container_text.draw(self._display)
        self._title.draw(self._display)
        self._players.draw(self._display)
        self._vote_player_group.draw(self._display)
        self._voted_container.draw(self._display)

        if event is not None:
            if event.type!=custom_event:
                #pygame event, text box handles it
                self._text_box.handle_event(event) #Textbox handles key input
                tmp=self._text_box.last_input #get last message sent (if it's not already handled)
                if len(tmp)>0 and str.isspace(tmp)==False:
                    #if the message is not the last message sent and it's not empty, then send the new message
                    self._text_box.reset_last_input() #clear internal memory
                    global username
                    message_sender_util(username+":"+tmp, self._my_limited_list, self._multiple_texts) #TODO: communicate with controller the message
            if event.type==custom_event:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, UsersType):
                    #Add new username
                    button=SelectorButton(e.username, SMALL_BTN_WIDTH, SMALL_BTN_HEIGHT)
                    self._selector.add_selector_button(button)
                    self._selector.set_enabled(False)
                    self._players.add_element(button)
                if isinstance(e, TimeOutType):
                    #Starts voting
                    self._selector.set_enabled(True)
                    self._vote_player.is_enabled=True
                if isinstance(e, ChangeScreenType):
                    #End of voting, changing screen to DayExecutionScreen
                    self._game_state_manager.change_screen(e.next_screen)
                if isinstance(e, ChatMessageType):
                    #Messages recived from other users
                    message_sender_util(e.message, self._my_limited_list, self._multiple_texts)

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

    def reset_screen(self) -> None:
        #TODO: implement
        pass

class DayExecutionScreen(AbstractScreen):
    """The screen where users chat and choose if the player nominated for execution should be spared or not"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import MultipleTexts,LimitedList, MemoryTextField,Text,EnabledButton
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Day: execution")], self._display.get_size(), (50, 5))
        self._my_limited_list=LimitedList(MAX_MESSAGES_DISPLAYED) #This is where the messages are stored, up to MAX_MESSAGES DISPLAYED
        self._multiple_texts=MultipleTexts(self._my_limited_list, SMALL_ELEMENT_DIV, self._display.get_size(), (70, 45), CONTAINER_FACTOR*WRAP_LINE_WIDTH, CHAT_BACKGROUND, font=FontSize.H3) #This is where the messages are displayed vertically
        self._text_box=MemoryTextField(LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, font=FontSize.H3) #This is where the new messages are entered
        self._container_text=VContainer(SINGLE_ELEMENT_DIV, [self._text_box], self._display.get_size(), (70,90))
        self._last_message=""
        self._vote_to_execute=None #Saved outcome of user voting, if None->not voted, True->executed, False->Spared
        self._executed_user="" #Gets username via custom event
        executed=partial(self._spare_or_execute, True)
        spared=partial(self._spare_or_execute, False)
        self._execute_button=EnabledButton(executed, "Vote to execute "+self._executed_user, MEDIUM_BTN_WIDTH, LARGE_BTN_HEIGHT, enabled=True)
        self._spare_button=EnabledButton(spared, "Vote to spare "+self._executed_user, MEDIUM_BTN_WIDTH, LARGE_BTN_HEIGHT, enabled=True)
        self._button_container=VContainer(LARGE_ELEMENT_DIV, [self._execute_button, self._spare_button], self._display.get_size(), (20, 50))

    def run(self,event:pygame.event.Event | None)->None:
        """A day execution screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._multiple_texts.draw(self._display)
        self._container_text.draw(self._display)
        self._title.draw(self._display)
        self._button_container.draw(self._display)

        if event is not None:
            if event.type!=custom_event:
                self._text_box.handle_event(event) #Textbox handles key input
                tmp=self._text_box.last_input #get last message sent (if it's not already handled)
                if len(tmp)>0 and str.isspace(tmp)==False:
                    #if the message is not the last message sent and it's not empty, then send the new message
                    self._text_box.reset_last_input() #clear internal memory
                    global username
                    message_sender_util(username+":"+tmp, self._my_limited_list, self._multiple_texts) #TODO: communicate with controller the message
            if event.type==custom_event:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of day, changing screen to Night villager or night role, according to user role
                    self._game_state_manager.change_screen(e.next_screen)
                if isinstance(e, ChatMessageType):
                    #Messages recived from other users
                    message_sender_util(e.message, self._my_limited_list, self._multiple_texts)
                if isinstance(e, UsersType):
                    #Username of player to execute
                    self._executed_user=e.username
                    self._execute_button.text="Vote to execute "+self._executed_user
                    self._spare_button.text="Vote to spare "+self._executed_user
                    #Updating the button text requires an update on the container
                    self._button_container.update_on_next_draw()
    
    def _spare_or_execute(self, outcome:bool)->None:
        """The function called when the buttons are pressed, to save the outcome of the voting"""
        #Can only vote once, disabling buttons
        self._execute_button.is_enabled=False
        self._spare_button.is_enabled=False
        self._vote_to_execute=outcome
        
    def reset_screen(self) -> None:
        #TODO: implement
        pass

class NightVillagerScreen(AbstractScreen):
    """The screen where villager role users wait for the night to end"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import Text
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Night")], self._display.get_size(), (50, 5))
        self._villager=VContainer(SINGLE_ELEMENT_DIV, [Text("Wait for the night to end...")], self._display.get_size())

    def run(self,event:pygame.event.Event | None)->None:
        """A night villager screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        self._villager.draw(self._display)
        if event is not None and event.type==custom_event:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of night, changing screen to day voting
                    self._game_state_manager.change_screen(e.next_screen)
    
    def reset_screen(self) -> None:
        #TODO: implement
        pass

class NightRoleScreen(AbstractScreen):
    """The screen where non villager role users act during the night"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import Text, SelectorGroup, EnabledButton
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Night")], self._display.get_size(), (50, 5))
        self._role_name=""
        self._role_text=Text("Use your power, "+self._role_name)
        self._role_container=VContainer(SINGLE_ELEMENT_DIV, [self._role_text], self._display.get_size(),(50, 10)) 
        self._selector_group=SelectorGroup([]) #Added dynamically via events
        self._users=VContainer(MEDIUM_ELEMENT_DIV, [], self._display.get_size()) #Added dynamically via events
        act_on=partial(self._act_on_player)
        self._execute=EnabledButton(act_on, "Act on this player", LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, enabled=True) #TODO: customize this further? ex werewolves kill this player, ... 
        self._execute_container=VContainer(SINGLE_ELEMENT_DIV, [self._execute], self._display.get_size(), (50, 90))

    def run(self,event:pygame.event.Event | None)->None:
        """A night non villager role screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        self._role_container.draw(self._display)
        self._users.draw(self._display)
        self._execute_container.draw(self._display)
        if event is not None and event.type==custom_event:
                #parse the custom event into an object
                e=create_custom_event_from_dict(event.dict)
                if isinstance(e, ChangeScreenType):
                    #End of night, changing screen to day voting
                    self._game_state_manager.change_screen(e.next_screen)
                if isinstance(e, UsersType):
                    #Add username to users you can act on (ex: werewolfs can only kill non werewolves ecc)
                    button=SelectorButton(e.username, SMALL_BTN_WIDTH, SMALL_BTN_HEIGHT)
                    self._selector_group.add_selector_button(button)
                    self._users.add_element(button)
                if isinstance(e, GameRoleType):
                    #Personalizes screen with player role
                    self._role_name=e.role
                    self._role_text.text="Use your power, "+self._role_name
                    self._role_container.update_on_next_draw()
    
    def _act_on_player(self)->None:
        """The function called when the button is pressed, to save who you acted on"""
        voted_player=self._selector_group.selected_text() #gets the chosen player
        if voted_player!="":
            #Can only act once, disabling buttons
            self._selector_group.set_enabled(False) #disable selectors
            self._execute.is_enabled=False #disable button
            #TODO: communicate to controller that user acted on given player

    def reset_screen(self) -> None:
        #TODO: implement
        pass


class VillagerWinScreen(AbstractScreen):
    """The winning screen for villager users"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import Text
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Villagers have won!")], self._display.get_size())

    def run(self, event:pygame.event.Event | None)->None:
        """A winning screen for villager users"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        if event is not None and event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #End of winning screen, go to home?
                self._game_state_manager.change_screen(e.next_screen)
 
    def reset_screen(self) -> None:
        #TODO: implement
        pass

class VillagerLossScreen(AbstractScreen):
    """The losing screen for villager users"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager,gui_manager, panel_handler)
        from wiredwolf.view.Components import Text
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Villagers have lost")], self._display.get_size())

    def run(self, event:pygame.event.Event | None)->None:
        """A losing screen for villager users"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        if event is not None and event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #End of winning screen, go to home?
                self._game_state_manager.change_screen(e.next_screen)

    def reset_screen(self) -> None:
        #TODO: implement
        pass

class WolfWinScreen(AbstractScreen):
    """The winning screen for werewolf users"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import Text
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Werewolves have won!")], self._display.get_size())

    def run(self, event:pygame.event.Event | None)->None:
        """A winning screen for werewolf users"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        if event is not None and event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #End of winning screen, go to home?
                self._game_state_manager.change_screen(e.next_screen)

    def reset_screen(self) -> None:
        #TODO: implement
        pass

class WolfLossScreen(AbstractScreen):
    """The losing screen for werewolf users"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import Text
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Werewolves have lost")], self._display.get_size())

    def run(self, event:pygame.event.Event | None)->None:
        """A losing screen for werewolf users"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        if event is not None and event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #End of winning screen, go to home?
                self._game_state_manager.change_screen(e.next_screen)
    
    def reset_screen(self) -> None:
        #TODO: implement
        pass

class RoleDisplayScreen(AbstractScreen):
    """The screen displaying which role you were assigned to and explaining its powers"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        from wiredwolf.view.Components import Text
        self._title=Text("Role") #Properly set via custom event
        self._title_container=VContainer(SINGLE_ELEMENT_DIV, [self._title], self._display.get_size(), (50, 20))
        self._description=Text("Description", font=FontSize.H2) #Properly set via custom event
        self._description_container=VContainer(SINGLE_ELEMENT_DIV, [self._description], self._display.get_size())
    
    def run(self, event:pygame.event.Event | None)->None:
        """A role screen for users"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title_container.draw(self._display)
        self._description_container.draw(self._display)
        if event is not None and event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #Go to next screen
                self._game_state_manager.change_screen(e.next_screen)
            if isinstance(e, GameRoleType):
                #Update role and description
                self._title.text=e.role
                self._title_container.update_on_next_draw()
                self._description.text=e.role_description
                self._description_container.update_on_next_draw()
        
    def reset_screen(self) -> None:
        #TODO: implement
        pass

if __name__ == "__main__":
    my_app=App()
    while my_app.app_running:
        my_app.update_display()
