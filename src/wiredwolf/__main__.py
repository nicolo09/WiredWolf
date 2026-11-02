import argparse
import asyncio
import sys

from wiredwolf.controller.connections.connections import (
    FixedIPv4TCPConnectionSuite,
    TCPConnectionSuite,
)
from wiredwolf.controller.controller import GameController
from wiredwolf.view.view import View

if __name__ == "__main__":

    async def main():

        my_app = View()

        args = sys.argv[1:]
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "-a", "--address", help="Fixed local bind address", required=False
        )
        args = parser.parse_args()
        if args.address is None:
            controller = GameController(TCPConnectionSuite(), my_app.event_sender)
        else:
            controller = GameController(
                FixedIPv4TCPConnectionSuite(args.address), my_app.event_sender
                )

        my_app.set_controller(controller)
        # Run the GUI update loop while yielding to the asyncio event loop
        while my_app.app_running:
            my_app.update_display()
            # give control back to asyncio so other tasks/coroutines can run
            await asyncio.sleep(0)

    asyncio.run(main())
