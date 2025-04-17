"""
Reaction role functionality for the Discord bot.
Handles commands for creating and managing reaction roles.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
from typing import Optional, List, Dict, Union

import config
import utils
from database import db

logger = logging.getLogger(__name__)

class ReactionRole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("ReactionRole cog loaded")
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Handle reaction add events for reaction roles."""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
            
        # Check if this is a reaction role
        reaction_roles = db.get_reaction_roles(payload.guild_id, payload.message_id)
        
        for reaction_role in reaction_roles:
            # Check if the emoji matches
            if self._emoji_matches(str(payload.emoji), reaction_role["emoji"]):
                # Get the guild and member
                guild = self.bot.get_guild(payload.guild_id)
                if not guild:
                    continue
                    
                member = guild.get_member(payload.user_id)
                if not member:
                    continue
                    
                # Get the role
                role = guild.get_role(reaction_role["role_id"])
                if not role:
                    continue
                    
                # Add the role to the member
                try:
                    await member.add_roles(role, reason="Reaction Role")
                    logger.info(f"Added role {role.name} to {member.display_name} in {guild.name}")
                except discord.Forbidden:
                    logger.error(f"Failed to add role {role.name} to {member.display_name} in {guild.name}: Missing permissions")
                except discord.HTTPException as e:
                    logger.error(f"Failed to add role {role.name} to {member.display_name} in {guild.name}: {e}")
                    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Handle reaction remove events for reaction roles."""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
            
        # Check if this is a reaction role
        reaction_roles = db.get_reaction_roles(payload.guild_id, payload.message_id)
        
        for reaction_role in reaction_roles:
            # Check if the emoji matches
            if self._emoji_matches(str(payload.emoji), reaction_role["emoji"]):
                # Get the guild and member
                guild = self.bot.get_guild(payload.guild_id)
                if not guild:
                    continue
                    
                member = guild.get_member(payload.user_id)
                if not member:
                    continue
                    
                # Get the role
                role = guild.get_role(reaction_role["role_id"])
                if not role:
                    continue
                    
                # Remove the role from the member
                try:
                    await member.remove_roles(role, reason="Reaction Role")
                    logger.info(f"Removed role {role.name} from {member.display_name} in {guild.name}")
                except discord.Forbidden:
                    logger.error(f"Failed to remove role {role.name} from {member.display_name} in {guild.name}: Missing permissions")
                except discord.HTTPException as e:
                    logger.error(f"Failed to remove role {role.name} from {member.display_name} in {guild.name}: {e}")
                    
    def _emoji_matches(self, emoji1, emoji2):
        """Check if two emoji strings match, handling custom emoji IDs."""
        # For custom emojis, compare the ID
        if emoji1.isdigit() and emoji2.isdigit():
            return emoji1 == emoji2
            
        # If one is a custom emoji and contains the ID of the other
        if emoji1.isdigit() and emoji2.count(':') == 2:
            emoji_id = emoji2.split(':')[-1].rstrip('>')
            return emoji1 == emoji_id
            
        if emoji2.isdigit() and emoji1.count(':') == 2:
            emoji_id = emoji1.split(':')[-1].rstrip('>')
            return emoji2 == emoji_id
            
        # For Unicode emojis, direct comparison
        return emoji1 == emoji2
        
    # Create reaction role command
    @app_commands.command(name="reactionrole", description="Create a reaction role message")
    @app_commands.describe(
        channel="The channel to send the reaction role message to",
        title="The title for the reaction role message",
        description="The description for the reaction role message"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def reactionrole_command(self, interaction: discord.Interaction,
                                  channel: discord.TextChannel,
                                  title: str,
                                  description: str):
        """Create a new reaction role message."""
        # Check bot permissions
        if not channel.permissions_for(interaction.guild.me).send_messages:
            return await interaction.response.send_message(f"I don't have permission to send messages in {channel.mention}", ephemeral=True)
            
        if not channel.permissions_for(interaction.guild.me).add_reactions:
            return await interaction.response.send_message(f"I don't have permission to add reactions in {channel.mention}", ephemeral=True)
            
        if not interaction.guild.me.guild_permissions.manage_roles:
            return await interaction.response.send_message("I don't have the Manage Roles permission, which is required for reaction roles.", ephemeral=True)
            
        # Create a modal for adding roles
        await interaction.response.send_message("Creating reaction role message. Please add roles one by one using the command below.", ephemeral=True)
        
        # Create and send the reaction role embed
        embed = await utils.create_embed(
            title=title,
            description=description,
            color=config.EMBED_COLOR,
            footer={"text": "React to get a role!"}
        )
        
        reaction_message = await channel.send(embed=embed)
        
        # Store the message ID for later use
        await interaction.followup.send(
            f"Reaction role message created in {channel.mention}. Use `/addrole {reaction_message.id} @role :emoji:` to add roles.", 
            ephemeral=True
        )
        
    # Add role to reaction role message
    @app_commands.command(name="addrole", description="Add a role to a reaction role message")
    @app_commands.describe(
        message_id="The ID of the reaction role message",
        role="The role to add",
        emoji="The emoji to use for this role"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def addrole_command(self, interaction: discord.Interaction,
                             message_id: str,
                             role: discord.Role,
                             emoji: str):
        """Add a role to an existing reaction role message."""
        # Convert message ID to int
        try:
            message_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("Invalid message ID. Please provide a valid numeric ID.", ephemeral=True)
            
        # Check if the role is manageable
        if role.position >= interaction.guild.me.top_role.position:
            return await interaction.response.send_message("I can't assign this role because it's higher than or equal to my highest role.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        # Find the message
        message = None
        for channel in interaction.guild.text_channels:
            try:
                message = await channel.fetch_message(message_id)
                if message.author.id == self.bot.user.id:
                    break
                message = None
            except:
                continue
                
        if not message:
            return await interaction.followup.send("Message not found. Please provide a valid message ID from a message sent by the bot.", ephemeral=True)
            
        # Check if the emoji is valid
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            return await interaction.followup.send("Invalid emoji. Please provide a valid emoji that the bot can use.", ephemeral=True)
            
        # Store the reaction role in the database
        emoji_str = str(emoji)
        db.add_reaction_role(interaction.guild.id, message.channel.id, message_id, emoji_str, role.id)
        
        # Update the reaction role message with the new role
        if message.embeds:
            embed = message.embeds[0]
            
            # Create a new embed with the updated information
            new_embed = discord.Embed(
                title=embed.title,
                description=embed.description,
                color=embed.color
            )
            
            # Copy existing fields
            for field in embed.fields:
                new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                
            # Add the new role
            new_embed.add_field(name=f"{emoji} {role.name}", value=f"React with {emoji} to get the {role.mention} role", inline=False)
            
            # Set footer
            new_embed.set_footer(text="React to get a role!")
            
            await message.edit(embed=new_embed)
            
        await interaction.followup.send(f"Added {role.mention} with emoji {emoji} to the reaction role message.", ephemeral=True)
        
    # Remove role from reaction role message
    @app_commands.command(name="removerole", description="Remove a role from a reaction role message")
    @app_commands.describe(
        message_id="The ID of the reaction role message",
        role="The role to remove"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def removerole_command(self, interaction: discord.Interaction,
                               message_id: str,
                               role: discord.Role):
        """Remove a role from an existing reaction role message."""
        # Convert message ID to int
        try:
            message_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("Invalid message ID. Please provide a valid numeric ID.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        # Find the message
        message = None
        for channel in interaction.guild.text_channels:
            try:
                message = await channel.fetch_message(message_id)
                if message.author.id == self.bot.user.id:
                    break
                message = None
            except:
                continue
                
        if not message:
            return await interaction.followup.send("Message not found. Please provide a valid message ID from a message sent by the bot.", ephemeral=True)
            
        # Find the reaction role in the database
        reaction_roles = db.get_reaction_roles(interaction.guild.id, message_id)
        
        target_role = None
        target_emoji = None
        for reaction_role in reaction_roles:
            if reaction_role["role_id"] == role.id:
                target_role = reaction_role
                target_emoji = reaction_role["emoji"]
                break
                
        if not target_role:
            return await interaction.followup.send(f"Role {role.mention} not found in the reaction role message.", ephemeral=True)
            
        # Remove the reaction role from the database
        db.remove_reaction_role(role.id, message_id)
        
        # Update the reaction role message to remove the role
        if message.embeds:
            embed = message.embeds[0]
            
            # Create a new embed with the updated information
            new_embed = discord.Embed(
                title=embed.title,
                description=embed.description,
                color=embed.color
            )
            
            # Copy existing fields, excluding the removed role
            for field in embed.fields:
                if not (field.name.endswith(role.name) or role.mention in field.value):
                    new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
                    
            # Set footer
            if new_embed.fields:
                new_embed.set_footer(text="React to get a role!")
            else:
                new_embed.set_footer(text="No roles available")
                
            await message.edit(embed=new_embed)
            
        # Remove the reaction from the message
        try:
            for reaction in message.reactions:
                if str(reaction.emoji) == target_emoji:
                    await reaction.clear()
                    break
        except:
            pass
            
        await interaction.followup.send(f"Removed {role.mention} from the reaction role message.", ephemeral=True)
        
    # List reaction roles command
    @app_commands.command(name="listroles", description="List all reaction roles in the server")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def listroles_command(self, interaction: discord.Interaction):
        """List all reaction roles in the server."""
        await interaction.response.defer(ephemeral=True)
        
        # Get all reaction roles for this guild
        reaction_roles = db.get_reaction_roles(interaction.guild.id)
        
        if not reaction_roles:
            return await interaction.followup.send("There are no reaction roles set up in this server.", ephemeral=True)
            
        # Group by message ID
        message_groups = {}
        for rr in reaction_roles:
            msg_id = rr["message_id"]
            if msg_id not in message_groups:
                message_groups[msg_id] = []
            message_groups[msg_id].append(rr)
            
        # Create an embed for each message
        embeds = []
        for msg_id, roles in message_groups.items():
            channel_id = roles[0]["channel_id"]
            channel = interaction.guild.get_channel(channel_id)
            channel_mention = channel.mention if channel else "Unknown Channel"
            
            embed = await utils.create_embed(
                title=f"Reaction Roles for Message {msg_id}",
                description=f"Channel: {channel_mention}",
                color=config.EMBED_COLOR
            )
            
            for role_data in roles:
                role = interaction.guild.get_role(role_data["role_id"])
                role_mention = role.mention if role else f"Unknown Role ({role_data['role_id']})"
                
                embed.add_field(
                    name=f"Emoji: {role_data['emoji']}",
                    value=f"Role: {role_mention}",
                    inline=False
                )
                
            embeds.append(embed)
            
        # Send the embeds
        if len(embeds) == 1:
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
        else:
            # Send the first embed
            await interaction.followup.send(embed=embeds[0], ephemeral=True)
            
            # Send the rest as separate messages
            for embed in embeds[1:]:
                await interaction.followup.send(embed=embed, ephemeral=True)

    # Error handlers
    @reactionrole_command.error
    @addrole_command.error
    @removerole_command.error
    @listroles_command.error
    async def reactionrole_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in reaction role command: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ReactionRole(bot))
