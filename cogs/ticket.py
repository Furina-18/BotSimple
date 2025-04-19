import discord
from discord import app_commands
from discord.ext import commands

class Ticket(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.category_name = "Tickets"

    @app_commands.command(name="createticket", description="Open a private support ticket")
    async def createticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        cat = discord.utils.get(guild.categories, name=self.category_name)
        if not cat:
            cat = await guild.create_category(self.category_name)
        channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}", category=cat,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )
        await interaction.response.send_message(
            f"🎫 Your ticket: {channel.mention}", ephemeral=True
        )

    @app_commands.command(name="closeticket", description="Close an existing ticket")
    async def closeticket(self, interaction: discord.Interaction):
        ch = interaction.channel
        if isinstance(ch.category, discord.CategoryChannel) and ch.category.name == self.category_name:
            await ch.delete()
        else:
            await interaction.response.send_message(
                "❌ This is not a ticket channel.", ephemeral=True
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(Ticket(bot))
