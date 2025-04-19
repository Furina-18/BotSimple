import asyncio
from bot import bot  # Assuming your bot instance is defined in bot.py
from keep_alive import keep_alive  # If you're using a keep-alive mechanism

async def main():
    keep_alive()  # Start the keep-alive server if applicable
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())
