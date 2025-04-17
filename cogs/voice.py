"""
Voice channel functionality for the Discord bot.
Handles commands for creating and managing voice channels.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import logging
from typing import Optional, Dict

import config
import utils
from database import db

logger = logging.getLogger(__name__)

class Voice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_channels = {}  # guild_id -> {channel_id: owner_id}
        self.channel_owners = {}  # channel_id -> user_id
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Voice cog loaded")
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Handle dynamic voice channel creation and deletion."""
        guild = member.guild
        
        # Check if the guild has voice channel settings
        settings = db.get_server_settings(guild.id)
        voice_settings = settings.get('settings', {}).get('voice_channels', {})
        
        create_channel_id = voice_settings.get('create_channel_id')
        voice_category_id = voice_settings.get('voice_category_id')
        
        # Check if user joined the "create channel" voice channel
        if create_channel_id and after.channel and after.channel.id == create_channel_id:
            # Create a new voice channel
            if voice_category_id:
                category = guild.get_channel(voice_category_id)
            else:
                category = after.channel.category
                
            # Create a name for the channel
            channel_name = f"{member.display_name}'s Channel"
            
            # Set up permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(
                    manage_channels=True,
                    move_members=True,
                    mute_members=True,
                    deafen_members=True
                )
            }
            
            try:
                # Create the channel
                new_channel = await guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites
                )
                
                # Move the user to the new channel
                await member.move_to(new_channel)
                
                # Store the channel as temporary
                if guild.id not in self.temp_channels:
                    self.temp_channels[guild.id] = {}
                    
                self.temp_channels[guild.id][new_channel.id] = member.id
                self.channel_owners[new_channel.id] = member.id
                
                logger.info(f"Created temporary voice channel '{channel_name}' for {member.display_name} in {guild.name}")
                
            except discord.Forbidden:
                logger.error(f"Failed to create voice channel in {guild.name}: Missing permissions")
            except discord.HTTPException as e:
                logger.error(f"Failed to create voice channel in {guild.name}: {e}")
                
        # Check if a user left a temporary voice channel
        if before.channel and guild.id in self.temp_channels and before.channel.id in self.temp_channels[guild.id]:
            # If the channel is empty, delete it
            if len(before.channel.members) == 0:
                try:
                    await before.channel.delete(reason="Temporary voice channel is empty")
                    
                    # Remove the channel from storage
                    self.temp_channels[guild.id].pop(before.channel.id, None)
                    self.channel_owners.pop(before.channel.id, None)
                    
                    if not self.temp_channels[guild.id]:
                        self.temp_channels.pop(guild.id, None)
                        
                    logger.info(f"Deleted empty temporary voice channel '{before.channel.name}' in {guild.name}")
                    
                except discord.Forbidden:
                    logger.error(f"Failed to delete voice channel in {guild.name}: Missing permissions")
                except discord.HTTPException as e:
                    logger.error(f"Failed to delete voice channel in {guild.name}: {e}")
                    
    # Setup voice channels command
    @app_commands.command(name="voicesetup", description="Set up dynamic voice channels")
    @app_commands.describe(
        category="The category for voice channels",
        create_channel_name="The name for the channel that creates new voice channels when joined"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def voicesetup_command(self, interaction: discord.Interaction,
                                category: discord.CategoryChannel,
                                create_channel_name: str = "➕ Create Voice Channel"):
        """Set up dynamic voice channels."""
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create the "create channel" voice channel
            create_channel = await interaction.guild.create_voice_channel(
                name=create_channel_name,
                category=category
            )
            
            # Store the settings
            settings = db.get_server_settings(interaction.guild.id)
            if not settings.get('settings'):
                settings['settings'] = {}
                
            if not settings['settings'].get('voice_channels'):
                settings['settings']['voice_channels'] = {}
                
            settings['settings']['voice_channels']['create_channel_id'] = create_channel.id
            settings['settings']['voice_channels']['voice_category_id'] = category.id
            
            db.update_server_settings(interaction.guild.id, settings)
            
            # Send confirmation
            await interaction.followup.send(
                f"Voice channels setup complete. Users who join {create_channel.mention} will get their own voice channel.",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to create voice channels.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to setup voice channels: {e}", ephemeral=True)
            
    # Voice channel commands
    @app_commands.command(name="voicelock", description="Lock your voice channel so no one can join")
    async def voicelock_command(self, interaction: discord.Interaction):
        """Lock your voice channel so no one can join."""
        # Check if the user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
            
        # Check if it's their temporary channel
        channel = interaction.user.voice.channel
        if channel.id not in self.channel_owners or self.channel_owners[channel.id] != interaction.user.id:
            return await interaction.response.send_message("You can only lock voice channels that you own.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer()
        
        try:
            # Update the permissions
            await channel.set_permissions(interaction.guild.default_role, connect=False)
            
            # Send confirmation
            await interaction.followup.send(f"Voice channel {channel.name} is now locked.")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to modify channel permissions.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to lock voice channel: {e}", ephemeral=True)
            
    @app_commands.command(name="voiceunlock", description="Unlock your voice channel so anyone can join")
    async def voiceunlock_command(self, interaction: discord.Interaction):
        """Unlock your voice channel so anyone can join."""
        # Check if the user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
            
        # Check if it's their temporary channel
        channel = interaction.user.voice.channel
        if channel.id not in self.channel_owners or self.channel_owners[channel.id] != interaction.user.id:
            return await interaction.response.send_message("You can only unlock voice channels that you own.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer()
        
        try:
            # Update the permissions
            await channel.set_permissions(interaction.guild.default_role, connect=True)
            
            # Send confirmation
            await interaction.followup.send(f"Voice channel {channel.name} is now unlocked.")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to modify channel permissions.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to unlock voice channel: {e}", ephemeral=True)
            
    @app_commands.command(name="voicename", description="Change the name of your voice channel")
    @app_commands.describe(
        name="The new name for your voice channel"
    )
    async def voicename_command(self, interaction: discord.Interaction, name: str):
        """Change the name of your voice channel."""
        # Check if the user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
            
        # Check if it's their temporary channel
        channel = interaction.user.voice.channel
        if channel.id not in self.channel_owners or self.channel_owners[channel.id] != interaction.user.id:
            return await interaction.response.send_message("You can only rename voice channels that you own.", ephemeral=True)
            
        # Check name length
        if len(name) < 1 or len(name) > 100:
            return await interaction.response.send_message("Channel name must be between 1 and 100 characters.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer()
        
        try:
            # Update the name
            await channel.edit(name=name)
            
            # Send confirmation
            await interaction.followup.send(f"Voice channel renamed to {name}.")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to modify the channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to rename voice channel: {e}", ephemeral=True)
            
    @app_commands.command(name="voicelimit", description="Set the user limit for your voice channel")
    @app_commands.describe(
        limit="The maximum number of users (0 for unlimited)"
    )
    async def voicelimit_command(self, interaction: discord.Interaction, limit: int):
        """Set the user limit for your voice channel."""
        # Check if the user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
            
        # Check if it's their temporary channel
        channel = interaction.user.voice.channel
        if channel.id not in self.channel_owners or self.channel_owners[channel.id] != interaction.user.id:
            return await interaction.response.send_message("You can only set the limit for voice channels that you own.", ephemeral=True)
            
        # Check limit
        if limit < 0 or limit > 99:
            return await interaction.response.send_message("User limit must be between 0 and 99 (0 means unlimited).", ephemeral=True)
            
        # Defer response
        await interaction.response.defer()
        
        try:
            # Update the limit
            await channel.edit(user_limit=limit)
            
            # Send confirmation
            if limit == 0:
                await interaction.followup.send(f"Voice channel {channel.name} now has no user limit.")
            else:
                await interaction.followup.send(f"Voice channel {channel.name} now has a limit of {limit} users.")
                
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to modify the channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to set voice channel limit: {e}", ephemeral=True)
            
    @app_commands.command(name="voicekick", description="Kick a user from your voice channel")
    @app_commands.describe(
        user="The user to kick from your voice channel"
    )
    async def voicekick_command(self, interaction: discord.Interaction, user: discord.Member):
        """Kick a user from your voice channel."""
        # Check if the user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
            
        # Check if it's their temporary channel
        channel = interaction.user.voice.channel
        if channel.id not in self.channel_owners or self.channel_owners[channel.id] != interaction.user.id:
            return await interaction.response.send_message("You can only kick users from voice channels that you own.", ephemeral=True)
            
        # Check if the target user is in the same voice channel
        if not user.voice or user.voice.channel != channel:
            return await interaction.response.send_message(f"{user.display_name} is not in your voice channel.", ephemeral=True)
            
        # Cannot kick yourself
        if user.id == interaction.user.id:
            return await interaction.response.send_message("You cannot kick yourself from your own channel.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer()
        
        try:
            # Kick the user (move them to None disconnects them)
            await user.move_to(None)
            
            # Send confirmation
            await interaction.followup.send(f"{user.mention} has been kicked from your voice channel.")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to move members.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to kick user from voice channel: {e}", ephemeral=True)
            
    @app_commands.command(name="voiceclaim", description="Claim ownership of a voice channel if the owner left")
    async def voiceclaim_command(self, interaction: discord.Interaction):
        """Claim ownership of a voice channel if the owner left."""
        # Check if the user is in a voice channel
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.", ephemeral=True)
            
        channel = interaction.user.voice.channel
        guild_id = interaction.guild.id
        
        # Check if it's a temporary channel
        if guild_id not in self.temp_channels or channel.id not in self.temp_channels[guild_id]:
            return await interaction.response.send_message("You can only claim temporary voice channels.", ephemeral=True)
            
        # Check if the owner is still in the channel
        owner_id = self.channel_owners.get(channel.id)
        if owner_id:
            owner = interaction.guild.get_member(owner_id)
            if owner and owner.voice and owner.voice.channel and owner.voice.channel.id == channel.id:
                return await interaction.response.send_message(f"This channel is still owned by {owner.display_name}.", ephemeral=True)
                
        # Defer response
        await interaction.response.defer()
        
        try:
            # Update permissions - remove old owner's permissions
            if owner_id:
                old_owner = interaction.guild.get_member(owner_id)
                if old_owner:
                    await channel.set_permissions(old_owner, overwrite=None)
                    
            # Set new owner permissions
            await channel.set_permissions(interaction.user, 
                manage_channels=True,
                move_members=True,
                mute_members=True,
                deafen_members=True
            )
            
            # Update ownership records
            self.temp_channels[guild_id][channel.id] = interaction.user.id
            self.channel_owners[channel.id] = interaction.user.id
            
            # Update channel name
            await channel.edit(name=f"{interaction.user.display_name}'s Channel")
            
            # Send confirmation
            await interaction.followup.send(f"You are now the owner of this voice channel.")
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to modify the channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to claim voice channel: {e}", ephemeral=True)

    # Error handlers
    @voicesetup_command.error
    @voicelock_command.error
    @voiceunlock_command.error
    @voicename_command.error
    @voicelimit_command.error
    @voicekick_command.error
    @voiceclaim_command.error
    async def voice_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in voice command: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Voice(bot))
