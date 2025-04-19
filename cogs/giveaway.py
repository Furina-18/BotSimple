import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
from typing import Literal, Optional

class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_giveaways = {}

    @app_commands.command(name="giveaway", description="Start a giveaway with time, winners, and optional role requirement.")
    @app_commands.describe(
        prize="What is the giveaway prize?",
        duration="How long should the giveaway last?",
        time_unit="Time unit for the duration (seconds, minutes, hours, days)",
        winners="How many winners?",
        required_role="Optional role required to enter"
    )
    async def giveaway(
        self,
        interaction: discord.Interaction,
        prize: str,
        duration: int,
        time_unit: Literal["seconds", "minutes", "hours", "days"],
        winners: int,
        required_role: Optional[discord.Role] = None,
    ):
        multiplier = {
            "seconds": 1,
            "minutes": 60,
            "hours": 3600,
            "days": 86400
        }
        total_seconds = duration * multiplier[time_unit]

        embed = discord.Embed(
            title="🎉 Giveaway!",
            description=f"**Prize:** {prize}\n**Hosted by:** {interaction.user.mention}\n"
                        f"**Time:** {duration} {time_unit}\n"
                        f"**Winners:** {winners}" +
                        (f"\n**Required Role:** {required_role.mention}" if required_role else ""),
            color=discord.Color.gold()
        )
        embed.set_footer(text="React with 🎉 to enter!")

        message = await interaction.channel.send(embed=embed)
        await message.add_reaction("🎉")

        self.active_giveaways[message.id] = {
            "prize": prize,
            "winners": winners,
            "message": message,
            "channel": interaction.channel,
            "required_role": required_role,
            "author": interaction.user
        }

        await interaction.response.send_message(f"✅ Giveaway started for **{prize}** lasting {duration} {time_unit}!")

        await asyncio.sleep(total_seconds)
        await self.end_giveaway(message.id)

    async def end_giveaway(self, message_id):
        data = self.active_giveaways.get(message_id)
        if not data:
            return

        message = data["message"]
        channel = data["channel"]
        winners_count = data["winners"]
        required_role = data["required_role"]

        try:
            message = await channel.fetch_message(message.id)
        except Exception:
            return

        users = await message.reactions[0].users().flatten()
        users = [u for u in users if not u.bot]

        if required_role:
            users = [
                u for u in users
                if isinstance(channel, discord.TextChannel) and
                channel.guild.get_member(u.id) and
                required_role in channel.guild.get_member(u.id).roles
            ]

        if len(users) < winners_count:
            await channel.send("❌ Not enough participants to draw winners.")
        else:
            winners = random.sample(users, winners_count)
            winner_mentions = ", ".join(w.mention for w in winners)
            await channel.send(f"🎉 Congratulations {winner_mentions}! You won **{data['prize']}**!")

        del self.active_giveaways[message_id]


async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
