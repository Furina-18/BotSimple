import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive  # optional, for uptime robot pings

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded: {filename}")
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")

async def start_bot():
    await load_cogs()
    await bot.start(os.getenv("TOKEN"))

# Web ping for UptimeRobot (if you're using it)
keep_alive()

# Use this for Render: prevents crash when already in an event loop
try:
    asyncio.run(start_bot())
except RuntimeError:
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(start_bot())
