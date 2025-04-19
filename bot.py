import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from keep_alive import keep_alive  # if you’re pinging UptimeRobot

# 1) Load & check token
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("❌ TOKEN not found! Set TOKEN in .env or in your Render environment variables.")

# 2) Define bot & intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 3) Load cogs on startup
@bot.event
async def on_ready():
    for fn in os.listdir("./cogs"):
        if fn.endswith(".py") and fn != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{fn[:-3]}")
                print(f"✅ Loaded cog {fn}")
            except Exception as e:
                print(f"❌ Failed to load {fn}: {e}")
    print(f"▶️ Logged in as {bot.user} (ID: {bot.user.id})")

# 4) (Optional) kick off the keep‑alive server
keep_alive()

# 5) **This is what actually starts your bot**
print("⚙️ TOKEN repr:", repr(TOKEN))
print("⚙️ TOKEN length:", len(TOKEN or ""))
bot.run(TOKEN)
