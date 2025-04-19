import discord
from discord import app_commands
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member.")
    @app_commands.describe(member="Member to kick", reason="Reason for kick")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ You lack permission.", ephemeral=True)
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 Kicked {member.mention}.")

    @app_commands.command(name="ban", description="Ban a member.")
    @app_commands.describe(member="Member to ban", reason="Reason for ban")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ You lack permission.", ephemeral=True)
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 Banned {member.mention}.")

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.describe(member="Member to timeout", minutes="Length in minutes", reason="Reason")
    async def timeout(
        self, interaction: discord.Interaction,
        member: discord.Member, minutes: int, reason: str = "No reason"
    ):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ You lack permission.", ephemeral=True)
        await member.timeout(discord.utils.utcnow() + discord.timedelta(minutes=minutes), reason=reason)
        await interaction.response.send_message(f"⏱️ Timed out {member.mention} for {minutes} min.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
