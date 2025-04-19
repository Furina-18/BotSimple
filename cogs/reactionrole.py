import discord
from discord import app_commands
from discord.ext import commands

class ReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="reactionrole",
        description="Create a reaction role message"
    )
    @app_commands.describe(
        channel="Channel to send message in",
        message="The embed message text",
        emoji="Emoji for the role",
        role="Role to assign"
    )
    async def reactionrole(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        emoji: str,
        role: discord.Role
    ):
        embed = discord.Embed(description=message, color=discord.Color.green())
        msg = await channel.send(embed=embed)
        await msg.add_reaction(emoji)

        def check(reaction, user):
            return reaction.message.id == msg.id and str(reaction.emoji) == emoji

        @self.bot.event
        async def on_raw_reaction_add(payload):
            if payload.message_id == msg.id and str(payload.emoji) == emoji:
                guild = self.bot.get_guild(payload.guild_id)
                member = guild.get_member(payload.user_id)
                await member.add_roles(role)

        await interaction.response.send_message("✅ Reaction role set up!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRole(bot))
