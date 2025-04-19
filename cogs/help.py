import discord
from discord import app_commands
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="help",
        description="Show this help message"
    )
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Bot Commands",
            description="Here are the available slash commands:",
            color=discord.Color.blurple()
        )
        for cmd in self.bot.tree.get_commands():
            embed.add_field(name=f"/{cmd.name}", value=cmd.description or "No description", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
