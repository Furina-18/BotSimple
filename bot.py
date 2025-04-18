import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from web_server import start_web  # <- Adjust this to your file name (no .py)

start_web()  # Start Flask server to keep the bot alive

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

# Bot intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Define the bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Event when the bot is ready
@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Synced {len(synced)} global slash commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

# Load all cogs dynamically from the cogs folder
async def load_all_cogs():
    for fn in os.listdir("./cogs"):
        if fn.endswith(".py") and not fn.startswith("_"):
                await bot.load_extension(cog_name)
                print(f"✅ Loaded cog: {filename}")
            except Exception as e:
                print(f"❌ Failed to load cog {filename}: {e}")

# Start the bot
async def main():
    async with bot:
        await load_all_cogs()
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
