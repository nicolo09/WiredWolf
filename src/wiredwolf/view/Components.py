from typing import Sequence
import pygame
from abc import ABC, abstractmethod

from wiredwolf.view.Constants import BACKGROUND_COLOR, BUTTON_COLOR, BUTTON_HOVER_COLOR, TEXT_COLOR

class DrawableComponent(ABC):
    """A drawable component abstraction"""
    @abstractmethod
    def draw(self, screen: pygame.Surface)->None:
        """This is the called for drawing the component on the given screen, implement this in your component class"""
        raise NotImplementedError("Please implement this method")

class AbstractButton(DrawableComponent):
    """A button abstraction, handling all internal button logic"""
    def __init__(self, text: str, width:int, height:int, position:tuple[int, int], default_color:str=BUTTON_COLOR, activation_color:str=BUTTON_HOVER_COLOR)-> None:
        pygame.font.init() #initializes pygame modules
        self._button_rect=pygame.Rect(position, (width, height)) #position is for top left
        self._button_color_not_hover=default_color #default color when not hovering
        self._button_color_hover=activation_color #default color when hovering
        self._button_color=self._button_color_not_hover #button starts as not hovering
        self._button_clicked=False #sets the button as not clicked
        guiFont=pygame.font.Font(None, 30) #generates font
        self._text_surface=guiFont.render(text, True, TEXT_COLOR) #renders the text
        self._text_rect=self._text_surface.get_rect(center=self._button_rect.center) #centers the text in the button
    
    @property
    def size(self)->tuple[int, int]:
        """Returns a button size as (width, height)"""
        return (self._button_rect.width, self._button_rect.height)
    
    @property
    def position(self)->tuple[int, int]:
        """Returns a the top left coords of the button position"""
        return (self._button_rect.x, self._button_rect.y)
    
    @position.setter
    def position(self, value:tuple[int, int]):
        """Sets the button position as a the top left coords of the button position"""
        self._button_rect.x=value[0]
        self._button_rect.y=value[1]

    def draw(self, screen: pygame.Surface)-> None:
        """Draws the button on the given surface"""
        #Since the window is resizable, the button position is calculated as centered.
        self._text_rect=self._text_surface.get_rect(center=self._button_rect.center) #re-centers the text in the button
        #draws the button as a rectangle with rounded corners
        pygame.draw.rect(screen, self._button_color, self._button_rect, border_radius=12) #border radius is for rounded corners
        screen.blit(self._text_surface, self._text_rect) #draws the rectangle on the given screen
        self._handle_button_click() #function that checks if the button has been pressed 
    
    def _handle_button_click(self)-> None:
        """Checks if button has been pressed and starts on click function"""
        mouse_pos =pygame.mouse.get_pos() #returns mouse position
        if self._button_rect.collidepoint(mouse_pos): #is the mouse over the button?
            self._button_color=self._button_color_hover #changes button color to hover
            if pygame.mouse.get_pressed()[0]: #[left mouse, middle mouse, right mouse] boolean
                self._button_clicked=True #sets button as pressed
            else:
                if self._button_clicked==True:
                    self.on_click() #does action
                    self._button_clicked=False #resets button
                    #if no check is applied the button would be pressed many times per frame
        else:
            #mouse button is not pressed, restores original color
            self._button_color=self._button_color_not_hover

    @abstractmethod
    def on_click(self)-> None:
        """This is the action done when the button is pressed, implement this in your button class"""
        raise NotImplementedError("Please implement this method")
    
class CenteredText(DrawableComponent):
    """Text centered horizontally in the window"""
    def __init__(self, text: str, color:str=TEXT_COLOR)-> None:
        pygame.font.init() #initializes pygame modules
        font=pygame.font.Font(None, 30) #generates font
        self._text_surface=font.render(text, True, color) #renders the text

    def draw(self, screen: pygame.Surface)-> None:
        """Draws the text on the given surface"""
        win_size=screen.get_size()
        x_coord=int((win_size[0]-self._text_surface.get_size()[0])/2)
        screen.blit(self._text_surface, (x_coord,10))
        
class ButtonVContainer(DrawableComponent):
    """A button container that displays the given buttons vertically and automatically re-centers the buttons on window resize"""
    def __init__(self, vert_div:int, buttons:Sequence[AbstractButton], win_size:tuple[int, int], color:str=BACKGROUND_COLOR)-> None:
        if len(buttons)==0:
            raise ValueError("Must contain at least a button")
        pygame.font.init() #initializes pygame modules
        self._divider=vert_div
        self._buttons=buttons
        self._win_size=win_size
        self._color=color
        self._dimensions=(0,0)
        self._set_dimensions() #these are the dimensions of the container, calculated with the buttons list and the vertical divider
        #the top left corner of the container is at total window size/2 (which would be the center of the window) - container size/2
        #this operation is done on both axis, to derive the position for the top left corner
        self._top_left_pos=(0,0)
        self._set_top_left_position() #this is the position of the top left corner of the container 
        self._rect=pygame.Rect(self._top_left_pos, self._dimensions)
        self._center_buttons()

    def _center_buttons(self)-> None:
        """Sets button position as:
            x-> x coord of container
            y-> y coord of container + size of buttons before + n-1 dividers"""
        #y coord = top left coord + button size + div
        #x coord = top left coord
        ycoord=self._top_left_pos[1]
        xcoord=self._top_left_pos[0]
        for button in self._buttons:
            button.position=(xcoord, ycoord)
            ycoord=ycoord+button.size[1]+self._divider
        
    def _set_dimensions(self)-> None:
        """Sets container dimensions:
            x-> max x of buttons contained
            y-> sum of y of buttons contained + n-1 * vertical divider spacer
            This allows the container to have the buttons aligned with some vertical separation"""
        dimensionsX=0
        dimensionsY=0
        for button in self._buttons:
            #the button container will have size defined as such:
            #x: max of button x in given list
            #y: sum of button y in given list + n-1 *vertDiv
            #this should permit the container to have the buttons aligned with some vertical separation
            dimensionsY=dimensionsY+button.size[1]
            dimensionsX=max(dimensionsX, button.size[0])
        dimensionsY=dimensionsY+(len(self._buttons)-1)*self._divider
        self._dimensions=(dimensionsX, dimensionsY)
    
    def _set_top_left_position(self)-> None:
        """Sets container position, knowing container dimensions and window dimension"""
        self._top_left_pos=(int((self._win_size[0]/2)-(self._dimensions[0]/2)), int((self._win_size[1]/2)-(self._dimensions[1]/2)))

    def draw(self, screen: pygame.Surface)-> None:
        """Draws the button container centered on the given surface"""
        win_size=screen.get_size()
        if win_size!=self._win_size:
            self._win_size=win_size
            #window size was changed, re-center container
            self._set_top_left_position()
            self._rect.x=self._top_left_pos[0]
            self._rect.y=self._top_left_pos[1]
            #re-centers buttons inside the new container
            self._center_buttons()
        pygame.draw.rect(screen, self._color, self._rect)
        for button in self._buttons:
            button.draw(screen)
        pygame.display.flip() #draws the elements on the screen

class PrintButton(AbstractButton):
    """A simple button implementation that prints a test string"""
    def on_click(self)-> None:
        """Prints a test string when the button is pressed"""
        print("Hello concrete method")

class CallbackButton(AbstractButton):
    """A button that calls the callback on click"""
    #TODO: callback typing
    def __init__(self, callback, text: str, width:int, height:int, position:tuple[int, int], default_color:str=BUTTON_COLOR, activation_color:str=BUTTON_HOVER_COLOR)-> None:
        super().__init__(text, width, height, position, default_color, activation_color)
        self._callback=callback
    def on_click(self)-> None:
        """Calls the callback function"""
        self._callback()

class TextField(DrawableComponent):
    """A drawable text field. When the user clicks on the field and writes, it displays what is being written"""
    def __init__(self, width:int, height:int, position:tuple[int, int], text_color:str=TEXT_COLOR, active_color:str=BUTTON_HOVER_COLOR, not_active_color:str=BUTTON_COLOR)->None:
        self._rect = pygame.Rect(position, (width, height))
        self._not_active_color = not_active_color
        self._active_color=active_color
        self._current_color=self._not_active_color
        self._text_color=text_color
        self._text = ""
        pygame.font.init() #initializes pygame modules
        self._font=pygame.font.Font(None, 30) #generates font
        self._txt_surface = self._font.render(self._text, True, self._text_color)
        self._active = False 

    @property
    def text(self)->str:
        """Returns the currently written text"""
        return self._text

    def handle_event(self, event:pygame.event.Event)->None:
        """Handles events and updates the text shown"""
        if event.type== pygame.MOUSEBUTTONDOWN and self._rect.collidepoint(event.pos):
            #if the user clicks inside the rectangle, the text box is activated or not
            self._active=not self._active
            #changes color
            if self._current_color==self._active_color:
                self._current_color=self._not_active_color
            else:
                self._current_color=self._active_color
        if event.type==pygame.KEYUP and self._active==True:
            if event.key == pygame.K_BACKSPACE:
                #deletes the last char
                self._text = self._text[:-1]
            else:
                if event.key!=pygame.K_RETURN: #skips enters, otherwise a "􏿮" is displayed
                    #adds the char to the text
                    self._text = self._text+event.unicode

    def draw(self, screen: pygame.Surface) -> None:
        """Draws the text field on the given surface"""
        self._txt_surface=self._font.render(self._text, True, self._text_color)
        screen.blit(self._txt_surface, (self._rect.x+5, self._rect.y+5))
        pygame.draw.rect(screen, self._current_color, self._rect, 2) #border width

if __name__ == "__main__":
    print("Hello world")
