import asyncio
from olvid import OlvidClient

async def main():
    client = OlvidClient()
    print((await client.identity_get()).display_name)

asyncio.set_event_loop(asyncio.new_event_loop())
asyncio.get_event_loop().run_until_complete(main())