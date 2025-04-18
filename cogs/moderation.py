import discord
from discord import app_commands
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ban", description="Ban a member")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"{member} has been banned. Reason: {reason}")

    @app_commands.command(name="timeout", description="Timeout a member")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
        await member.timeout(duration=discord.utils.utcnow() + discord.timedelta(seconds=duration))
        await interaction.response.send_message(f"{member} has been timed out for {duration} seconds. Reason: {reason}")

    @app_commands.command(name="warn", description="Warn a member")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await interaction.response.send_message(f"{member.mention} has been warned. Reason: {reason}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
