from typing import List
import pygame
from abc import ABC, abstractmethod
from collections.abc import Callable
import copy

from wiredwolf.view.constants import FontSize
from wiredwolf.view.view_constants import *

class DrawableComponent(ABC):
    """A drawable component abstraction"""
    
    @property
    @abstractmethod
    def size(self)->tuple[int, int]:
        """Returns the size of the component as (width, height)"""
        raise NotImplementedError("Please implement this method")
    
    @property
    @abstractmethod
    def position(self)->tuple[int, int]:
        """Returns the coordinates of the top left position of the component"""
        raise NotImplementedError("Please implement this method")
    
    @position.setter
    @abstractmethod
    def position(self, value:tuple[int, int])->None:
        """Sets the coordinates of the top left position of the component"""
        raise NotImplementedError("Please implement this method")

    @abstractmethod
    def draw(self, screen: pygame.Surface)->None:
        """Draws the component on the given screen"""
        raise NotImplementedError("Please implement this method")

    @property
    def text(self)->str:
        """Returns the text of the component"""
        return self._text
    
    @text.setter
    def text(self, new_text:str)->None:
        """Sets the text of the component"""
        self._text=new_text

class AbstractButton(DrawableComponent):
    """A button abstraction, handling all internal button logic"""

    def __init__(self, text: str, width:int, height:int, position:tuple[int, int]=(0,0), font:FontSize=FontSize.H1, default_color:str=BUTTON_COLOR, activation_color:str=BUTTON_HOVER_COLOR)-> None:
        self._button_rect=pygame.Rect(position, (width, height)) #position is for top left
        self._button_color_not_hover=default_color #default color when not hovering
        self._button_color_hover=activation_color #default color when hovering
        self._button_color=self._button_color_not_hover #button starts as not hovering
        self._button_clicked=False #sets the button as not clicked
        self._font=font.value #gets the font chosen
        self._text=text
        self._text_surface=self._font.render(self._text, True, TEXT_COLOR) #renders the text
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

    @property
    def text(self)->str:
        """Returns button text"""
        return self._text
    
    @text.setter
    def text(self, new_text:str)->None:
        """Sets button text"""
        self._text=new_text

    def draw(self, screen: pygame.Surface)-> None:
        """Draws the button on the given surface"""
        #Since the window is resizable, the button position is calculated as centered.
        self._text_surface=self._font.render(self._text, True, TEXT_COLOR) #renders the text
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
    
class Text(DrawableComponent):
    """Text displayed in the window"""
    
    def __init__(self, text: str, coords:tuple[int, int]=(0,0), font:FontSize=FontSize.H1, color:str=TEXT_COLOR)-> None:
        self._font=font.value
        self._text=text
        self._coords=coords
        self._color=color
        self._text_surface=self._font.render(self._text, True, self._color) #renders the text

    def draw(self, screen: pygame.Surface)-> None:
        """Draws the text on the given surface"""
        self._text_surface=self._font.render(self._text, True, self._color) #renders the text
        screen.blit(self._text_surface, self._coords)

    @property
    def size(self)->tuple[int, int]:
        """Returns a text size as (width, height)"""
        return self._text_surface.get_size()
    
    @property
    def position(self)->tuple[int, int]:
        """Returns a the top left coords of the text position"""
        return self._coords
    
    @position.setter
    def position(self, value:tuple[int, int]):
        """Sets the given position as a the top left coords of the text position"""
        self._coords=value
        
class AbstractContainer(ABC):
    """An abstract container that displays the given components"""
    def __init__(self, div:int, elements:List[DrawableComponent], win_size:tuple[int, int], position:tuple[int,int]=(50,50), color:str=BACKGROUND_COLOR, fixed_other_dim:int=0)-> None:
        if position[0]<0 or position[0]>100 or position[1]<0 or position[1]>100:
            raise ValueError("Position must be between 0 and 100")
        self._divider=div
        self._elements:List[DrawableComponent] =copy.copy(elements)
        self._trigger_update=False #When a new element is added inside the list, on the next draw triggers a re-calculation for dimensions
        self._win_size=win_size
        self._color=color
        self._dimensions=(0,0)
        self._top_left_pos=(0,0)
        self._offset=position
        self._set_dimensions() #these are the dimensions of the container, calculated with the components list and the given divider
        self._fixed_dim=fixed_other_dim
        if self._fixed_dim!=0:
            #if a fixed dimension is set, then the calculated dimension is overridden for the specific dimension
            self._dimensions_if_fixed_dim()
        self._top_left_pos=(0,0)
        self._set_top_left_position() #this is the position of the top left corner of the container 
        self._rect=pygame.Rect(self._top_left_pos, self._dimensions)
        self._center_elements()
    
    def _center_elements(self)-> None:
        """Centers elements inside the container"""
        raise NotImplementedError("Please implement this method")
        
    def _set_dimensions(self)-> None:
        """Sets the dimensions of the container in order to allow the elements to be displayed without overlapping"""
        raise NotImplementedError("Please implement this method")

    def _dimensions_if_fixed_dim(self)->None:
        """Sets the fixed dimension if set"""
        raise NotImplementedError("Please implement this method")
    
    def _set_top_left_position(self)-> None:
        """Sets container position, knowing container dimensions and window dimension"""
        #Uses offset, measured as a number between 0 and 100 to align the container
        self._top_left_pos=(int((self._win_size[0]/100)*self._offset[0]-(self._dimensions[0]/2)), 
                            int((self._win_size[1]/100)*self._offset[1]-(self._dimensions[1]/2)))

    def draw(self, screen: pygame.Surface)-> None:
        """Draws the container offset on the given surface"""
        pygame.draw.rect(screen, self._color, self._rect)
        for element in self._elements:
            element.draw(screen)
        #If the size of the screen changed or some drawable inside the container changed, re-calculate coordinates to draw the elements correctly
        win_size=screen.get_size()
        if win_size!=self._win_size or self._trigger_update==True:
            self._win_size=win_size
            #window size was changed, re-center container
            self._manually_update()
            self._trigger_update=False
    
    def _manually_update(self)->None:
        """Triggers a re-calculation of all the dimensions of the container"""
        self._set_dimensions()
        if self._fixed_dim!=0:
            self._dimensions_if_fixed_dim()
        self._set_top_left_position()
        self._rect.x=self._top_left_pos[0]
        self._rect.y=self._top_left_pos[1]
        self._rect.width=self._dimensions[0]
        self._rect.height=self._dimensions[1]
        self._center_elements()
    
    def add_element(self, drawable:DrawableComponent)->None:
        """Adds a new drawable component to the container"""
        self._elements.append(drawable)
        self.update_on_next_draw()
    
    def update_on_next_draw(self)->None:
        """Call this function when a drawable component inside the container has changed size to trigger a re-centering on the next call of draw"""
        self._trigger_update=True
    
    def get_count(self)->int:
        """Returns the number of elements inside the container"""
        return len(self._elements)

class VContainer(AbstractContainer):
    """A drawable container that displays the given components vertically"""

    def __init__(self, vert_div:int, elements:List[DrawableComponent], win_size:tuple[int, int], position:tuple[int,int]=(50,50), color:str=BACKGROUND_COLOR, fixed_width:int=0)-> None:
        super().__init__(vert_div, elements, win_size, position, color, fixed_width)
    
    def _center_elements(self)-> None:
        """Sets element position as:
            x-> x coord of container
            y-> y coord of container + size of element before + n-1 dividers"""
        #y coord = top left coord + button size + div
        #x coord = top left coord
        ycoord=self._top_left_pos[1]
        xcoord=self._top_left_pos[0]
        for element in self._elements:
            element.position=(xcoord, ycoord)
            ycoord=ycoord+element.size[1]+self._divider
        
    def _set_dimensions(self)-> None:
        """Sets container dimensions:
            x-> max x of elements contained
            y-> sum of y of elements contained + n-1 * vertical divider spacer
            This allows the container to have the elements stacked vertically with some vertical separation"""
        dimensionsX=0
        dimensionsY=0
        for element in self._elements:
            #the button container will have size defined as such:
            #x: max of button x in given list
            #y: sum of button y in given list + n-1 *vertDiv
            #this should permit the container to have the buttons aligned with some vertical separation
            dimensionsY=dimensionsY+element.size[1]
            dimensionsX=max(dimensionsX, element.size[0])
        dimensionsY=dimensionsY+(len(self._elements)-1)*self._divider
        self._dimensions=(dimensionsX, dimensionsY)

    def _dimensions_if_fixed_dim(self) -> None:
        """Sets the width to fixed"""
        self._dimensions=(self._fixed_dim, self._dimensions[1])

class HContainer(AbstractContainer):
    """A drawable container that displays the given components horizontally"""

    def __init__(self, horiz_div:int, elements:List[DrawableComponent], win_size:tuple[int, int], position:tuple[int,int]=(50,50), color:str=BACKGROUND_COLOR, fixed_height:int=0)-> None:
        super().__init__(horiz_div, elements, win_size, position, color, fixed_height)
    
    def _center_elements(self)-> None:
        """Sets element position as:
            x-> x coord of container + size of element before + n-1 dividers
            y-> y coord of container"""
        #y coord = top left coord + button size + div
        #x coord = top left coord
        ycoord=self._top_left_pos[1]
        xcoord=self._top_left_pos[0]
        for element in self._elements:
            element.position=(xcoord, ycoord)
            xcoord=xcoord+element.size[0]+self._divider
        
    def _set_dimensions(self)-> None:
        """Sets container dimensions:
            x-> max x of elements contained
            y-> sum of y of elements contained + n-1 * vertical divider spacer
            This allows the container to have the elements stacked vertically with some vertical separation"""
        dimensionsX=0
        dimensionsY=0
        for element in self._elements:
            #the container will have size defined as such:
            #y: max of elements y in given list
            #x: sum of button x in given list + n-1 *horizontal div
            #this should permit the container to have the buttons aligned with some horizontal separation
            dimensionsY=max(dimensionsY, element.size[1])
            dimensionsX=dimensionsX+element.size[0]
        dimensionsX=dimensionsX+(len(self._elements)-1)*self._divider
        self._dimensions=(dimensionsX, dimensionsY)
    
    def _dimensions_if_fixed_dim(self) -> None:
        """Sets the height to fixed"""
        self._dimensions=(self._dimensions[0], self._fixed_dim)

class CallbackButton(AbstractButton):
    """A button that calls the callback on click"""

    def __init__(self, callback:Callable[[],None], text: str, width:int, height:int, position:tuple[int, int]=(0,0), font:FontSize=FontSize.H1, default_color:str=BUTTON_COLOR, activation_color:str=BUTTON_HOVER_COLOR)-> None:
        super().__init__(text, width, height, position, font, default_color, activation_color)
        self._callback=callback

    def on_click(self)-> None:
        """Calls the callback function"""
        self._callback()

class EnabledButton(CallbackButton):
    """A button that calls the callback on click, if the button is enabled"""

    def __init__(self, callback:Callable[[],None], text: str, width:int, height:int, enabled:bool=False, position:tuple[int, int]=(0,0), font:FontSize=FontSize.H1, disabled_color:str=BUTTON_DISABLED_COLOR,default_color:str=BUTTON_COLOR, activation_color:str=BUTTON_HOVER_COLOR)-> None:
        super().__init__(callback, text, width, height, position, font, default_color, activation_color)
        self._is_enabled=enabled
        self._disabled_color=disabled_color
    
    @property
    def is_enabled(self)->bool:
        """Returns if the button is enabled"""
        return self._is_enabled
    
    @is_enabled.setter
    def is_enabled(self, value:bool)->None:
        """Sets if the button is enabled to the given value"""
        self._is_enabled=value

    def _handle_button_click(self)-> None:
        """Checks if button has been pressed and starts on click function, if the button is enabled"""
        if self._is_enabled==True:
            super()._handle_button_click()
        else:
            self._button_color=self._disabled_color

class TextField(DrawableComponent):
    """A drawable text field. When the user clicks on the field and writes, it displays what is being written"""

    def __init__(self, width:int, height:int, position:tuple[int, int]=(0,0), font:FontSize=FontSize.H1, text_color:str=TEXT_COLOR, active_color:str=BUTTON_HOVER_COLOR, not_active_color:str=BUTTON_COLOR)->None:
        self._rect = pygame.Rect(position, (width, height))
        self._not_active_color = not_active_color
        self._active_color=active_color
        self._current_color=self._not_active_color
        self._text_color=text_color
        self._text = ""
        self._font=font.value
        self._txt_surface = self._font.render(self._text, True, self._text_color)
        self._active = False 

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
        screen.blit(self._txt_surface, (self._rect.x+5, self._rect.y+5)) #+5 to make it more centered in the rectangle outline
        pygame.draw.rect(screen, self._current_color, self._rect, 2) #border width

    @property
    def size(self)->tuple[int, int]:
        """Returns a text field size as (width, height)"""
        return self._rect.size
    
    @property
    def position(self)->tuple[int, int]:
        """Returns a the top left coords of the text field position"""
        return (self._rect.x, self._rect.y)
    
    @position.setter
    def position(self, value:tuple[int, int]):
        """Sets the given position as a the top left coords of the text field position"""
        self._rect.x=value[0]
        self._rect.y=value[1]
