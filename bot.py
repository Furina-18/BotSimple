import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive
import wavelink

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        print("🛠️ Running setup_hook...")
        for filename in os.listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ Loaded cog: {filename}")
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")
        try:
            synced = await self.tree.sync()
            print(f"⚡ Synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"❌ Slash command sync failed: {e}")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"✅ Bot is ready: {bot.user} (ID: {bot.user.id})")
@bot.event
async def on_connect():
    # Connect to Lavalink node
    await wavelink.NodePool.create_node(bot=bot,
                                        host='localhost',
                                        port=2333,
                                        password='youshallnotpass',
                                        https=False)
    
keep_alive()

bot.run(TOKEN)
