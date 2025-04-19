import discord
from discord import app_commands
from discord.ext import commands

class Announcement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="announce",
        description="Send an announcement to a channel"
    )
    @app_commands.describe(
        channel="The channel to announce in",
        message="The announcement text"
    )
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str
    ):
        await channel.send(f"**📢 Announcement**:\n{message}")
        await interaction.response.send_message(
            f"✅ Announcement sent to {channel.mention}!", ephemeral=True
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(Announcement(bot))
