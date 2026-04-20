import asyncio

from wiredwolf.controller.controller import GameController
from wiredwolf.controller.lobbies import TcpMdnsLobbyBrowser
from wiredwolf.view.view import View

if __name__ == "__main__":
    async def main():
        my_app=View()
        controller=GameController(TcpMdnsLobbyBrowser(), my_app.event_sender)
        my_app.set_controller(controller)
        # Run the GUI update loop while yielding to the asyncio event loop
        while my_app.app_running:
            my_app.update_display()
            # give control back to asyncio so other tasks/coroutines can run
            await asyncio.sleep(0)

    asyncio.run(main())
