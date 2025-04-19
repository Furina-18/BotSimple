import discord
from discord import app_commands
from discord.ext import commands

class ServerStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="serverstats",
        description="Show server statistics"
    )
    async def serverstats(self, interaction: discord.Interaction):
        g = interaction.guild
        embed = discord.Embed(
            title=f"Stats for {g.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Members", value=g.member_count)
        embed.add_field(name="Text Channels", value=len(g.text_channels))
        embed.add_field(name="Voice Channels", value=len(g.voice_channels))
        embed.set_thumbnail(url=g.icon.url if g.icon else discord.Embed.Empty)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ServerStats(bot))
