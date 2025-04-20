import asyncio
from bot import bot  # Assuming your bot instance is defined in bot.py
from keep_alive import keep_alive  # If you're using a keep-alive mechanism
import wavelink

class YourBot(commands.Bot):
    async def setup_hook(self):
        try:
            await wavelink.NodePool.create_node(
                bot=self,
                host='your.lavalink.host',  # Or 127.0.0.1 if local
                port=2333,
                password='youshallnotpass',
                https=False
            )
            print("✅ Lavalink node initialized")
        except Exception as e:
            print(f"❌ Failed to init Lavalink node: {e}")
async def main():
    keep_alive()  # Start the keep-alive server if applicable
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
