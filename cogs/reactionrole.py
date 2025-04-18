import discord
from discord.ext import commands
from discord import app_commands
from db import db_manager

class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_id = None
        self.emoji_role_map = {}

    @app_commands.command(name="reactionrole", description="Set up a reaction role")
    async def reactionrole(self, interaction: discord.Interaction, role: discord.Role, emoji: str, message: str):
        embed = discord.Embed(description=message)
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction(emoji)

        self.message_id = msg.id
        self.emoji_role_map[emoji] = role.id

        await interaction.response.send_message("✅ Reaction role set up!", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id == self.message_id:
            guild = self.bot.get_guild(payload.guild_id)
            role_id = self.emoji_role_map.get(str(payload.emoji))
            if role_id:
                role = guild.get_role(role_id)
                member = guild.get_member(payload.user_id)
                await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.message_id == self.message_id:
            guild = self.bot.get_guild(payload.guild_id)
            role_id = self.emoji_role_map.get(str(payload.emoji))
            if role_id:
                role = guild.get_role(role_id)
                member = guild.get_member(payload.user_id)
                await member.remove_roles(role)

async def setup(bot):
    await bot.add_cog(ReactionRole(bot))
