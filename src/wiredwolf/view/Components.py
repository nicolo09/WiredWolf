from typing import Sequence
import pygame
from abc import ABC, abstractmethod
from collections.abc import Callable

from wiredwolf.view.Constants import BACKGROUND_COLOR, BUTTON_COLOR, BUTTON_DISABLED_COLOR, BUTTON_HOVER_COLOR, SELECTED_COLOR, TEXT_COLOR, FontSize

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
        self._text_surface=self._font.render(text, True, TEXT_COLOR) #renders the text
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

    @property
    def text(self)->str:
        return self._text
    
    @text.setter
    def text(self, new_text:str)->None:
        self._text=new_text
        
class VContainer():
    """A drawable container that displays the given components vertically"""
    def __init__(self, vert_div:int, elements:Sequence[DrawableComponent], win_size:tuple[int, int], position:tuple[int,int]=(50,50), color:str=BACKGROUND_COLOR)-> None:
        if len(elements)==0:
            raise ValueError("Must contain at least a button")
        if position[0]<0 or position[0]>100 or position[1]<0 or position[1]>100:
            raise ValueError("Position must be between 0 and 100")
        self._divider=vert_div
        self._elements=elements
        self._win_size=win_size
        self._color=color
        self._dimensions=(0,0)
        self._offset=position
        self._set_dimensions() #these are the dimensions of the container, calculated with the components list and the vertical divider
        #the top left corner of the container is at total window size/2 (which would be the center of the window) - container size/2
        #this operation is done on both axis, to derive the position for the top left corner
        self._top_left_pos=(0,0)
        self._set_top_left_position() #this is the position of the top left corner of the container 
        self._rect=pygame.Rect(self._top_left_pos, self._dimensions)
        self._center_elements()
    
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
    
    def _set_top_left_position(self)-> None:
        """Sets container position, knowing container dimensions and window dimension"""
        #Uses offset, measured as a number between 0 and 100 to align the container
        self._top_left_pos=(int((self._win_size[0]/100)*self._offset[0]-(self._dimensions[0]/2)), 
                            int((self._win_size[1]/100)*self._offset[1]-(self._dimensions[1]/2)))

    def draw(self, screen: pygame.Surface)-> None:
        """Draws the container offset on the given surface"""
        win_size=screen.get_size()
        if win_size!=self._win_size:
            self._win_size=win_size
            #window size was changed, re-center container
            self.manually_update()
        pygame.draw.rect(screen, self._color, self._rect)
        for element in self._elements:
            element.draw(screen)
    
    def manually_update(self)->None:
        """If any component inside the container is changed (ex a Text.text), call this function to trigger an update to the size of the container"""
        self._set_dimensions()
        self._set_top_left_position()
        self._rect.x=self._top_left_pos[0]
        self._rect.y=self._top_left_pos[1]
        self._center_elements()


class HContainer():
    """A drawable container that displays the given components horizontally"""
    def __init__(self, horiz_div:int, elements:Sequence[DrawableComponent], win_size:tuple[int, int], position:tuple[int,int]=(50,50), color:str=BACKGROUND_COLOR)-> None:
        if len(elements)==0:
            raise ValueError("Must contain at least a button")
        if position[0]<0 or position[0]>100 or position[1]<0 or position[1]>100:
            raise ValueError("Position must be between 0 and 100")
        self._divider=horiz_div
        self._elements=elements
        self._win_size=win_size
        self._color=color
        self._dimensions=(0,0)
        self._offset=position
        self._set_dimensions() #these are the dimensions of the container, calculated with the components list and the vertical divider
        #the top left corner of the container is at total window size/2 (which would be the center of the window) - container size/2
        #this operation is done on both axis, to derive the position for the top left corner
        self._top_left_pos=(0,0)
        self._set_top_left_position() #this is the position of the top left corner of the container 
        self._rect=pygame.Rect(self._top_left_pos, self._dimensions)
        self._center_elements()
    
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
    
    def _set_top_left_position(self)-> None:
        """Sets container position, knowing container dimensions and window dimension"""
        #Uses offset, measured as a number between 0 and 100 to align the container
        self._top_left_pos=(int((self._win_size[0]/100)*self._offset[0]-(self._dimensions[0]/2)), 
                            int((self._win_size[1]/100)*self._offset[1]-(self._dimensions[1]/2)))

    def draw(self, screen: pygame.Surface)-> None:
        """Draws the container offset on the given surface"""
        win_size=screen.get_size()
        if win_size!=self._win_size:
            self._win_size=win_size
            #window size was changed, re-center container
            self.manually_update()
        pygame.draw.rect(screen, self._color, self._rect)
        for element in self._elements:
            element.draw(screen)
    
    def manually_update(self)->None:
        """If any component inside the container is changed (ex a Text.text), call this function to trigger an update to the size of the container"""
        self._set_dimensions()
        self._set_top_left_position()
        self._rect.x=self._top_left_pos[0]
        self._rect.y=self._top_left_pos[1]
        #re-centers buttons inside the new container
        self._center_elements()

class PrintButton(AbstractButton):
    """A simple button implementation that prints a test string"""
    def on_click(self)-> None:
        """Prints a test string when the button is pressed"""
        print("Hello concrete method")

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
    def __init__(self, callback:Callable[[],None], text: str, width:int, height:int, position:tuple[int, int]=(0,0), font:FontSize=FontSize.H1, disabled_color:str=BUTTON_DISABLED_COLOR,default_color:str=BUTTON_COLOR, activation_color:str=BUTTON_HOVER_COLOR)-> None:
        super().__init__(callback, text, width, height, position, font, default_color, activation_color)
        self._is_enabled=False
        self._disabled_color=BUTTON_DISABLED_COLOR
    
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
        else:
            self._button_color=self._disabled_color

class SelectorButton(AbstractButton):
    """A button that can be selected or unselected"""
    def __init__(self, text: str, width:int, height:int, position:tuple[int, int]=(0,0), font:FontSize=FontSize.H1, default_color:str=BUTTON_COLOR, activation_color:str=BUTTON_HOVER_COLOR, selected_color:str=SELECTED_COLOR)-> None:
        super().__init__(text, width, height, position, font, default_color, activation_color)
        self._selected=False
        self._selected_color=selected_color
        self._callback=print #Placeholder function. Selector buttons should be grouped into a Selector Group, which sets the correct callback

    @property
    def selected(self)->bool:
        """Returns selected status"""
        return self._selected
    
    @selected.setter
    def selected(self, selected:bool)->None:
        """Sets selected status"""
        self._selected=selected
    
    @property
    def text(self)->str:
        """Returns button text"""
        return self._text
    
    @property
    def callback(self)->Callable[[],None]:
        """Returns the callback function called on click"""
        #Needed or the setter won't work
        return self._callback

    @callback.setter
    def callback(self, callback:Callable[[],None])->None:
        """Sets the callback function called on click"""
        self._callback=callback


    def _handle_button_click(self)-> None:
        """Checks if button has been pressed and starts on click function"""
        mouse_pos =pygame.mouse.get_pos() #returns mouse position
        if self._button_rect.collidepoint(mouse_pos): #is the mouse over the button?
            if pygame.mouse.get_pressed()[0]: #[left mouse, middle mouse, right mouse] boolean
                self._button_clicked=True #sets button as pressed
            else:
                if self._button_clicked==True:
                    self._selected=not self.selected #inverts selection
                    self.on_click() #does action
                    self._button_clicked=False #resets button
                    #if no check is applied the button would be pressed many times per frame

    def on_click(self)-> None:
        """Calls the on click function"""
        self._callback()
    
    def draw(self, screen: pygame.Surface)-> None:
        """Draws the button on the given surface"""
        #Since the window is resizable, the button position is calculated as centered.
        self._text_rect=self._text_surface.get_rect(center=self._button_rect.center) #re-centers the text in the button
        #draws the button as a rectangle with rounded corners
        if self._selected==True:
            self._button_color=self._selected_color #changes color if the button is selected
        else:
            self._button_color=self._button_color_not_hover #default color
        pygame.draw.rect(screen, self._button_color, self._button_rect, border_radius=12) #border radius is for rounded corners
        screen.blit(self._text_surface, self._text_rect) #draws the rectangle on the given screen
        self._handle_button_click() #function that checks if the button has been pressed 

class SelectorGroup():
    """A group of selectors. Only 0 or 1 at most elements can be selected at once"""
    def __init__(self, selectors:Sequence[SelectorButton])->None:
        assert(len(selectors)>=1) #A selector group with 0 elements doesn't make sense
        self._selectors=self._convert_sequence_to_dictionary(selectors)
        self._selected_element=None
        for id in self._selectors:
            self._selectors[id].callback=self._update

    def _convert_sequence_to_dictionary(self, list:Sequence[SelectorButton])->dict[int,SelectorButton]:
        """Converts the given list into a dictionary, such as {1: list[1], ....}"""
        index=1
        dict={index:list[index]} #Needed to initialize the list with the correct typing
        for element in list:
            #Adds all other elements to the list
            dict[index]=element
            index=index+1
        return dict

    def _update(self)->None:
        """Keeps integrity of group by de-selecting if necessary oldest selector"""
        new_selected=None
        count_selected=0
        for id in self._selectors:
            if self._selectors[id].selected==True:
                count_selected=count_selected+1 #count how many elements are selected right now
                if self._selected_element!=id:
                    new_selected=id #if the element is selected and it's not the saved element->2 elements are selected
        if count_selected==0:
            #No elements selected
            self._selected_element=None
        else:
            if count_selected==1 and self._selected_element is None:
                #A new element has been selected
                self._selected_element=new_selected
            else: 
                if count_selected==2:
                    #Two elements selected, oldest element is deselected and newest remains
                    assert(self._selected_element)
                    self._selectors[self._selected_element].selected=False
                    self._selected_element=new_selected
    
    def selectedText(self)->str:
        """Returns the text of the selected element, or no text if no element is selected"""
        if self._selected_element is None:
            return ""
        else :
            return self._selectors[self._selected_element].text

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

if __name__ == "__main__":
    print("Hello world")
