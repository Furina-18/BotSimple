import discord
from discord import app_commands
from discord.ext import commands

class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="voice_lock", description="Lock your voice channel")
    async def voice_lock(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ Join a VC first.", ephemeral=True)
        ch = interaction.user.voice.channel
        overwrite = ch.overwrites_for(interaction.guild.default_role)
        overwrite.connect = False
        await ch.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"🔒 Locked {ch.name}")

    @app_commands.command(name="voice_unlock", description="Unlock your voice channel")
    async def voice_unlock(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ Join a VC first.", ephemeral=True)
        ch = interaction.user.voice.channel
        overwrite = ch.overwrites_for(interaction.guild.default_role)
        overwrite.connect = True
        await ch.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"🔓 Unlocked {ch.name}")

    @app_commands.command(name="voice_claim", description="Claim an empty voice channel")
    async def voice_claim(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ Join a VC first.", ephemeral=True)
        ch = interaction.user.voice.channel
        members = [m for m in ch.members if not m.bot]
        if len(members) == 1 and members[0] == interaction.user:
            await ch.set_permissions(interaction.user, manage_channels=True, move_members=True)
            await interaction.response.send_message(f"👑 You now control {ch.name}")
        else:
            await interaction.response.send_message("❌ Channel not empty or you’re not alone.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Voice(bot))
