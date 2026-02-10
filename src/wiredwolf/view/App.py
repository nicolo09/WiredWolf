import pygame
import pygame_gui
import tkinter
from abc import ABC, abstractmethod
from wiredwolf.controller.commons import Peer
from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser
from wiredwolf.view.custom_events import ChangeScreenType, ChatMessageType, CustomEventSender, LobbyType, EventSender, GameRoleType, TimeOutType, UsersType, create_custom_event_from_dict
from wiredwolf.view.components import CallbackButton, MemoryTextField, VContainer, HContainer, EnabledButton, Text, TextField, DrawableComponent
from wiredwolf.view.constants import FontSize, Screens
from functools import partial
from wiredwolf.view.view_constants import AUTO_SIZING, HORIZONTAL_SPACE_FOR_SCROLLBAR, MEDIUM_BTN_HEIGHT, MEDIUM_PANEL, SMALL_PANEL, PANEL_Y, SINGLE_ELEMENT_DIV, SMALL_BTN_WIDTH, MEDIUM_ELEMENT_DIV, LARGE_ELEMENT_DIV, LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, MEDIUM_BTN_WIDTH, BACKGROUND_COLOR, SMALL_ELEMENT_DIV, WIDE_PANEL
from pygame_gui.core.interfaces import IUIElementInterface
from pygame_gui.core import UIElement
from tkinter import messagebox

FPS=60
username=""
lobby_name=""
voted_user=""
custom_event=0 #custom event id, to be set by event sender
class PanelHandler():
    """A class to handle all panel creations and hiding/showing"""

    def __init__(self, gui_manager:pygame_gui.UIManager)->None:
        self._gui_manager=gui_manager
        self._panel_dictionary:dict[Screens,list[tuple[UIElement, bool]]]={} #Can store both UiPanels and UiScrollingContainers
        #this dictionary stores all existing panels connected to the screen they are shown on
        #list of (panels, always_on)->if always_on==true, panel is always displayed when screen is shown. Otherwise it stays hidden

    def create_panel(self, screen:Screens, relative_rect:pygame.Rect, anchors:dict[str, str | IUIElementInterface], starting_height:int=10,always_on:bool=True)->pygame_gui.elements.UIPanel:
        """Creates a hidden pygame_gui UIPanel with the given parameters. Saves a reference to the panel together with the screen it's shown on for future use"""
        panel=pygame_gui.elements.UIPanel(relative_rect=relative_rect, starting_height=starting_height, manager=self._gui_manager, anchors=anchors)
        panel.hide() #starts panel as hidden
        if screen in self._panel_dictionary:
            #already another panel of the same screen has been created
            self._panel_dictionary[screen].append((panel,always_on))
        else:
            #first panel of this screen
            self._panel_dictionary[screen]=[(panel, always_on)]
        return panel
    
    def create_scrolling_panel(self, screen:Screens, relative_rect:pygame.Rect, anchors:dict[str, str | IUIElementInterface], starting_height:int=10, allow_scroll_x:bool=False, always_on:bool=True)->pygame_gui.elements.UIScrollingContainer:
        """Creates a hidden pygame_gui UIScrollingContainer with the given parameters. Saves a reference to the panel together with the screen it's shown on for future use"""
        panel=pygame_gui.elements.UIScrollingContainer(relative_rect=relative_rect, starting_height=starting_height, manager=self._gui_manager, anchors=anchors, allow_scroll_x=allow_scroll_x)
        panel.hide() #starts panel as hidden
        if screen in self._panel_dictionary:
            #already another panel of the same screen has been created
            self._panel_dictionary[screen].append((panel,always_on))
        else:
            #first panel of this screen
            self._panel_dictionary[screen]=[(panel,always_on)]
        return panel

    def show_screens(self, screen:Screens)->None:
        """Shows all panels of a given screen"""
        if screen in self._panel_dictionary:
            for element in self._panel_dictionary[screen]:
                if element[1]==True:
                    #If always on->true then display
                    element[0].show()
    
    def hide_screens(self, screen:Screens)->None:
        """Hides all panels of a given screen"""
        if screen in self._panel_dictionary:
            for element in self._panel_dictionary[screen]:
                element[0].hide()

    def delete_panels(self, screen:Screens)->None:
        """Deletes all panels of a given screen"""
        if screen in self._panel_dictionary:
            for element in self._panel_dictionary[screen]:
                element[0].kill()
            self._panel_dictionary[screen]=[]

class GameStateManager:
    """The game state manager internally stores which scene is displayed"""

    def __init__(self, start_screen:Screens, panel_handler:PanelHandler) -> None:
        self._current_state=start_screen
        self._panel_handler=panel_handler

    @property
    def current_state(self)->Screens:
        """Returns the screen the app game is on"""
        return self._current_state

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
        self._controller: GameController 
    
    @property
    def screen(self)->Screens:
        """Returns the Screen enum of the displayed screen"""
        return self._screen_id
    
    @abstractmethod
    def reset_screen(self)->None:
        """This is where your screen is reset, it should look like the fist draw"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def run(self, event:pygame.event.Event)->None:
        """This is where your screen is displayed"""
        raise NotImplementedError("Please implement this method")
    
    def set_controller(self, controller: GameController)->None:
        self._controller=controller

class View:
    """The main window for the Wiredwolf game"""
    def __init__(self)-> None:
        pygame.init() #initializes pygame modules
        self._size=(640, 400) #default starting values
        self._icon = pygame.image.load('resources/icon.png') #load image from file
        pygame.display.set_icon(self._icon) #set image as window icon
        self._display_screen = pygame.display.set_mode(self._size, pygame.RESIZABLE) #the window is resizable
        pygame.display.set_caption("Wiredwolf") #window title
        self._running = True
        self._gui_manager=pygame_gui.UIManager(self._size, theme_path='resources/theme.json')
        self._panel_handler=PanelHandler(self._gui_manager)
        self._game_state_manager=GameStateManager(Screens.HOME, self._panel_handler)
        #Sets custom event sender
        self._event_sender=CustomEventSender()
        global custom_event
        custom_event=self._event_sender.custom_event
        self._start_screen=StartScreen(Screens.HOME, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._new_lobby_screen=NewLobbyScreen(Screens.NEW_LOBBY, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._search_lobby_screen=SearchLobbyScreen(Screens.SEARCH_LOBBY, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._waiting_lobby_screen=WaitingLobbyScreen(Screens.LOBBY_WAITING, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler, self._event_sender) #TODO: is this ok?
        self._day_voting_screen=DayVotingScreen(Screens.DAY_VOTING, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._day_execution_screen=DayExecutionScreen(Screens.DAY_EXECUTION, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._night_villager_screen=NightVillagerScreen(Screens.NIGHT_VILLAGER, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._night_role_screen=NightRoleScreen(Screens.NIGHT_ROLE, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._role_display_screen=RoleDisplayScreen(Screens.ROLE_DISPLAY, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._loading_screen=LoadingLobbyScreen(Screens.LOADING_LOBBY, self._display_screen, self._game_state_manager, self._gui_manager, self._panel_handler)
        self._dictionary:dict[Screens, AbstractScreen]={self._start_screen.screen: self._start_screen,
                          self._new_lobby_screen.screen:self._new_lobby_screen, 
                          self._search_lobby_screen.screen:self._search_lobby_screen, 
                          self._waiting_lobby_screen.screen:self._waiting_lobby_screen,
                          self._day_voting_screen.screen:self._day_voting_screen,
                          self._day_execution_screen.screen: self._day_execution_screen,
                          self._night_villager_screen.screen: self._night_villager_screen,
                          self._night_role_screen.screen: self._night_role_screen,
                          self._role_display_screen.screen: self._role_display_screen,
                          self._loading_screen.screen: self._loading_screen}
        self._clock = pygame.time.Clock()
        #Activate panels of first screen
        self._panel_handler.show_screens(self._game_state_manager.current_state)
        self._controller=None

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
                surface=pygame.display.get_surface()
                if surface!=None:
                    self._size=surface.get_size()
                    #Update the manager with the new window size
                    self._gui_manager.set_window_resolution((event.x, event.y))
            else:
                #event is handled by the specific screen
                self._dictionary[self._game_state_manager.current_state].run(event)

    def update_display(self)->None:
        """Called inside the event loop, handles framerate limiting, event handling and scene switching"""
        pygame.display.update() #necessary or the screen won't draw at all
        #gui manager needs to know how much time has passed since the last update in milliseconds
        tick=self._clock.tick(FPS)
        self._gui_manager.update(tick/1000.0)
        for event in pygame.event.get():
            self._on_event(event) #handles generated events 

    def set_controller(self, controller:GameController)->None:
        """A function to connect the controller to the view"""
        self._controller=controller
        #Communicate controller to all screens
        for screen in self._dictionary:
            self._dictionary[screen].set_controller(controller)

class StartScreen(AbstractScreen):
    """The start screen, the first screen showed at startup"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager,gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        go_new_lobby=partial(self._game_state_manager.change_screen, Screens.NEW_LOBBY)
        self._new_lobby_button=EnabledButton(go_new_lobby, 'New Lobby', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, enabled=False) 
        go_search_lobby=partial(self._game_state_manager.change_screen, Screens.SEARCH_LOBBY)
        self._search_lobby_button=EnabledButton(go_search_lobby, 'Search for lobbies', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, enabled=False) 
        self._field=TextField(LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT)
        username_enter=Text("Insert username:", font=FontSize.H2)
        list_buttons:list[DrawableComponent]=[username_enter, self._field, self._new_lobby_button, self._search_lobby_button]
        self._v_container=VContainer(MEDIUM_ELEMENT_DIV, list_buttons, self._display.get_size())
        self._title_container=VContainer(SINGLE_ELEMENT_DIV, [Text("Wiredwolf")], self._display.get_size(), (50, 15))
        
    def run(self,event:pygame.event.Event)->None:
        """The start screen, the first screen showed at startup"""
        self._display.fill(BACKGROUND_COLOR) #fills the background color for the application
        self._gui_manager.draw_ui(self._display)
        self._v_container.draw(self._display)
        self._title_container.draw(self._display)
        
        #Event handling
        self._field.handle_event(event)
        tmp=self._field.text
        global username
        if len(tmp)>0 and str.isspace(tmp)==False: #the username field is filled by chars, not empty or only whitespaces
            username=self._field.text #save username in global variable
            #TODO: communicate username to controller
            self._new_lobby_button.is_enabled=True
            self._search_lobby_button.is_enabled=True
        else:
            self._new_lobby_button.is_enabled=False
            self._search_lobby_button.is_enabled=False
        self._gui_manager.process_events(event) #processes pygame_gui events
    
    def reset_screen(self) -> None:
        #Reset field text
        self._field.text=""
        pass

class NewLobbyScreen(AbstractScreen):
    """A simple new lobby screen"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._title=VContainer(SINGLE_ELEMENT_DIV,[Text("Create a new lobby")], self._display.get_size(), (50,20))
        lobby_name=Text("Insert the new lobby name", font=FontSize.H2)
        self._field=TextField(LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT)
        create_lobby=partial(self._game_state_manager.change_screen, Screens.LOBBY_WAITING)
        self._create_lobby_button=EnabledButton(create_lobby, 'Create the new lobby!', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT,font=FontSize.H2)
        go_home=partial(self._game_state_manager.change_screen, Screens.HOME)
        go_home_button=CallbackButton(go_home, 'Go back to start screen', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT ,font=FontSize.H2)
        self._button_container=VContainer(MEDIUM_ELEMENT_DIV, [lobby_name, self._field, self._create_lobby_button], self._display.get_size())
        self._button_back=VContainer(SINGLE_ELEMENT_DIV, [go_home_button], self._display.get_size(), (50, 80))
    
    def run(self,event:pygame.event.Event)->None:
        """The new lobby screen, to create a new lobby"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        self._button_container.draw(self._display)
        self._button_back.draw(self._display)
        #Event handling
        self._field.handle_event(event)
        tmp=self._field.text
        global lobby_name
        if len(tmp)>0 and str.isspace(tmp)==False: #the lobby name field is filled by chars, not empty or only whitespaces
            lobby_name=self._field.text #save new lobby name in global variable
            self._create_lobby_button.is_enabled=True
            result=self._controller.create_lobby(lobby_name, "") #TODO: add waiting for lobby to be created
        else:
            self._create_lobby_button.is_enabled=False
            lobby_name=""
        self._gui_manager.process_events(event) #processes pygame_gui events
            
    def reset_screen(self) -> None:
        #Reset lobby name
        self._field.text=""
        self._create_lobby_button.is_enabled=False
        pass

class LoadingLobbyScreen(AbstractScreen):
    """A simple loading screen shown when a lobby is being created"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._loading_container:pygame_gui.elements.UIPanel
        self._loading_bar:pygame_gui.elements.UIProgressBar
        self._current_progress=0
        self._step=1
        self._create_loading_panel()

    def run(self, event:pygame.event.Event)->None:
        self._display.fill(BACKGROUND_COLOR) #fills the background color for the application
        self._gui_manager.draw_ui(self._display)
        self._gui_manager.process_events(event) #processes pygame_gui events
        self._current_progress=self._current_progress+self._step
        if self._current_progress>=100 or self._current_progress<=2:
            self._step=-self._step #Inverts progress
        self._loading_bar.set_current_progress(self._current_progress)

    def reset_screen(self) -> None:
        #Delete panel and create it new
        self._panel_handler.delete_panels(self._screen_id)
        self._create_loading_panel()

    def _create_loading_panel(self)->None:
        """Creates the panel containing the loading element"""
        self._loading_container=self._panel_handler.create_panel(self._screen_id, pygame.rect.Rect(0,0, 110, 100), anchors={'centerx':'centerx', 'centery': 'centery'})
        self._loading_bar=pygame_gui.elements.UIProgressBar(pygame.rect.Rect(0,0, 100, 50), manager=self._gui_manager, container=self._loading_container)
        #TODO: create a class to hide progressbar text
        self._current_progress=2
        self._step=1

class SearchLobbyScreen(AbstractScreen):
    """A simple search lobby screen"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Join an existing lobby")], self._display.get_size(), (50, 10))
        go_home=partial(self._game_state_manager.change_screen, Screens.HOME)
        self._buttons=HContainer(SINGLE_ELEMENT_DIV, [CallbackButton(go_home, 'Go back to start screen', LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, font=FontSize.H2)], self._display.get_size(), (50, 85))
        #The lobbies discovered are stored in a lobby panel
        self._create_lobby_panel()
        #This is a list to store the buttons corresponding to the lobbies
        self._lobby_list:list[pygame_gui.elements.UIButton]=[]

    def run(self,event:pygame.event.Event)->None:
        """The search lobby screen, to search for existing lobbies"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        self._buttons.draw(self._display)
        global lobby_name

        #Event handling
        #process pygame_events
        #then process pygame_gui events
        self._gui_manager.process_events(event)
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            #A pygame_gui button is pressed
            if event.ui_element in self._lobby_list:
                #join the clicked lobby
                global lobby_name
                lobby_name=event.ui_element.text
                self._game_state_manager.change_screen(Screens.LOBBY_WAITING)

        #Process received custom events
        if event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, LobbyType):
                #This screen only interacts with Lobby Events
                if e.action==LobbyType.s_action_add:
                    #Add new lobby
                    length=len(self._lobby_list)
                    if length==0:
                        #First element, absolute positioning inside the container
                        self._lobby_list.insert(length, pygame_gui.elements.UIButton(relative_rect=pygame.Rect((0, MEDIUM_ELEMENT_DIV), (SMALL_BTN_WIDTH, LARGE_BTN_HEIGHT)), text=e.lobby, manager=self._gui_manager, anchors={"centerx":"centerx"}, container=self._lobby_panel))
                    else:
                        #Second element, relative positioning (below previous button)
                        self._lobby_list.insert(length, pygame_gui.elements.UIButton(relative_rect=pygame.Rect((0, MEDIUM_ELEMENT_DIV), (SMALL_BTN_WIDTH, LARGE_BTN_HEIGHT)), text=e.lobby, manager=self._gui_manager, anchors={"centerx":"centerx",'top_target': self._lobby_list[length-1]}, container=self._lobby_panel))
                    if length>self._elements_before_scrollbar:
                        #Increase scrollbar size, up to self._elements_before_scrollbar buttons can fit without a scrollbar
                        self._increased_size=(self._increased_size[0], self._increased_size[1]+LARGE_BTN_HEIGHT+MEDIUM_ELEMENT_DIV)
                        self._lobby_panel.set_scrollable_area_dimensions(self._increased_size)
                else:
                    if e.action==LobbyType.s_action_remove:
                        self._remove_lobby(e.lobby)
        
    def reset_screen(self) -> None:
        #reset lobby list
        self._lobby_list.clear()
        #Delete current panels and creates them again
        self._panel_handler.delete_panels(self._screen_id)
        self._create_lobby_panel()
    
    def _remove_lobby(self, lobby:str)->None:
        """Remove a lobby from the panel if present"""
        element_to_remove=None
        anchors=None
        for elem in self._lobby_list:
            if elem.text==lobby:
                element_to_remove=elem
                anchors=elem.anchors
                #Save anchors
            else:
                if anchors!=None:
                    #A match has been found, shift anchors (lower element gets upper element anchors)
                    temp=elem.anchors
                    elem.anchors=anchors
                    anchors=temp
                    
        #Now delete element
        if element_to_remove!=None:
            self._lobby_list.remove(element_to_remove)
            element_to_remove.kill()
            if len(self._lobby_list)>self._elements_before_scrollbar:
                #Make inner area smaller, but number of elements necessitates a scrollbar
                self._increased_size=self._increased_size[0], self._increased_size[1]-LARGE_BTN_HEIGHT-MEDIUM_ELEMENT_DIV
            else:
                #Smallest inner area possible, scrollbar disappears
                self._increased_size=self._starting_size
            self._lobby_panel.set_scrollable_area_dimensions(self._increased_size)

    def _create_lobby_panel(self)->None:
        """Creates the scrolling panel containing all lobbies buttons"""
        self._starting_size=(SMALL_PANEL, PANEL_Y) 
        self._increased_size=self._starting_size
        self._elements_before_scrollbar=int(PANEL_Y/(LARGE_BTN_HEIGHT+MEDIUM_ELEMENT_DIV))-1 #3 elements can fit without a scrollbar, 4th element needs it
        self._lobby_panel=self._panel_handler.create_scrolling_panel(self._screen_id, pygame.rect.Rect(0,0, self._starting_size[0], self._starting_size[1]), anchors={'centerx':'centerx', 'centery':'centery'})
        self._lobby_panel.set_scrollable_area_dimensions(self._starting_size)

class WaitingLobbyScreen(AbstractScreen):
    """The waiting room after joining a lobby"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler, custom_event_sender:CustomEventSender) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._custom_event_sender=custom_event_sender
        global lobby_name
        self._local_lobby=lobby_name
        self._title=Text("Waiting for other players to join "+self._local_lobby+" lobby")
        self._title_container=VContainer(SINGLE_ELEMENT_DIV, [self._title], self._display.get_size(), (50,20))
        self._text_number=Text("1 player connected...", font=FontSize.H2) #Updated count via custom events
        self._waiting=VContainer(SINGLE_ELEMENT_DIV,[self._text_number], self._display.get_size())
        self._button=CallbackButton(self._if_master_start, "Start the game!", LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT)
        go_home=partial(self._game_state_manager.change_screen, Screens.HOME)
        self._back_button=CallbackButton(go_home, "Exit lobby, go to home",LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT)
        self._button_container=HContainer(SMALL_ELEMENT_DIV, [self._button, self._back_button], self._display.get_size(), (50, 85))
        #Count and display which users are connected to the lobby
        self._counter=1
        self._users_list:list[pygame_gui.elements.UILabel]=[]
        self._create_users_panel()
        #TODO: Get initial state (users connected) of the lobby from controller
        
    def run(self,event:pygame.event.Event)->None:
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
        self._button_container.draw(self._display)
        #Event handling
        self._gui_manager.process_events(event) #processes pygame_gui events
        #Received a custom event
        if event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #This screen only interacts ChangeScreen Events
                #Should go to Day Voting Screen
                self._game_state_manager.change_screen(e.next_screen)
                self.reset_screen() #resets current screen for next time this is used
            if isinstance(e, UsersType):
                #Updates the number of players in the waiting room
                if e.action==UsersType.s_action_add:
                    #Add user
                    self._counter=self._counter+1
                    self._text_number.text=str(self._counter) +" players connected..."
                    self._waiting.update_on_next_draw()
                    self._add_player(e.username)
                if e.action==UsersType.s_action_remove:
                    #Remove user
                    self._delete_player(e.username)        
                    
    def _add_player(self, username:str)->None:
        """Add a connected player username to the panel"""
        length=len(self._users_list)
        label=None
        if length==0:
            #First element, absolute positioning inside the container
            label=pygame_gui.elements.UILabel(relative_rect=pygame.Rect((0, 0), (-1, MEDIUM_BTN_HEIGHT)), text=username, manager=self._gui_manager, anchors={}, container=self._user_panel)
        else:
            #Second element, relative positioning (below previous label)
            label=pygame_gui.elements.UILabel(relative_rect=pygame.Rect((0, 0), (-1, MEDIUM_BTN_HEIGHT)), text=username, manager=self._gui_manager, anchors={'top_target': self._users_list[length-1]}, container=self._user_panel)
        self._users_list.insert(length, label)
        #To calculate the horizontal width of the internal container
        #The horizontal scrollbar appears if the width of text inserted is bigger than the current size
        self._increased_size=(max(self._increased_size[0], label.rect[2]), self._increased_size[1]) # type: ignore
        #Vertical scrollbar
        if length>self._elements_before_scrollbar:
            self._increased_size=(self._increased_size[0], self._increased_size[1]+MEDIUM_BTN_HEIGHT+MEDIUM_ELEMENT_DIV) #Spacer to make the elements fit better
        self._user_panel.set_scrollable_area_dimensions(self._increased_size)

    def _delete_player(self, username:str)->None:
        """Remove a player username to the panel if present"""
        element_to_remove=None
        anchors=None
        biggest_width_remaining=0
        for elem in self._users_list:
            if elem.text==username:
                element_to_remove=elem
                anchors=elem.anchors
                #Save anchors
            else:
                #Get biggest width of any non-deleted element
                biggest_width_remaining=max(biggest_width_remaining, elem.rect[2]) # type: ignore
                if anchors!=None:
                    #A match has been found, shift anchors (lower element gets upper element anchors)
                    temp=elem.anchors
                    elem.anchors=anchors
                    anchors=temp
                    
        #Now delete element
        if element_to_remove!=None:
            self._users_list.remove(element_to_remove)
            element_to_remove.kill()
            self._counter=self._counter-1
            self._text_number.text=str(self._counter) +" players connected..."
            self._waiting.update_on_next_draw()
            #Scrollbar updates to horizontally biggest element not deleted and height - deleted element height
            self._increased_size=(min(self._increased_size[0], biggest_width_remaining), self._increased_size[1])
            if len(self._users_list)>self._elements_before_scrollbar:
                #Make inner area smaller, but number of elements necessitates a scrollbar
                self._increased_size=self._increased_size[0], self._increased_size[1]-MEDIUM_BTN_HEIGHT-MEDIUM_ELEMENT_DIV
            else:
                #Smallest inner area possible, scrollbar disappears
                self._increased_size=self._starting_size
            self._user_panel.set_scrollable_area_dimensions(self._increased_size)
    
    def reset_screen(self) -> None:
        #Reset lobby name
        self._local_lobby=""
        self._title.text="Waiting for other players to join lobby"
        self._title_container.update_on_next_draw()
        #Reset number of connected players
        self._text_number.text="1 player connected..."
        self._waiting.update_on_next_draw()
        #Deleted panels
        self._panel_handler.delete_panels(self._screen_id)
        #Resets users connected to game
        self._counter=0
        self._users_list.clear()
        self._create_users_panel()

    def _if_master_start(self) ->None:
        """If the button is pressed by the master, start the game"""
        #TODO: ask controller if player is master
        master=True
        if master==True: 
            self._game_state_manager.change_screen(Screens.DAY_VOTING)
            self.reset_screen() #resets current screen for next time this is used
            #Sends message that says what day it is
            self._custom_event_sender.day_message() #All other players receive the message when switching screens via event. The master won't receive this unless it sends a message to itself
            #Send message to controller that master started the game
            result=self._controller.start_game() #TODO: make waiting for start game
        else:
            #error message
            tkinter.Tk().wm_withdraw() #to hide the main window
            messagebox.showwarning('Can\'t start game', 'Only the master can start the game')
    
    def _create_users_panel(self)->None:
        """Creates the scrolling panel containing all player buttons"""
        self._starting_size=(SMALL_PANEL, PANEL_Y)  
        self._increased_size=(SMALL_PANEL-HORIZONTAL_SPACE_FOR_SCROLLBAR, PANEL_Y) #The actual inside space is slightly smaller, due to the horizontal scrollbar
        self._elements_before_scrollbar=int(PANEL_Y/MEDIUM_BTN_HEIGHT) #How many elements fit into the inner panel, rounded to the lowest integer 
        self._user_panel=self._panel_handler.create_scrolling_panel(self._screen_id, pygame.rect.Rect(20,0, self._starting_size[0], self._starting_size[1]), anchors={'left':'left', 'centery':'centery'}, allow_scroll_x=True)
        self._user_panel.set_scrollable_area_dimensions(self._starting_size)

class DayVotingScreen(AbstractScreen):
    """The screens where users chat and choose which players to nominate for an execution"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Day")], self._display.get_size(), (50, 5))
        self._text_box=MemoryTextField(LARGE_BTN_WIDTH, LARGE_BTN_HEIGHT, font=FontSize.H3) #This is where the new messages are entered
        self._container_text=VContainer(SINGLE_ELEMENT_DIV, [self._text_box], self._display.get_size(), (70,90))
        self._last_message=""
        self._create_voting_panel()
        #This is a list to store the buttons corresponding to the users
        self._player_list:list[pygame_gui.elements.UIButton]=[]
        self._voted_text=Text("Wait to vote...", font=FontSize.H3)
        self._voted_container=HContainer(SINGLE_ELEMENT_DIV, [self._voted_text], self._display.get_size(), (15, 80))
        #Chat panel
        self._create_chat_panel()
        self._chat_messages:list[pygame_gui.elements.UILabel]=[]

    def run(self,event:pygame.event.Event)->None:
        """A day waiting and voting screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._container_text.draw(self._display)
        self._title.draw(self._display)
        self._voted_container.draw(self._display)

        #Event handling
        if event.type!=custom_event:
            #pygame event, text box handles it
            self._text_box.handle_event(event) #Textbox handles key input
            tmp=self._text_box.last_input #get last message sent (if it's not already handled)
            if len(tmp)>0 and str.isspace(tmp)==False:
                #if the message is not the last message sent and it's not empty, then send the new message
                self._text_box.reset_last_input() #clear internal memory
                global username
                result=self._controller.send_chat_message(username+":"+tmp) #TODO: start coroutine and ignore result. If it fails the controller will notify you

            self._gui_manager.process_events(event) #processes pygame_gui events
            if event.type == pygame_gui.UI_BUTTON_PRESSED:
                #A pygame_gui button is pressed
                if event.ui_element in self._player_list:
                    #vote for selected player
                    voted_player=event.ui_element.text
                    self._set_voted_player(voted_player)
        if event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, UsersType):
                if e.action==UsersType.s_action_add:
                    #Add user
                    self._add_player(e.username)
                if e.action==UsersType.s_action_remove:
                    #Remove user
                    self._delete_player(e.username)
            if isinstance(e, TimeOutType):
                #Starts voting
                self._voting_panel.enable()
                self._voted_text.text="Start voting for execution!"
            if isinstance(e, ChangeScreenType):
                #End of voting, changing screen to DayExecutionScreen
                self._game_state_manager.change_screen(e.next_screen)
                self.reset_screen() #resets current screen for next time this is used
            if isinstance(e, ChatMessageType):
                #Messages received from other users
                self._send_message(e.message)

    def _add_player(self, username:str)->None:
        """Adds a new button username to the panel"""
        #Add new button username
        length=len(self._player_list)
        if length==0:
            #First element, absolute positioning inside the container
            self._player_list.insert(length, pygame_gui.elements.UIButton(relative_rect=pygame.Rect((0, MEDIUM_ELEMENT_DIV), (SMALL_BTN_WIDTH, LARGE_BTN_HEIGHT)), text=username, manager=self._gui_manager, anchors={"centerx":"centerx"}, container=self._voting_panel))
        else:
            #Second element, relative positioning (below previous button)
            self._player_list.insert(length, pygame_gui.elements.UIButton(relative_rect=pygame.Rect((0, MEDIUM_ELEMENT_DIV), (SMALL_BTN_WIDTH, LARGE_BTN_HEIGHT)), text=username, manager=self._gui_manager, anchors={"centerx":"centerx",'top_target': self._player_list[length-1]}, container=self._voting_panel))
        if length>self._elements_before_scrollbar_players:
            #Increase scrollbar size, up to 2 buttons can fit without a scrollbar
            self._increased_size=(self._increased_size[0], self._increased_size[1]+LARGE_BTN_HEIGHT+MEDIUM_ELEMENT_DIV)
            self._voting_panel.set_scrollable_area_dimensions(self._increased_size)
        self._voting_panel.disable()#All buttons start as disabled

    def _delete_player(self, username:str)->None:
        """Remove a player username to the panel if present"""
        element_to_remove=None
        anchors=None
        for elem in self._player_list:
            if elem.text==username:
                element_to_remove=elem
                anchors=elem.anchors
                #Save anchors
            else:
                if anchors!=None:
                    #A match has been found, shift anchors (lower element gets upper element anchors)
                    temp=elem.anchors
                    elem.anchors=anchors
                    anchors=temp
                    
        #Now delete element
        if element_to_remove!=None:
            self._player_list.remove(element_to_remove)
            element_to_remove.kill()
            #Scrollbar updates to horizontally biggest element not deleted and height - deleted element height
            if len(self._player_list)>self._elements_before_scrollbar_players:
                #Make inner area smaller, but number of elements necessitates a scrollbar
                self._increased_size=self._increased_size[0], self._increased_size[1]-LARGE_BTN_HEIGHT-MEDIUM_ELEMENT_DIV
            else:
                #Smallest inner area possible, scrollbar disappears
                self._increased_size=self._starting_size
            self._voting_panel.set_scrollable_area_dimensions(self._increased_size)

    def _set_voted_player(self, username:str)->None:
        """Function called when the user chooses who to nominate for execution"""
        global voted_user
        if len(username)>0:
            #can only vote a player if one is selected
            voted_user=username
            self._voted_text.text="You voted for "+voted_user
        else:
            voted_user="" #deselects player voted to be executed
            self._voted_text.text="You haven't voted"
        
    def _send_message(self, message:str)->None:
        """Function called to display a new message in chat"""
        length=len(self._chat_messages)
        label=None
        if length==0:
            #First element, absolute positioning inside the container
            label=pygame_gui.elements.UILabel(relative_rect=pygame.Rect((0, 0), (-1, MEDIUM_BTN_HEIGHT)), text=message, manager=self._gui_manager, anchors={}, container=self._chat_panel)
        else:
            #Second element, relative positioning (below previous label)
            label=pygame_gui.elements.UILabel(relative_rect=pygame.Rect((0, 0), (-1, MEDIUM_BTN_HEIGHT)), text=message, manager=self._gui_manager, anchors={'top_target': self._chat_messages[length-1]}, container=self._chat_panel) 
        self._chat_messages.insert(length, label)
        #To calculate the horizontal width of the internal container
        #The horizontal scrollbar appears if the width of text inserted is bigger than the current size
        self._increased_size_chat=(max(self._increased_size_chat[0], label.rect[2]), self._increased_size_chat[1]) # type: ignore
        #Vertical scrollbar
        if length>self._elements_before_scrollbar:
            #Increase scrollbar size, up to 2 buttons can fit without a scrollbar
            self._increased_size_chat=(self._increased_size_chat[0], self._increased_size_chat[1]+MEDIUM_BTN_HEIGHT)
        self._chat_panel.set_scrollable_area_dimensions(self._increased_size_chat)
        scroll_bar=self._chat_panel.vert_scroll_bar
        if scroll_bar!=None:
            #If there's a scroll bar, it should show the bottom of the internal panel
            #Lowest message = newest message
            scroll_bar.set_scroll_from_start_percentage(1.0)

    def _create_voting_panel(self)->None:
        """Creates the scrolling panel containing all player buttons"""
        self._starting_size=(SMALL_PANEL, PANEL_Y)  
        self._increased_size=self._starting_size
        self._elements_before_scrollbar_players=int(PANEL_Y/(LARGE_BTN_HEIGHT+MEDIUM_ELEMENT_DIV))-1 #3 elements can fit without a scrollbar, 4th element needs it
        self._voting_panel=self._panel_handler.create_scrolling_panel(self._screen_id, pygame.rect.Rect(20,0, self._starting_size[0], self._starting_size[1]), anchors={'left':'left', 'centery':'centery'})
        self._voting_panel.set_scrollable_area_dimensions(self._starting_size)
    
    def _create_chat_panel(self)->None:
        """Creates the chat panel"""
        self._starting_size_chat=(WIDE_PANEL, PANEL_Y)  
        self._increased_size_chat=(WIDE_PANEL-HORIZONTAL_SPACE_FOR_SCROLLBAR, PANEL_Y) #Inner panel is slightly smaller, has to account for scrollbars
        self._elements_before_scrollbar=int(PANEL_Y/MEDIUM_BTN_HEIGHT) #How many elements fit into the inner panel, rounded to the lowest integer 
        self._chat_panel=self._panel_handler.create_scrolling_panel(self._screen_id, pygame.rect.Rect(-WIDE_PANEL ,0, self._starting_size_chat[0], self._starting_size_chat[1]), anchors={'right':'right', 'centery':'centery'}, allow_scroll_x=True)
        #Positioning is negative because the anchor is right, same applies to bottom anchors
        self._chat_panel.set_scrollable_area_dimensions(self._increased_size_chat)
        
    def reset_screen(self) -> None:
        #reset player list
        self._player_list.clear()
        #Delete current panels and creates them again
        self._panel_handler.delete_panels(self._screen_id)
        self._create_voting_panel()
        #Wait to vote 
        self._voted_text.text="Wait to vote..."
        #Delete all chat messages
        self._chat_messages.clear()
        #Already deleted panel
        self._create_chat_panel()
        #Clears textbox input
        self._text_box.reset_last_input()
        self._text_box.text=""

class DayExecutionScreen(AbstractScreen):
    """The screen where users chat and choose if the player nominated for execution should be spared or not"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Day: execution")], self._display.get_size(), (50, 5))
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
        #Chat panel
        self._create_chat_panel()
        self._chat_messages:list[pygame_gui.elements.UILabel]=[]

    def run(self,event:pygame.event.Event)->None:
        """A day execution screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._container_text.draw(self._display)
        self._title.draw(self._display)
        self._button_container.draw(self._display)

        #Event handling
        if event.type!=custom_event:
            self._text_box.handle_event(event) #Textbox handles key input
            tmp=self._text_box.last_input #get last message sent (if it's not already handled)
            if len(tmp)>0 and str.isspace(tmp)==False:
                #if the message is not the last message sent and it's not empty, then send the new message
                self._text_box.reset_last_input() #clear internal memory
                global username
                result=self._controller.send_chat_message(username+":"+tmp) #TODO: start coroutine and ignore result. If it fails the controller will notify you
                
            self._gui_manager.process_events(event) #processes pygame_gui events
        if event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #End of day, changing screen to Night villager or night role, according to user role
                self._game_state_manager.change_screen(e.next_screen)
                self.reset_screen() #resets current screen for next time this is used
            if isinstance(e, ChatMessageType):
                #Messages received from other users
                self._send_message(e.message)
            if isinstance(e, UsersType):
                if e.action==UsersType.s_action_add:
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

    def _create_chat_panel(self)->None:
        """Creates the chat panel"""
        self._starting_size_chat=(MEDIUM_PANEL, PANEL_Y)  
        self._increased_size_chat=(MEDIUM_PANEL-HORIZONTAL_SPACE_FOR_SCROLLBAR, PANEL_Y) #Inner panel is slightly smaller, has to account for scrollbars
        self._elements_before_scrollbar=int(PANEL_Y/MEDIUM_BTN_HEIGHT) #How many elements fit into the inner panel, rounded to the lowest integer 
        self._chat_panel=self._panel_handler.create_scrolling_panel(self._screen_id, pygame.rect.Rect(-MEDIUM_PANEL,0, self._starting_size_chat[0], self._starting_size_chat[1]), anchors={'right':'right', 'centery':'centery'}, allow_scroll_x=True)
        #Positioning is negative because the anchor is right, same applies to bottom anchors
        self._chat_panel.set_scrollable_area_dimensions(self._increased_size_chat)

    def _send_message(self, message:str)->None:
        """Function called to display a new message in chat"""
        length=len(self._chat_messages)
        label=None
        if length==0:
            #First element, absolute positioning inside the container
            label=pygame_gui.elements.UILabel(relative_rect=pygame.Rect((0, 0), (-1, MEDIUM_BTN_HEIGHT)), text=message, manager=self._gui_manager, anchors={}, container=self._chat_panel)
        else:
            #Second element, relative positioning (below previous label)
            label=pygame_gui.elements.UILabel(relative_rect=pygame.Rect((0, 0), (-1, MEDIUM_BTN_HEIGHT)), text=message, manager=self._gui_manager, anchors={'top_target': self._chat_messages[length-1]}, container=self._chat_panel) 
        self._chat_messages.insert(length, label)
        #To calculate the horizontal width of the internal container
        #The horizontal scrollbar appears if the width of text inserted is bigger than the current size
        self._increased_size_chat=(max(self._increased_size_chat[0], label.rect[2]), self._increased_size_chat[1]) # type: ignore
        #Vertical scrollbar
        if length>self._elements_before_scrollbar:
            #Increase scrollbar size, up to self._elements_before_scrollbar buttons can fit without a scrollbar
            self._increased_size_chat=(self._increased_size_chat[0], self._increased_size_chat[1]+MEDIUM_BTN_HEIGHT)
        self._chat_panel.set_scrollable_area_dimensions(self._increased_size_chat)
        scroll_bar=self._chat_panel.vert_scroll_bar
        if scroll_bar!=None:
            #If there's a scroll bar, it should show the bottom of the internal panel
            #Lowest message = newest message
            scroll_bar.set_scroll_from_start_percentage(1.0)
        
    def reset_screen(self) -> None:
        #Enable buttons to execute
        self._execute_button.is_enabled=True
        self._spare_button.is_enabled=True
        #Resets outcome of voting
        self._vote_to_execute=None #Saved outcome of user voting, if None->not voted, True->executed, False->Spared
        #Reset name
        self._execute_button.text="Vote to execute "
        self._spare_button.text="Vote to spare "
        self._button_container.update_on_next_draw()
        #Delete all chat messages
        self._chat_messages.clear()
        #Already deleted panel
        self._create_chat_panel()
        #Clears textbox input
        self._text_box.reset_last_input()
        self._text_box.text=""

class NightVillagerScreen(AbstractScreen):
    """The screen where villager role users wait for the night to end"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Night")], self._display.get_size(), (50, 5))
        self._villager=VContainer(SINGLE_ELEMENT_DIV, [Text("Wait for the night to end...")], self._display.get_size())

    def run(self,event:pygame.event.Event)->None:
        """A night villager screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        self._villager.draw(self._display)
        
        #Event handling
        self._gui_manager.process_events(event) #processes pygame_gui events
        if event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #End of night, changing screen to day voting
                self._game_state_manager.change_screen(e.next_screen)
                self.reset_screen() #resets current screen for next time this is used
    
    def reset_screen(self) -> None:
        #Static screen, nothing to change
        pass

class NightRoleScreen(AbstractScreen):
    """The screen where non villager role users act during the night"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._title=VContainer(SINGLE_ELEMENT_DIV, [Text("Night")], self._display.get_size(), (50, 5))
        self._role_name=""
        self._role_text=Text("Use your power, "+self._role_name)
        self._role_container=VContainer(SINGLE_ELEMENT_DIV, [self._role_text], self._display.get_size(),(50, 10)) 
        #TODO: customize this further? ex werewolves kill this player, ...
        self._create_users_panel()
        #This is a list to store the buttons corresponding to the users
        self._players_list:list[pygame_gui.elements.UIButton]=[]
        #Wolves chat panel
        self._create_chat_panel()
        self._chat_messages:list[pygame_gui.elements.UILabel]=[]
        #Wolves chat input
        self._create_input_panel()
        self._text_input=pygame_gui.elements.UITextEntryLine(relative_rect=(0,0,MEDIUM_BTN_WIDTH, AUTO_SIZING), manager=self._gui_manager, initial_text="",container=self._input_panel)

    def run(self,event:pygame.event.Event)->None:
        """A night non villager role screen"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title.draw(self._display)
        self._role_container.draw(self._display)
        
        #Event handling
        self._gui_manager.process_events(event) #processes pygame_gui events
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            #A pygame_gui button is pressed
            if event.ui_element in self._players_list:
                #vote for selected player
                global voted_player
                voted_player=event.ui_element.text
                #TODO: communicate to controller that user acted on given player
                result=self._controller.choose_player(voted_player)
                #TODO: MAKE PLAYER IS A PEER
                self._voting_panel.disable() #Can only act once 
        if event.type==pygame_gui.UI_TEXT_ENTRY_FINISHED:
            #Enter is entered in the textbox
            if len(event.text)>0 and str.isspace(event.text)==False:
                #Message isn't empty
                result=self._controller.send_chat_message(username+":"+event.text) #TODO: start coroutine and ignore result. If it fails the controller will notify you
                self._text_input.clear() #Remove message
        if event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #End of night, changing screen to day voting
                self._game_state_manager.change_screen(e.next_screen)
                self.reset_screen() #resets current screen for next time this is used
            if isinstance(e, UsersType):
                if e.action==UsersType.s_action_add:
                #Add username to users you can act on (ex: werewolves can only kill non werewolves ecc)
                    length=len(self._players_list)
                    if length==0:
                        #First element, absolute positioning inside the container
                        self._players_list.insert(length, pygame_gui.elements.UIButton(relative_rect=pygame.Rect((0, MEDIUM_ELEMENT_DIV), (SMALL_BTN_WIDTH, LARGE_BTN_HEIGHT)), text=e.username, manager=self._gui_manager, anchors={"centerx":"centerx"}, container=self._voting_panel))
                    else:
                        #Second element, relative positioning (below previous button)
                        self._players_list.insert(length, pygame_gui.elements.UIButton(relative_rect=pygame.Rect((0, MEDIUM_ELEMENT_DIV), (SMALL_BTN_WIDTH, LARGE_BTN_HEIGHT)), text=e.username, manager=self._gui_manager, anchors={"centerx":"centerx",'top_target': self._players_list[length-1]}, container=self._voting_panel))
                    if length>self._elements_before_scrollbar_players:
                        #Increase scrollbar size, up to 2 buttons can fit without a scrollbar
                        self._increased_size=(self._increased_size[0], self._increased_size[1]+LARGE_BTN_HEIGHT+MEDIUM_ELEMENT_DIV)
                        self._voting_panel.set_scrollable_area_dimensions(self._increased_size)
            if isinstance(e, GameRoleType):
                #Personalizes screen with player role
                self._role_name=e.role
                self._role_text.text="Use your power, "+self._role_name
                self._role_container.update_on_next_draw()
                #TODO: if role==werewolf (role is already stored somewhere)
                self._chat_panel.show()
                self._input_panel.show()
                #Otherwise panels stay hidden
            if isinstance(e, ChatMessageType):
                self._send_message(e.message)
                              
    def _create_users_panel(self)->None:
        """Creates the scrolling panel containing all player buttons"""
        self._starting_size=(SMALL_PANEL, PANEL_Y) 
        self._increased_size=self._starting_size
        self._elements_before_scrollbar_players=int(PANEL_Y/(LARGE_BTN_HEIGHT+MEDIUM_ELEMENT_DIV))-1 #3 elements can fit without a scrollbar, 4th element needs it
        self._voting_panel=self._panel_handler.create_scrolling_panel(self._screen_id, pygame.rect.Rect(0,0, self._starting_size[0], self._starting_size[1]), anchors={'centerx':'centerx', 'centery':'centery'})
        self._voting_panel.set_scrollable_area_dimensions(self._starting_size)

    def _create_chat_panel(self)->None:
        """Creates the chat panel"""
        self._starting_size_chat=(MEDIUM_PANEL, PANEL_Y)  
        self._increased_size_chat=(MEDIUM_PANEL-HORIZONTAL_SPACE_FOR_SCROLLBAR, PANEL_Y) #Inner panel is slightly smaller, has to account for scrollbars
        self._elements_before_scrollbar=int(PANEL_Y/MEDIUM_BTN_HEIGHT) #How many elements fit into the inner panel, rounded to the lowest integer 
        self._chat_panel=self._panel_handler.create_scrolling_panel(self._screen_id, pygame.rect.Rect(-MEDIUM_PANEL,0, self._starting_size_chat[0], self._starting_size_chat[1]), anchors={'right':'right', 'centery':'centery'}, allow_scroll_x=True, always_on=False)
        #Positioning is negative because the anchor is right, same applies to bottom anchors
        self._chat_panel.set_scrollable_area_dimensions(self._increased_size_chat)
        #Panel default hidden unless werewolf role is set

    def _create_input_panel(self)->None:
        """Creates the text box panel"""
        self._input_panel=self._panel_handler.create_panel(self._screen_id, pygame.rect.Rect(-MEDIUM_PANEL,0, self._starting_size_chat[0], self._starting_size_chat[1]), anchors={'right':'right', 'top_target': self._chat_panel}, always_on=False)
        #Positioning is: below chat panel, same distance from right side as chat panel
        #Panel default hidden unless werewolf role is set

    def _send_message(self, message:str)->None:
        """Function called to display a new message in chat"""
        length=len(self._chat_messages)
        label=None
        if length==0:
            #First element, absolute positioning inside the container
            label=pygame_gui.elements.UILabel(relative_rect=pygame.Rect((0, 0), (-1, MEDIUM_BTN_HEIGHT)), text=message, manager=self._gui_manager, anchors={}, container=self._chat_panel)
        else:
            #Second element, relative positioning (below previous label)
            label=pygame_gui.elements.UILabel(relative_rect=pygame.Rect((0, 0), (-1, MEDIUM_BTN_HEIGHT)), text=message, manager=self._gui_manager, anchors={'top_target': self._chat_messages[length-1]}, container=self._chat_panel) 
        self._chat_messages.insert(length, label)
        #To calculate the horizontal width of the internal container
        #The horizontal scrollbar appears if the width of text inserted is bigger than the current size
        self._increased_size_chat=(max(self._increased_size_chat[0], label.rect[2]), self._increased_size_chat[1]) # type: ignore
        #Vertical scrollbar
        if length>self._elements_before_scrollbar:
            #Increase scrollbar size, up to 2 buttons can fit without a scrollbar
            self._increased_size_chat=(self._increased_size_chat[0], self._increased_size_chat[1]+MEDIUM_BTN_HEIGHT)
        self._chat_panel.set_scrollable_area_dimensions(self._increased_size_chat)
        scroll_bar=self._chat_panel.vert_scroll_bar
        if scroll_bar!=None:
            #If there's a scroll bar, it should show the bottom of the internal panel
            #Lowest message = newest message
            scroll_bar.set_scroll_from_start_percentage(1.0)

    def reset_screen(self) -> None:
        #reset player list
        self._players_list.clear()
        #Delete current panels and creates them again
        self._panel_handler.delete_panels(self._screen_id)
        self._create_users_panel()
        #Wait for role 
        self._role_text.text="Use your power, "
        #Delete all chat messages
        self._chat_messages.clear()
        #Already deleted panel
        self._create_chat_panel()
        #Delete text input, already deleted panel
        self._create_input_panel()
        self._text_input.clear()

class RoleDisplayScreen(AbstractScreen):
    """The screen displaying which role you were assigned to and explaining its powers"""
    def __init__(self, screen:Screens, display: pygame.Surface, game_state_manager:GameStateManager, gui_manager: pygame_gui.UIManager, panel_handler: PanelHandler) -> None:
        super().__init__(screen, display, game_state_manager, gui_manager, panel_handler)
        self._title=Text("Role") #Properly set via custom event
        self._title_container=VContainer(SINGLE_ELEMENT_DIV, [self._title], self._display.get_size(), (50, 20))
        self._description=Text("Description", font=FontSize.H2) #Properly set via custom event
        self._description_container=VContainer(SINGLE_ELEMENT_DIV, [self._description], self._display.get_size())
    
    def run(self, event:pygame.event.Event)->None:
        """A role screen for users"""
        self._display.fill(BACKGROUND_COLOR)
        self._gui_manager.draw_ui(self._display)
        self._title_container.draw(self._display)
        self._description_container.draw(self._display)
        
        #Event handling
        self._gui_manager.process_events(event) #processes pygame_gui events
        if event.type==custom_event:
            #parse the custom event into an object
            e=create_custom_event_from_dict(event.dict)
            if isinstance(e, ChangeScreenType):
                #Go to next screen
                self._game_state_manager.change_screen(e.next_screen)
                self.reset_screen() #resets current screen for next time this is used
            if isinstance(e, GameRoleType):
                #Update role and description
                self._title.text=e.role
                self._title_container.update_on_next_draw()
                self._description.text=e.role_description
                self._description_container.update_on_next_draw()
        
    def reset_screen(self) -> None:
        #Reset values that were sent via custom event
        self._title.text="Role"
        self._title_container.update_on_next_draw()
        self._description.text="Description"
        self._description_container.update_on_next_draw()

if __name__ == "__main__":
    my_app=View()
    controller=GameController(TcpMdnsLobbyBrowser(), Peer("Peer"))
    my_app.set_controller(controller)
    while my_app.app_running:
        my_app.update_display()
