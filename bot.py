import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive  # Flask ping webserver

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            application_id=None  # Optional if already in .env
        )

    async def setup_hook(self):
        print("🛠️ Running setup_hook...")

        # Load all cogs from the cogs folder
        for filename in os.listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                cog_path = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(cog_path)
                    print(f"✅ Loaded cog: {filename}")
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"⚡ Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"❌ Slash command sync failed: {e}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Bot is ready: {bot.user} (ID: {bot.user.id})")

# Start keep-alive server
keep_alive()

# Run the bot
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ No TOKEN found in .env or environment!")
