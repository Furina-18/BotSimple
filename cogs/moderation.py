"""
Moderation commands for the Discord bot.
Handles moderation actions like kick, ban, timeout, and warning management.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import logging
from typing import Optional, List

import config
import utils
from database import db

logger = logging.getLogger(__name__)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Moderation cog loaded")
        
    # Utility methods
    async def log_moderation_action(self, guild: discord.Guild, action: str, target: discord.Member, 
                                     moderator: discord.Member, reason: str, duration: str = None):
        """Log a moderation action to the server's log channel."""
        settings = db.get_server_settings(guild.id)
        log_channel_id = settings.get('log_channel_id')
        
        if not log_channel_id:
            return
            
        log_channel = guild.get_channel(log_channel_id)
        if not log_channel:
            return
            
        embed_fields = [
            {"name": "Target", "value": f"{target.mention} ({target.id})", "inline": True},
            {"name": "Moderator", "value": f"{moderator.mention} ({moderator.id})", "inline": True},
            {"name": "Reason", "value": reason or "No reason provided", "inline": False}
        ]
        
        if duration:
            embed_fields.append({"name": "Duration", "value": duration, "inline": False})
            
        embed = await utils.create_embed(
            title=f"Moderation Action: {action}",
            color=config.WARNING_COLOR,
            fields=embed_fields,
            timestamp=True
        )
        
        await log_channel.send(embed=embed)
        
    # Kick command
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(
        member="The member to kick",
        reason="Reason for kicking the member"
    )
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick_command(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("You cannot kick someone with a higher or equal role.", ephemeral=True)
            
        if not member.kickable:
            return await interaction.response.send_message("I cannot kick this member due to role hierarchy or permissions.", ephemeral=True)
            
        # Defer the response since kicking might take time
        await interaction.response.defer(ephemeral=True)
        
        # Log the action before kicking
        await self.log_moderation_action(
            interaction.guild, 
            "Kick", 
            member, 
            interaction.user, 
            reason
        )
        
        try:
            # Send a DM to the user being kicked
            try:
                dm_embed = await utils.create_embed(
                    title=f"You've been kicked from {interaction.guild.name}",
                    description=f"Reason: {reason or 'No reason provided'}",
                    color=config.ERROR_COLOR
                )
                await member.send(embed=dm_embed)
            except:
                # User might have DMs closed, this shouldn't stop the kick
                pass
                
            # Kick the member
            await member.kick(reason=reason)
            
            # Send confirmation
            embed = await utils.create_embed(
                title="Member Kicked",
                description=f"{member.mention} has been kicked from the server.",
                color=config.SUCCESS_COLOR,
                fields=[{"name": "Reason", "value": reason or "No reason provided", "inline": False}],
                timestamp=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to kick that member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while kicking the member: {str(e)}", ephemeral=True)
            
    # Ban command
    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(
        member="The member to ban",
        reason="Reason for banning the member",
        delete_messages="Number of days of messages to delete (0-7)"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban_command(self, interaction: discord.Interaction, member: discord.Member, 
                         reason: Optional[str] = None, delete_messages: Optional[int] = 1):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("You cannot ban someone with a higher or equal role.", ephemeral=True)
            
        if not member.banlable:
            return await interaction.response.send_message("I cannot ban this member due to role hierarchy or permissions.", ephemeral=True)
            
        # Ensure delete_messages is between 0-7 days
        delete_messages = max(0, min(7, delete_messages))
        
        # Defer the response since banning might take time
        await interaction.response.defer(ephemeral=True)
        
        # Log the action before banning
        await self.log_moderation_action(
            interaction.guild, 
            "Ban", 
            member, 
            interaction.user, 
            reason
        )
        
        try:
            # Send a DM to the user being banned
            try:
                dm_embed = await utils.create_embed(
                    title=f"You've been banned from {interaction.guild.name}",
                    description=f"Reason: {reason or 'No reason provided'}",
                    color=config.ERROR_COLOR
                )
                await member.send(embed=dm_embed)
            except:
                # User might have DMs closed, this shouldn't stop the ban
                pass
                
            # Ban the member
            await member.ban(reason=reason, delete_message_days=delete_messages)
            
            # Send confirmation
            embed = await utils.create_embed(
                title="Member Banned",
                description=f"{member.mention} has been banned from the server.",
                color=config.SUCCESS_COLOR,
                fields=[{"name": "Reason", "value": reason or "No reason provided", "inline": False}],
                timestamp=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to ban that member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while banning the member: {str(e)}", ephemeral=True)
            
    # Unban command
    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user_id="The ID of the user to unban",
        reason="Reason for unbanning the user"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban_command(self, interaction: discord.Interaction, user_id: str, 
                           reason: Optional[str] = None):
        try:
            user_id = int(user_id)
        except ValueError:
            return await interaction.response.send_message("Invalid user ID. Please provide a valid numeric ID.", ephemeral=True)
            
        # Defer the response since fetching ban list might take time
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Fetch the ban entry
            ban_entry = await interaction.guild.fetch_ban(discord.Object(id=user_id))
            user = ban_entry.user
            
            # Unban the user
            await interaction.guild.unban(user, reason=reason)
            
            # Log the action
            await self.log_moderation_action(
                interaction.guild, 
                "Unban", 
                user, 
                interaction.user, 
                reason
            )
            
            # Send confirmation
            embed = await utils.create_embed(
                title="User Unbanned",
                description=f"{user.mention} ({user.id}) has been unbanned from the server.",
                color=config.SUCCESS_COLOR,
                fields=[{"name": "Reason", "value": reason or "No reason provided", "inline": False}],
                timestamp=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except discord.NotFound:
            await interaction.followup.send("This user is not banned.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to unban users.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while unbanning the user: {str(e)}", ephemeral=True)
            
    # Timeout (mute) command
    @app_commands.command(name="timeout", description="Timeout (mute) a member")
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration of timeout (e.g., 10m, 1h, 1d)",
        reason="Reason for the timeout"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout_command(self, interaction: discord.Interaction, member: discord.Member, 
                             duration: str, reason: Optional[str] = None):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("You cannot timeout someone with a higher or equal role.", ephemeral=True)
            
        # Parse the duration string to seconds
        seconds = utils.parse_time(duration)
        if seconds <= 0:
            return await interaction.response.send_message("Invalid duration. Please use a format like 10m, 1h, or 1d.", ephemeral=True)
            
        # Maximum timeout duration allowed by Discord is 28 days
        max_seconds = 28 * 24 * 60 * 60
        if seconds > max_seconds:
            return await interaction.response.send_message(f"Timeout duration cannot exceed 28 days. Your specified duration: {utils.format_time(seconds)}", ephemeral=True)
            
        # Calculate the end time
        until = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        
        # Defer the response
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Apply the timeout
            await member.timeout(until=until, reason=reason)
            
            # Log the action
            await self.log_moderation_action(
                interaction.guild, 
                "Timeout", 
                member, 
                interaction.user, 
                reason,
                utils.format_time(seconds)
            )
            
            # Send a DM to the user
            try:
                dm_embed = await utils.create_embed(
                    title=f"You've been timed out in {interaction.guild.name}",
                    description=f"Duration: {utils.format_time(seconds)}\nReason: {reason or 'No reason provided'}",
                    color=config.WARNING_COLOR
                )
                await member.send(embed=dm_embed)
            except:
                # User might have DMs closed
                pass
                
            # Send confirmation
            embed = await utils.create_embed(
                title="Member Timed Out",
                description=f"{member.mention} has been timed out.",
                color=config.SUCCESS_COLOR,
                fields=[
                    {"name": "Duration", "value": utils.format_time(seconds), "inline": True},
                    {"name": "Until", "value": f"<t:{int(until.timestamp())}:F>", "inline": True},
                    {"name": "Reason", "value": reason or "No reason provided", "inline": False}
                ],
                timestamp=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to timeout that member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while timing out the member: {str(e)}", ephemeral=True)
            
    # Remove timeout command
    @app_commands.command(name="untimeout", description="Remove a timeout from a member")
    @app_commands.describe(
        member="The member to remove timeout from",
        reason="Reason for removing the timeout"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout_command(self, interaction: discord.Interaction, member: discord.Member, 
                               reason: Optional[str] = None):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("You cannot remove a timeout from someone with a higher or equal role.", ephemeral=True)
            
        # Check if the member is actually timed out
        if not member.is_timed_out():
            return await interaction.response.send_message("This member is not currently timed out.", ephemeral=True)
            
        # Defer the response
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Remove the timeout
            await member.timeout(until=None, reason=reason)
            
            # Log the action
            await self.log_moderation_action(
                interaction.guild, 
                "Timeout Removed", 
                member, 
                interaction.user, 
                reason
            )
            
            # Send a DM to the user
            try:
                dm_embed = await utils.create_embed(
                    title=f"Your timeout in {interaction.guild.name} has been removed",
                    description=f"Reason: {reason or 'No reason provided'}",
                    color=config.SUCCESS_COLOR
                )
                await member.send(embed=dm_embed)
            except:
                # User might have DMs closed
                pass
                
            # Send confirmation
            embed = await utils.create_embed(
                title="Timeout Removed",
                description=f"{member.mention}'s timeout has been removed.",
                color=config.SUCCESS_COLOR,
                fields=[{"name": "Reason", "value": reason or "No reason provided", "inline": False}],
                timestamp=True
            )
            
            await interaction.followup.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to remove timeout from that member.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while removing the timeout: {str(e)}", ephemeral=True)
            
    # Purge messages command
    @app_commands.command(name="purge", description="Delete multiple messages from a channel")
    @app_commands.describe(
        amount="Number of messages to delete (default: 10, max: 100)",
        user="Only delete messages from this user (optional)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge_command(self, interaction: discord.Interaction, amount: Optional[int] = 10, 
                           user: Optional[discord.Member] = None):
        # Limit the amount to a maximum of 100
        amount = min(amount, config.DEFAULT_PURGE_LIMIT)
        
        # Defer the response
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Define a check function if we're filtering by user
            def check(message):
                return user is None or message.author.id == user.id
                
            # Delete the messages
            deleted = await interaction.channel.purge(limit=amount, check=check)
            
            # Log the action
            await self.log_moderation_action(
                interaction.guild, 
                "Purge", 
                user or interaction.guild.me, 
                interaction.user, 
                f"Deleted {len(deleted)} messages in {interaction.channel.mention}"
            )
            
            # Send confirmation
            message = f"Deleted {len(deleted)} messages"
            if user:
                message += f" from {user.mention}"
                
            await interaction.followup.send(message, ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete messages in this channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"An error occurred while deleting messages: {str(e)}", ephemeral=True)
    
    # Warning commands
    @app_commands.command(name="warn", description="Warn a member")
    @app_commands.describe(
        member="The member to warn",
        reason="Reason for the warning"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn_command(self, interaction: discord.Interaction, member: discord.Member, 
                          reason: str):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            return await interaction.response.send_message("You cannot warn someone with a higher or equal role.", ephemeral=True)
            
        # Defer the response
        await interaction.response.defer(ephemeral=True)
        
        # Add the warning to the database
        timestamp = int(datetime.datetime.now().timestamp())
        warning_id = db.add_warning(interaction.guild.id, member.id, interaction.user.id, reason, timestamp)
        
        # Log the action
        await self.log_moderation_action(
            interaction.guild, 
            "Warning", 
            member, 
            interaction.user, 
            reason
        )
        
        # Send a DM to the user
        try:
            dm_embed = await utils.create_embed(
                title=f"You've been warned in {interaction.guild.name}",
                description=f"Reason: {reason}",
                color=config.WARNING_COLOR,
                fields=[{"name": "Warning ID", "value": str(warning_id), "inline": False}],
                timestamp=True
            )
            await member.send(embed=dm_embed)
        except:
            # User might have DMs closed
            pass
            
        # Get the total number of warnings for this user
        warnings = db.get_warnings(interaction.guild.id, member.id)
        
        # Send confirmation
        embed = await utils.create_embed(
            title="Member Warned",
            description=f"{member.mention} has been warned.",
            color=config.SUCCESS_COLOR,
            fields=[
                {"name": "Reason", "value": reason, "inline": False},
                {"name": "Warning ID", "value": str(warning_id), "inline": True},
                {"name": "Total Warnings", "value": str(len(warnings)), "inline": True}
            ],
            timestamp=True
        )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="warnings", description="Show warnings for a member")
    @app_commands.describe(
        member="The member to check warnings for"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings_command(self, interaction: discord.Interaction, member: discord.Member):
        # Defer the response
        await interaction.response.defer(ephemeral=True)
        
        # Get warnings from the database
        warnings = db.get_warnings(interaction.guild.id, member.id)
        
        if not warnings:
            return await interaction.followup.send(f"{member.mention} has no warnings.", ephemeral=True)
            
        # Create an embed for the warnings
        embed = await utils.create_embed(
            title=f"Warnings for {member.display_name}",
            description=f"Total warnings: {len(warnings)}",
            color=config.WARNING_COLOR,
            timestamp=True
        )
        
        # Add fields for each warning (up to 25 to avoid hitting embed limits)
        for i, warning in enumerate(warnings[:25]):
            moderator = interaction.guild.get_member(warning['moderator_id'])
            moderator_name = moderator.mention if moderator else f"Unknown Moderator ({warning['moderator_id']})"
            
            warning_time = datetime.datetime.fromtimestamp(warning['timestamp'])
            time_str = f"<t:{warning['timestamp']}:F>"
            
            embed.add_field(
                name=f"Warning #{warning['id']}",
                value=f"**Reason:** {warning['reason']}\n**By:** {moderator_name}\n**When:** {time_str}",
                inline=False
            )
            
        # If there are more than 25 warnings, add a note
        if len(warnings) > 25:
            embed.set_footer(text=f"Showing 25/{len(warnings)} warnings")
            
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="delwarn", description="Delete a warning by ID")
    @app_commands.describe(
        warning_id="The ID of the warning to delete"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def delwarn_command(self, interaction: discord.Interaction, warning_id: int):
        # Defer the response
        await interaction.response.defer(ephemeral=True)
        
        # Attempt to remove the warning
        success = db.remove_warning(warning_id)
        
        if success:
            await interaction.followup.send(f"Warning #{warning_id} has been deleted.", ephemeral=True)
        else:
            await interaction.followup.send(f"Warning #{warning_id} not found.", ephemeral=True)

    # Error handlers
    @kick_command.error
    @ban_command.error
    @unban_command.error
    @timeout_command.error
    @untimeout_command.error
    @purge_command.error
    @warn_command.error
    @warnings_command.error
    @delwarn_command.error
    async def moderation_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in moderation command: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
