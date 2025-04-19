import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import random
from typing import Literal, Optional

class Giveaway(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_giveaways: dict[int, dict] = {}

    @app_commands.command(
        name="giveaway",
        description="Start a giveaway (prize, duration, winners, optional role)"
    )
    @app_commands.describe(
        prize="What users will win",
        duration="How long it runs for",
        time_unit="Unit for duration",
        winners="Number of winners",
        required_role="Role required to enter (optional)"
    )
    async def giveaway(
        self,
        interaction: discord.Interaction,
        prize: str,
        duration: int,
        time_unit: Literal["seconds", "minutes", "hours", "days"],
        winners: int,
        required_role: Optional[discord.Role] = None
    ):
        # calculate seconds
        mult = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}
        total = duration * mult[time_unit]

        embed = discord.Embed(
            title="🎉 Giveaway!",
            description=(
                f"**Prize:** {prize}\n"
                f"**Hosted by:** {interaction.user.mention}\n"
                f"**Duration:** {duration} {time_unit}\n"
                f"**Winners:** {winners}"
                + (f"\n**Role required:** {required_role.mention}" if required_role else "")
            ),
            color=discord.Color.purple()
        )
        embed.set_footer(text="React with 🎉 to enter!")
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction("🎉")

        self.active_giveaways[msg.id] = {
            "msg": msg,
            "winners": winners,
            "role": required_role,
            "prize": prize
        }
        await interaction.response.send_message(
            f"✅ Giveaway started for **{prize}**!", ephemeral=True
        )

        await asyncio.sleep(total)
        await self.end_giveaway(msg.id)

    async def end_giveaway(self, message_id: int):
        data = self.active_giveaways.pop(message_id, None)
        if not data:
            return

        msg = await data["msg"].channel.fetch_message(message_id)
        users = [
            u for u in await msg.reactions[0].users().flatten()
            if not u.bot
        ]
        if data["role"]:
            users = [
                u for u in users
                if data["role"] in msg.guild.get_member(u.id).roles
            ]
        if len(users) < data["winners"]:
            await msg.channel.send("❌ Not enough entrants.")
            return

        winners = random.sample(users, k=data["winners"])
        mentions = ", ".join(w.mention for w in winners)
        await msg.channel.send(
            f"🎊 Congratulations {mentions}, you won **{data['prize']}**!"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Giveaway(bot))
