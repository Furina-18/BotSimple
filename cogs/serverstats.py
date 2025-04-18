import discord
from discord.ext import commands
from discord import app_commands

class ServerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serverstats", description="Show server statistics")
    async def serverstats(self, interaction: discord.Interaction):
        guild = interaction.guild
        embed = discord.Embed(title="📊 Server Stats", color=discord.Color.green())
        embed.add_field(name="Members", value=str(guild.member_count))
        embed.add_field(name="Text Channels", value=str(len(guild.text_channels)))
        embed.add_field(name="Voice Channels", value=str(len(guild.voice_channels)))
        embed.set_footer(text=f"Server: {guild.name}")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(ServerStats(bot))
