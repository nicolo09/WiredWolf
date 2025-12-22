import unittest

from wiredwolf.view.custom_events import *

class TestCustomEvents(unittest.TestCase):
    """Unit test for view custom events"""

    def setUp(self) -> None:
        pygame.init()
        self.event_sender=CustomEventSender()
        self.custom_event=self.event_sender.custom_event
        self.change_screen=ChangeScreenType(Screens.HOME)
        self.discovered_lobby=DiscoveredLobbyType("lobby")
        self.username=UsersType("Mario")
        self.timeout=TimeOutType()
        self.waiting_users=WaitingRoomType(2)
        self.chat_message=ChatMessageType("Mario:Hello!")
        self.role=GameRoleType("Villager", "Try not to die, vote out the werewolves")

    def test_custom_event_serialization(self)->None:
        """A custom event serialized and deserialized should be the same"""
        self.assertEqual(self.change_screen, create_custom_event_from_dict(self.change_screen.as_dictionary()))
        self.assertEqual(self.discovered_lobby, create_custom_event_from_dict(self.discovered_lobby.as_dictionary()))
        self.assertEqual(self.username, create_custom_event_from_dict(self.username.as_dictionary()))
        self.assertEqual(self.timeout, create_custom_event_from_dict(self.timeout.as_dictionary())) #Useless, no information is passed via dictionary other than type
        self.assertEqual(self.waiting_users, create_custom_event_from_dict(self.waiting_users.as_dictionary()))
        self.assertEqual(self.chat_message, create_custom_event_from_dict(self.chat_message.as_dictionary()))
        self.assertEqual(self.role, create_custom_event_from_dict(self.role.as_dictionary()))

    def test_custom_event_pygame(self)->None:
        """An event sent to the game loop should be parsed correctly"""
        events_recived=0
        total_events=7
        self.event_sender.send_event_to_screen(self.change_screen.next_screen)
        self.event_sender.send_event_discovered_new_lobby(self.discovered_lobby.discovered_lobby)
        self.event_sender.send_event_new_user(self.username.username)
        self.event_sender.send_event_timeout()
        self.event_sender.send_event_waiting_room(self.waiting_users.number)
        self.event_sender.send_event_chat_message(self.chat_message.message)
        self.event_sender.send_event_game_role(self.role.role, self.role.role_description)

        while events_recived<total_events:
            for event in pygame.event.get():
                if event.type==self.custom_event:
                    e=create_custom_event_from_dict(event.dict)
                    if isinstance(e, ChangeScreenType):
                        self.assertEqual(e, self.change_screen)
                        events_recived=events_recived+1
                    if isinstance(e, DiscoveredLobbyType):
                        self.assertEqual(e, self.discovered_lobby)
                        events_recived=events_recived+1 
                    if isinstance(e, UsersType):
                        self.assertEqual(e, self.username)
                        events_recived=events_recived+1
                    if isinstance(e, TimeOutType):
                        self.assertEqual(e, self.timeout) #Useless, no information is passed via dictionary other than type
                        events_recived=events_recived+1
                    if isinstance(e, WaitingRoomType):
                        self.assertEqual(e, self.waiting_users) 
                        events_recived=events_recived+1
                    if isinstance(e, ChatMessageType):
                        self.assertEqual(e, self.chat_message) 
                        events_recived=events_recived+1
                    if isinstance(e, GameRoleType):
                        self.assertEqual(e, self.role) 
                        events_recived=events_recived+1
        #Recived all events
        self.assertEqual(events_recived, total_events)
