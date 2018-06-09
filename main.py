import asyncio
import aiohttp


from runner import Runner


async def coroutine(session):
    async with session.get('http://example.com') as response:
        data = await response.content.read(1024)
        return response.status == 200


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    runner = Runner(20, coroutine, duration=20, loop=loop)
    result = runner.run()
    print(str(result))