import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
from db import db_manager

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="giveaway", description="Start a giveaway")
    async def giveaway(self, interaction: discord.Interaction, duration: int, prize: str):
        await interaction.response.send_message(f"🎉 Giveaway started for **{prize}**! Ending in {duration} seconds...")
        msg = await interaction.channel.send("React with 🎉 to enter!")
        await msg.add_reaction("🎉")

        await asyncio.sleep(duration)

        msg = await interaction.channel.fetch_message(msg.id)
        users = await msg.reactions[0].users().flatten()
        users = [u for u in users if not u.bot]

        if not users:
            await interaction.followup.send("❌ No one joined the giveaway.")
        else:
            winner = random.choice(users)
            await interaction.followup.send(f"🎊 Congrats {winner.mention}! You won **{prize}**!")

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
