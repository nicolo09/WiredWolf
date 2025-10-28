import asyncio


def hello_world():
    print("Hello, world!")

async def pappero():
    print('hello')
    await asyncio.sleep(1)
    print('world')

async def main():
    task1 = asyncio.create_task(
        pappero())

    task2 = asyncio.create_task(
        pappero())
    
    await task1
    await task2


if __name__ == "__main__":
    asyncio.run(main())