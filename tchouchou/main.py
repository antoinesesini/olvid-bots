import asyncio
from olvid import OlvidClient, datatypes, tools

class Bot(OlvidClient):
    async def on_message_received(self, message: datatypes.Message):
        print(f"Message received: {message.body}")

async def main():
    bot = Bot()
    tools.AutoInvitationBot()
    await bot.run_forever()

asyncio.set_event_loop(asyncio.new_event_loop())
asyncio.get_event_loop().run_until_complete(main())