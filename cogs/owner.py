import discord, os, sys
from discord import app_commands
from discord.ext import commands

class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="shutdown", description="Shut down the bot (owner only)")
    async def shutdown(self, interaction: discord.Interaction):
        if interaction.user.id != int(os.getenv("OWNER_ID")):
            return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)
        await interaction.response.send_message("⚠️ Shutting down...")
        await self.bot.close()

    @app_commands.command(name="reload", description="Reload a cog (owner only)")
    @app_commands.describe(cog="Name of the cog to reload (e.g. music)")
    async def reload(self, interaction: discord.Interaction, cog: str):
        if interaction.user.id != int(os.getenv("OWNER_ID")):
            return await interaction.response.send_message("❌ Not authorized.", ephemeral=True)
        try:
            self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"🔄 Reloaded `{cog}`.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Reload failed: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Owner(bot))
