import discord
from discord.ext import commands
from discord import app_commands

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket", description="Create a support ticket")
    async def ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
        }
        ticket_channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
        await ticket_channel.send(f"{interaction.user.mention}, welcome to your support ticket!")
        await interaction.response.send_message(f"🎫 Ticket created: {ticket_channel.mention}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
