"""
Ticket functionality for the Discord bot.
Handles commands for creating and managing support tickets.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import logging
import io
import time
from typing import Optional, List, Dict, Any

import config
import utils
from database import db

logger = logging.getLogger(__name__)

class Ticket(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Ticket cog loaded")
        
    # Setup ticket system command
    @app_commands.command(name="ticketsetup", description="Set up the ticket system")
    @app_commands.describe(
        channel="The channel to send the ticket panel to",
        title="The title for the ticket panel",
        description="The description for the ticket panel",
        category="The category to create ticket channels in",
        support_role="The role that can see and respond to tickets"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def ticketsetup_command(self, interaction: discord.Interaction,
                                 channel: discord.TextChannel,
                                 title: str,
                                 description: str,
                                 category: discord.CategoryChannel,
                                 support_role: discord.Role):
        """Set up the ticket system."""
        # Check bot permissions
        if not channel.permissions_for(interaction.guild.me).send_messages:
            return await interaction.response.send_message(f"I don't have permission to send messages in {channel.mention}", ephemeral=True)
            
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        # Store ticket settings in server settings
        settings = db.get_server_settings(interaction.guild.id)
        if not settings.get('settings'):
            settings['settings'] = {}
            
        settings['settings']['ticket_category'] = category.id
        settings['settings']['ticket_support_role'] = support_role.id
        
        db.update_server_settings(interaction.guild.id, settings)
        
        # Create the ticket panel embed
        embed = await utils.create_embed(
            title=title,
            description=description,
            color=config.EMBED_COLOR,
            footer={"text": "Click the button below to create a ticket"}
        )
        
        # Create the button for creating tickets
        view = discord.ui.View(timeout=None)
        
        ticket_button = discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="Create Ticket",
            emoji="🎫",
            custom_id="create_ticket"
        )
        
        view.add_item(ticket_button)
        
        # Send the ticket panel
        await channel.send(embed=embed, view=view)
        
        # Confirmation message
        await interaction.followup.send(f"Ticket system set up in {channel.mention}. Tickets will be created in the {category.name} category and {support_role.mention} will have access to them.", ephemeral=True)
        
    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        """Handle button interactions for tickets."""
        if not interaction.type == discord.InteractionType.component:
            return
            
        custom_id = interaction.data.get("custom_id", "")
        
        if custom_id == "create_ticket":
            await self.create_ticket(interaction)
        elif custom_id == "close_ticket":
            await self.close_ticket(interaction)
        elif custom_id == "delete_ticket":
            await self.delete_ticket(interaction)
            
    async def create_ticket(self, interaction):
        """Create a new support ticket."""
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        # Get ticket settings
        settings = db.get_server_settings(interaction.guild.id)
        ticket_settings = settings.get('settings', {})
        
        category_id = ticket_settings.get('ticket_category')
        support_role_id = ticket_settings.get('ticket_support_role')
        
        if not category_id or not support_role_id:
            return await interaction.followup.send("The ticket system is not properly set up. Please contact an administrator.", ephemeral=True)
            
        category = interaction.guild.get_channel(category_id)
        support_role = interaction.guild.get_role(support_role_id)
        
        if not category or not support_role:
            return await interaction.followup.send("The ticket system is not properly set up. Please contact an administrator.", ephemeral=True)
            
        # Check if the user already has an open ticket
        for channel in category.channels:
            if channel.name.startswith(f"ticket-{interaction.user.name.lower()}"):
                return await interaction.followup.send(f"You already have an open ticket: {channel.mention}", ephemeral=True)
                
        # Create permissions for the ticket channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, manage_permissions=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Create the ticket channel
        # Remove special characters from username to prevent channel creation issues
        safe_name = ''.join(c for c in interaction.user.name.lower() if c.isalnum() or c == '-' or c == '_')
        if not safe_name:
            safe_name = "user"
            
        channel_name = f"ticket-{safe_name}"
        ticket_channel = await category.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            reason=f"Support ticket for {interaction.user}"
        )
        
        # Create the initial ticket message
        embed = await utils.create_embed(
            title="Support Ticket",
            description=f"Thank you for creating a ticket, {interaction.user.mention}. Please describe your issue and a support team member will assist you soon.",
            color=config.EMBED_COLOR,
            footer={"text": "To close this ticket, click the button below"}
        )
        
        # Create buttons for the ticket
        view = discord.ui.View(timeout=None)
        
        close_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Close Ticket",
            emoji="🔒",
            custom_id="close_ticket"
        )
        
        view.add_item(close_button)
        
        # Send the initial message
        await ticket_channel.send(
            content=f"{interaction.user.mention} {support_role.mention}",
            embed=embed,
            view=view
        )
        
        # Store the ticket in the database
        created_at = int(time.time())
        ticket_id = db.create_ticket(
            interaction.guild.id,
            ticket_channel.id,
            interaction.user.id,
            created_at
        )
        
        # Send confirmation
        await interaction.followup.send(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)
        
    async def close_ticket(self, interaction):
        """Close a support ticket."""
        # Defer response
        await interaction.response.defer(ephemeral=False)
        
        # Get ticket information
        ticket = db.get_ticket(interaction.channel.id)
        
        if not ticket:
            return await interaction.followup.send("This channel is not a valid ticket.", ephemeral=True)
            
        if ticket["closed"]:
            return await interaction.followup.send("This ticket is already closed.", ephemeral=True)
            
        # Get ticket creator
        creator_id = ticket["user_id"]
        creator = interaction.guild.get_member(creator_id)
        
        # Update permissions - remove the user's ability to send messages
        if creator:
            await interaction.channel.set_permissions(creator, send_messages=False, read_messages=True)
            
        # Mark the ticket as closed in the database
        db.close_ticket(interaction.channel.id)
        
        # Send a message that the ticket is closed
        embed = await utils.create_embed(
            title="Ticket Closed",
            description=f"This ticket has been closed by {interaction.user.mention}.",
            color=config.WARNING_COLOR,
            timestamp=True
        )
        
        # Create buttons for the closed ticket
        view = discord.ui.View(timeout=None)
        
        delete_button = discord.ui.Button(
            style=discord.ButtonStyle.danger,
            label="Delete Ticket",
            emoji="⛔",
            custom_id="delete_ticket"
        )
        
        view.add_item(delete_button)
        
        await interaction.followup.send(embed=embed, view=view)
        
    async def delete_ticket(self, interaction):
        """Delete a closed ticket."""
        # Check if the user has permission to delete tickets
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("You don't have permission to delete tickets.", ephemeral=True)
            
        # Confirm deletion
        await interaction.response.defer(ephemeral=False)
        
        # Get ticket information and messages for transcript
        ticket = db.get_ticket(interaction.channel.id)
        
        if not ticket:
            return await interaction.followup.send("This channel is not a valid ticket.", ephemeral=True)
            
        # Create transcript of the ticket
        messages = []
        async for message in interaction.channel.history(limit=500, oldest_first=True):
            if message.author.bot and not message.embeds and not message.content:
                continue
                
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = message.content or "No content"
            
            if message.embeds:
                content += "\n[Embed]"
                
            messages.append(f"[{timestamp}] {message.author.display_name}: {content}")
            
        transcript_text = "\n".join(messages)
        
        # Create a file with the transcript
        transcript_file = discord.File(
            io.StringIO(transcript_text),
            filename=f"transcript-{interaction.channel.name}.txt"
        )
        
        # Check if there's a logging channel
        settings = db.get_server_settings(interaction.guild.id)
        log_channel_id = settings.get('log_channel_id')
        
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                # Send the transcript to the log channel
                creator_id = ticket["user_id"]
                creator = interaction.guild.get_member(creator_id) or await interaction.guild.fetch_member(creator_id)
                creator_name = creator.display_name if creator else f"Unknown User ({creator_id})"
                
                embed = await utils.create_embed(
                    title="Ticket Deleted",
                    description=f"Ticket for {creator_name} was deleted by {interaction.user.mention}",
                    color=config.ERROR_COLOR,
                    timestamp=True,
                    fields=[
                        {"name": "Ticket Channel", "value": interaction.channel.name, "inline": True},
                        {"name": "Created At", "value": f"<t:{ticket['created_at']}:F>", "inline": True}
                    ]
                )
                
                await log_channel.send(embed=embed, file=transcript_file)
                
        # Send a final message before deleting
        await interaction.followup.send("This ticket will be deleted in 5 seconds...")
        
        # Wait a moment then delete the channel
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket closed and deleted by {interaction.user}")

    # Add user to ticket command
    @app_commands.command(name="adduser", description="Add a user to a ticket")
    @app_commands.describe(
        user="The user to add to the ticket"
    )
    async def adduser_command(self, interaction: discord.Interaction, user: discord.Member):
        """Add a user to a ticket."""
        # Check if this is a ticket channel
        ticket = db.get_ticket(interaction.channel.id)
        
        if not ticket:
            return await interaction.response.send_message("This command can only be used in ticket channels.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer()
        
        # Add the user to the ticket
        await interaction.channel.set_permissions(user, read_messages=True, send_messages=True)
        
        # Send confirmation
        await interaction.followup.send(f"{user.mention} has been added to the ticket by {interaction.user.mention}")
        
    # Remove user from ticket command
    @app_commands.command(name="removeuser", description="Remove a user from a ticket")
    @app_commands.describe(
        user="The user to remove from the ticket"
    )
    async def removeuser_command(self, interaction: discord.Interaction, user: discord.Member):
        """Remove a user from a ticket."""
        # Check if this is a ticket channel
        ticket = db.get_ticket(interaction.channel.id)
        
        if not ticket:
            return await interaction.response.send_message("This command can only be used in ticket channels.", ephemeral=True)
            
        # Don't allow removing the ticket creator
        if user.id == ticket["user_id"]:
            return await interaction.response.send_message("You cannot remove the ticket creator.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer()
        
        # Remove the user from the ticket
        await interaction.channel.set_permissions(user, overwrite=None)
        
        # Send confirmation
        await interaction.followup.send(f"{user.mention} has been removed from the ticket by {interaction.user.mention}")

    # Error handlers
    @ticketsetup_command.error
    @adduser_command.error
    @removeuser_command.error
    async def ticket_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in ticket command: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Ticket(bot))
