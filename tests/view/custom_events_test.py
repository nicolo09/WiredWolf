import unittest

from wiredwolf.view.custom_events import *

class TestCustomEvents(unittest.TestCase):
    """Unit test for view custom events"""

    def setUp(self) -> None:
        pygame.init()
        self.event_sender=CustomEventSender()
        self.status_messages=StatusMessages()
        self.custom_event=self.event_sender.custom_event
        self.change_screen=ChangeScreenType(Screens.HOME)
        self.lobby_without_peers=Lobby(Peer("Owner"), "Lobby 1", password="password")
        self.lobby_without_password=Lobby(Peer("Owner2"), "Lobby 2")
        self.lobby_without_password.peers.add(Peer("Mario"))
        self.lobby_without_password.peers.add(Peer("Luigi"))
        self.discovered_lobby_add=LobbyType(self.lobby_without_peers, LobbyType.s_action_add)
        self.discovered_lobby_remove=LobbyType(self.lobby_without_password, LobbyType.s_action_remove)
        self.username_add=UsersType(Peer("Mario"), UsersType.s_action_add)
        self.username_remove=UsersType(Peer("Luigi"), UsersType.s_action_remove)
        self.timeout=TimeOutType()
        self.waiting_users=WaitingRoomType(2)
        self.chat_message=ChatMessageType("Mario:Hello!")
        self.role=GameRoleType("Villager", "Try not to die, vote out the werewolves")
        self.error=ErrorType("A player disconnected", "Please wait while the player re-connects")
        self.end_error=EndErrorType()
        self.end_error_next_screen=EndErrorType(Screens.HOME)
        self.dead_player=DeadPlayerType()

    def test_custom_event_serialization(self)->None:
        """A custom event serialized and deserialized should be the same"""
        self.assertEqual(self.change_screen, create_custom_event_from_dict(self.change_screen.as_dictionary()))
        self.assertEqual(self.discovered_lobby_add, create_custom_event_from_dict(self.discovered_lobby_add.as_dictionary()))
        self.assertEqual(self.discovered_lobby_remove, create_custom_event_from_dict(self.discovered_lobby_remove.as_dictionary()))
        self.assertEqual(self.username_add, create_custom_event_from_dict(self.username_add.as_dictionary()))
        self.assertEqual(self.username_remove, create_custom_event_from_dict(self.username_remove.as_dictionary()))
        self.assertEqual(self.timeout, create_custom_event_from_dict(self.timeout.as_dictionary())) #Useless, no information is passed via dictionary other than type
        self.assertEqual(self.waiting_users, create_custom_event_from_dict(self.waiting_users.as_dictionary()))
        self.assertEqual(self.chat_message, create_custom_event_from_dict(self.chat_message.as_dictionary()))
        self.assertEqual(self.role, create_custom_event_from_dict(self.role.as_dictionary()))
        self.assertEqual(self.error, create_custom_event_from_dict(self.error.as_dictionary()))
        self.assertEqual(self.end_error, create_custom_event_from_dict(self.end_error.as_dictionary()))
        self.assertEqual(self.end_error_next_screen, create_custom_event_from_dict(self.end_error_next_screen.as_dictionary()))
        self.assertEqual(self.dead_player, create_dead_player_type(self.dead_player.as_dictionary()))

    def test_custom_event_pygame(self)->None:
        """An event sent to the game loop should be parsed correctly"""
        events_received=0
        total_events=13
        self.event_sender.send_event_to_screen(self.change_screen.next_screen)
        self.event_sender.send_event_new_lobby(self.discovered_lobby_add.lobby)
        self.event_sender.send_event_removed_lobby(self.discovered_lobby_remove.lobby)
        self.event_sender.send_event_add_user(self.username_add.user)
        self.event_sender.send_event_remove_user(self.username_remove.user)
        self.event_sender.send_event_timeout()
        self.event_sender.send_event_waiting_room(self.waiting_users.number)
        self.event_sender.send_event_chat_message(self.chat_message.message)
        self.event_sender.send_event_game_role(self.role.role, self.role.role_description)
        self.event_sender.send_event_error(self.error.title, self.error.message)
        self.event_sender.send_event_end_error()
        self.event_sender.send_event_end_error(self.end_error_next_screen.next_screen)
        self.event_sender.send_event_dead_player()

        while events_received<total_events:
            for event in pygame.event.get():
                if event.type==self.custom_event:
                    e=create_custom_event_from_dict(event.dict)
                    if isinstance(e, ChangeScreenType):
                        self.assertEqual(e, self.change_screen)
                        events_received=events_received+1
                    if isinstance(e, LobbyType):
                        if e.action==LobbyType.s_action_add:
                            self.assertEqual(e, self.discovered_lobby_add)
                            self.assertEqual(e.lobby, self.lobby_without_peers)
                            events_received=events_received+1
                        else:
                            if e.action==LobbyType.s_action_remove:
                                self.assertEqual(e, self.discovered_lobby_remove)
                                self.assertEqual(e.lobby, self.lobby_without_password)
                                events_received=events_received+1
                            else:
                                raise ValueError("Lobby type can only be add or remove")
                    if isinstance(e, UsersType):
                        if e.action==UsersType.s_action_add:
                            self.assertEqual(e, self.username_add)
                            events_received=events_received+1
                        else:
                            if e.action==UsersType.s_action_remove:
                                self.assertEqual(e, self.username_remove)
                                events_received=events_received+1
                            else:
                                raise ValueError("Users type can only be add or remove")
                    if isinstance(e, TimeOutType):
                        self.assertEqual(e, self.timeout) #Useless, no information is passed via dictionary other than type
                        events_received=events_received+1
                    if isinstance(e, WaitingRoomType):
                        self.assertEqual(e, self.waiting_users) 
                        events_received=events_received+1
                    if isinstance(e, ChatMessageType):
                        self.assertEqual(e, self.chat_message) 
                        events_received=events_received+1
                    if isinstance(e, GameRoleType):
                        self.assertEqual(e, self.role) 
                        events_received=events_received+1
                    if isinstance(e, ErrorType):
                        self.assertEqual(e, self.error)
                        self.assertEqual(e.title, self.error.title)
                        self.assertEqual(e.message, self.error.message)
                        events_received=events_received+1
                    if isinstance(e, EndErrorType):
                        if e.next_screen==Screens.NONE:
                            self.assertEqual(e, self.end_error)
                            events_received=events_received+1
                        else:
                            self.assertEqual(e, self.end_error_next_screen)
                            events_received=events_received+1
                    if isinstance(e, DeadPlayerType):
                        self.assertEqual(e, self.dead_player)
                        events_received=events_received+1

        #Received all events
        self.assertEqual(events_received, total_events)

    def test_custom_event_fail(self)->None:
        """Test parsing a wrong dictionary should throw an error"""
        self.assertRaises(ValueError, create_custom_event_from_dict, {'test':'hello'}) #fails because dictionary doesn't have the expected key
        self.assertRaisesRegex(ValueError, 'EventType enums',create_custom_event_from_dict, {AbstractEventType.s_event: 'none'}) #fails because key isn't an EventType enum
        self.assertRaises(TypeError, UsersType, ("Test", "Wrong action")) #fails because action can only be add or remove
        self.assertRaises(TypeError, LobbyType, ("Lobby", "Wrong action")) #fails because action can only be add or remove

    def test_status_messages_consistency(self)->None:
        """Test checking if day and night messages are correctly constructed"""
        for i in range(1, 5):
            self.assertEqual(self.status_messages.day_count, i)
            self.assertTrue("Day "+str(i) in self.status_messages.message_day())#Message is something like ...: Day n
            self.assertTrue("Night "+str(i) in self.status_messages.message_night()) #Message is something like ...: Night n
            self.status_messages.next_day()

    def test_status_messages_win(self)->None:
        """Test checking if winning messages are correctly constructed"""
        self.assertTrue("Villagers won" in self.status_messages.villager_win())
        self.assertTrue("Werewolves won" in self.status_messages.wolf_win())
        user="Cesare"
        self.assertTrue(user+" was executed" in self.status_messages.user_executed(user))
        self.assertTrue(user+" was killed" in self.status_messages.user_killed_during_night(user))
