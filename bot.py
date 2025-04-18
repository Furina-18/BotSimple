import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from web_server import start_web  # Flask keepalive server

start_web()  # Start the web server

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Create the bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Event: When the bot is ready
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Synced {len(synced)} global slash commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# Dynamically load all cogs in /cogs folder
async def load_all_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            cog_name = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                print(f"✅ Loaded cog: {filename}")
            except Exception as e:
                print(f"❌ Failed to load cog {filename}: {e}")

# Main entry point
async def main():
    async with bot:
        await load_all_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
