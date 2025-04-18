"""
Moderation commands for the Discord bot.
Handles moderation actions like kick, ban, timeout, and warning management.
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import timedelta

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="timeout", description="Timeout a member for a specified duration")
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration in minutes",
        reason="Reason for the timeout"
    )
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: int,
        reason: str = "No reason provided"
    ):
        try:
            await member.timeout(timedelta(minutes=duration), reason=reason)
            await interaction.response.send_message(
                f"🔇 {member.mention} has been timed out for {duration} minutes. Reason: {reason}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to timeout {member.mention}. Error: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(
        member="The member to ban",
        reason="Reason for the ban"
    )
    async def ban(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(
                f"🔨 {member.mention} has been banned. Reason: {reason}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to ban {member.mention}. Error: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(
        member="The member to warn",
        reason="Reason for the warning"
    )
    async def warn(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason provided"
    ):
        try:
            await interaction.response.send_message(
                f"⚠️ {member.mention} has been warned. Reason: {reason}",
                ephemeral=True
            )
            # Optional: Log the warning to a channel or save to database
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Failed to warn {member.mention}. Error: {str(e)}",
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
