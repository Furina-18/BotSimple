import discord
from discord.ext import commands
from discord import app_commands

class Voice(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="voice_lock", description="Lock your current voice channel.")
    async def voice_lock(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel to use this.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.connect = False
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"🔒 Locked {channel.name}.")

    @app_commands.command(name="voice_unlock", description="Unlock your current voice channel.")
    async def voice_unlock(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel to use this.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.connect = True
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"🔓 Unlocked {channel.name}.")

    @app_commands.command(name="voice_claim", description="Claim a voice channel if the owner left.")
    async def voice_claim(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel to use this.", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        members = [member for member in channel.members if not member.bot]

        if interaction.user not in members:
            await interaction.response.send_message("❌ You're not in this voice channel.", ephemeral=True)
            return

        if len(members) == 1:
            await channel.set_permissions(interaction.user, manage_channels=True, mute_members=True, move_members=True)
            await interaction.response.send_message(f"👑 You now control {channel.name}!")
        else:
            await interaction.response.send_message("❌ There are still other members in the voice channel.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Voice(bot))
