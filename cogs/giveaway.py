"""
Giveaway functionality for the Discord bot.
Handles commands for creating and managing giveaways.
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import datetime
import logging
import random
import time
from typing import Optional, List
import random
from datetime import datetime, timedelta

import config
import utils
from database import db

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}

    @app_commands.command(name="giveaway", description="Start a giveaway")
    @app_commands.describe(duration="Duration (e.g. 1m, 1h, 1d)", winners="Number of winners", prize="Prize description")
    async def giveaway(self, interaction: discord.Interaction, duration: str, winners: int, prize: str):
        await interaction.response.defer()

        seconds = self.parse_duration(duration)
        if seconds is None:
            await interaction.followup.send("❌ Invalid duration. Use formats like 1m, 2h, 3d.")
            return

        end_time = datetime.utcnow() + timedelta(seconds=seconds)
        embed = discord.Embed(title="🎉 Giveaway! 🎉", description=f"**Prize:** {prize}\nReact with 🎉 to enter!\n**Winners:** {winners}\nEnds <t:{int(end_time.timestamp())}:R>", color=discord.Color.blurple())
        embed.set_footer(text="Started by " + str(interaction.user))

        message = await interaction.followup.send(embed=embed)
        await message.add_reaction("🎉")

        self.active_giveaways[message.id] = {
            "message": message,
            "channel": message.channel,
            "end_time": end_time,
            "winners": winners,
            "prize": prize
        }

        self.bot.loop.create_task(self.wait_and_pick_winners(message.id))

    async def wait_and_pick_winners(self, message_id):
        data = self.active_giveaways[message_id]
        wait_time = (data["end_time"] - datetime.utcnow()).total_seconds()
        await asyncio.sleep(max(wait_time, 0))

        message = await data["channel"].fetch_message(message_id)
        users = await message.reactions[0].users().flatten()
        users = [u for u in users if not u.bot]

        if not users:
            result = "😢 No one entered the giveaway."
        else:
            winners = random.sample(users, min(len(users), data["winners"]))
            result = "🎉 Congratulations to: " + ", ".join(w.mention for w in winners) + f"! You won **{data['prize']}**!"

        embed = message.embeds[0]
        embed.title += " - ENDED"
        await message.edit(embed=embed)
        await data["channel"].send(result)
        del self.active_giveaways[message_id]

    def parse_duration(self, time_str):
        try:
            unit = time_str[-1]
            amount = int(time_str[:-1])
            if unit == 's': return amount
            elif unit == 'm': return amount * 60
            elif unit == 'h': return amount * 3600
            elif unit == 'd': return amount * 86400
        except:
            return None

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
