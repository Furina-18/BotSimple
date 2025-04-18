import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available slash commands")
    async def help(self, interaction: discord.Interaction):
        """List every slash command in an embed."""
        # Gather all global commands
        cmds = sorted(self.bot.tree.get_commands(), key=lambda c: c.name)
        embed = discord.Embed(
            title="📜 Available Commands",
            color=discord.Color.blurple()
        )
        for cmd in cmds:
            # skip hidden or test‐only commands if you like:
            # if cmd._is_subcommand: continue
            embed.add_field(
                name=f"/{cmd.name}",
                value=cmd.description or "No description",
                inline=False
            )
        # Send as an ephemeral response so only the invoker sees it
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))
