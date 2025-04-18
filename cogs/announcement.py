import discord
from discord.ext import commands
from discord import app_commands

class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Send an announcement to a channel")
    async def announce(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        await channel.send(f"📢 **Announcement**:\n{message}")
        await interaction.response.send_message(f"✅ Announcement sent to {channel.mention}!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Announcement(bot))
