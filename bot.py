import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from dotenv import load_dotenv
from db import DatabaseManager  # Make sure this file exists and is correct
import logging
import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return 'Discord bot is running!'

def run_web():
    port = int(os.environ.get("PORT", 8080))  # Required by Render
    app.run(host='0.0.0.0', port=port)

# Start the web server in a separate thread BEFORE starting the bot
threading.Thread(target=run_web).start()
# Load environment variables
load_dotenv()
# Then run your bot
if __name__ == "__main__":
    import asyncio

    async def main():
        try:
            await bot.start(os.getenv("TOKEN"))
        except Exception as e:
            print(f"Error while running bot: {e}")

    asyncio.run(main())

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            application_id=os.getenv("APPLICATION_ID")  # Optional
        )
        self.db: DatabaseManager | None = None

    async def setup_hook(self):
        await self.init_db()
        await self.load_all_cogs()
        await self.tree.sync()
        print("Slash commands synced.")

    async def init_db(self):
        os.makedirs("data", exist_ok=True)
        self.db = DatabaseManager("data/bot_data.db")
        await self.db.setup()

    async def load_all_cogs(self):
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"Loaded cog: {filename}")
                except Exception as e:
                    print(f"Failed to load cog {filename}: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print("Bot is ready!")

bot = MyBot()

# Optional basic test command
@bot.tree.command(name="ping", description="Check if the bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

if __name__ == "__main__":
    if TOKEN is None:
        raise ValueError("TOKEN not found in environment variables.")
