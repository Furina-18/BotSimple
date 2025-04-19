import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive  # your Flask keep‑alive

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("❌ Missing TOKEN in .env or environment variables.")

intents = discord.Intents.all()

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=os.getenv("APPLICATION_ID")  # optional
        )

    async def setup_hook(self):
        # 1) Load all cogs
        for filename in os.listdir("cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                path = f"cogs.{filename[:-3]}"
                try:
                    await self.load_extension(path)
                    print(f"✅ Loaded cog: {filename}")
                except Exception as e:
                    print(f"❌ Failed to load cog {filename}: {e}")

        # 2) Sync slash commands globally
        synced = await self.tree.sync()
        print(f"⚡ Synced {len(synced)} slash commands.")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"▶️ Bot is online as {bot.user} (ID: {bot.user.id})")

# start the keep‑alive webserver (Render/UptimeRobot)
keep_alive()

# finally run the bot
bot.run(TOKEN)
