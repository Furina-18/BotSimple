import os
import discord
from discord.ext import commands
from discord import app_commands
from keep_alive import keep_alive
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="ping", description="Test if bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

# Auto-load cogs
async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            await bot.load_extension(f"cogs.{filename[:-3]}")

async def main():
    async with bot:
        await load_cogs()
        keep_alive()
        await bot.start(TOKEN)

asyncio.run(main())
