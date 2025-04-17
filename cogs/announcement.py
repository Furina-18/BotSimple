"""
Announcement functionality for the Discord bot.
Handles commands for creating and managing announcements.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import logging
from typing import Optional

import config
import utils
from database import db

logger = logging.getLogger(__name__)

class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Announcement cog loaded")
        
    # Announcement command
    @app_commands.command(name="announce", description="Create an announcement")
    @app_commands.describe(
        channel="The channel to send the announcement to",
        title="The title of the announcement",
        message="The message for the announcement",
        color="The color of the announcement embed (hex format like #3498db)",
        mention="Optional role to mention with the announcement",
        image="Optional image URL to include"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.cooldown(1, config.ANNOUNCEMENT_COOLDOWN)
    async def announce_command(self, interaction: discord.Interaction, 
                              channel: discord.TextChannel,
                              title: str,
                              message: str,
                              color: Optional[str] = None,
                              mention: Optional[discord.Role] = None,
                              image: Optional[str] = None):
        """Create and send an announcement to a channel."""
        # Defer the response since this might take time
        await interaction.response.defer(ephemeral=True)
        
        # Validate and parse the color
        embed_color = config.EMBED_COLOR
        if color:
            try:
                # Convert hex color (e.g. #RRGGBB) to integer
                if color.startswith('#'):
                    color = color[1:]
                embed_color = int(color, 16)
            except ValueError:
                await interaction.followup.send("Invalid color format. Please use hex format like #3498db", ephemeral=True)
                return
                
        # Create the announcement embed
        embed = await utils.create_embed(
            title=title,
            description=message,
            color=embed_color,
            timestamp=True,
            footer={"text": f"Announcement by {interaction.user.display_name}"}
        )
        
        # Add image if provided
        if image and utils.is_url(image):
            embed.set_image(url=image)
            
        # Prepare the mention text if needed
        mention_text = ""
        if mention:
            mention_text = f"{mention.mention} "
            
        # Send the announcement
        try:
            announcement_message = await channel.send(content=mention_text, embed=embed)
            
            # Send confirmation to the user
            confirm_embed = await utils.create_embed(
                title="Announcement Sent",
                description=f"Your announcement has been sent to {channel.mention}",
                color=config.SUCCESS_COLOR,
                fields=[
                    {"name": "Message Link", "value": f"[Click here]({announcement_message.jump_url})", "inline": False}
                ]
            )
            
            await interaction.followup.send(embed=confirm_embed, ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send(f"I don't have permission to send messages in {channel.mention}", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to send announcement: {str(e)}", ephemeral=True)
            
    # Edit announcement command
    @app_commands.command(name="editannounce", description="Edit an existing announcement")
    @app_commands.describe(
        message_id="The ID of the announcement message to edit",
        channel="The channel where the announcement is",
        title="The new title (leave empty to keep current)",
        message="The new message (leave empty to keep current)",
        color="The new color (hex format like #3498db, leave empty to keep current)",
        image="The new image URL (leave empty to keep current)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def edit_announce_command(self, interaction: discord.Interaction,
                                   message_id: str,
                                   channel: discord.TextChannel,
                                   title: Optional[str] = None,
                                   message: Optional[str] = None,
                                   color: Optional[str] = None,
                                   image: Optional[str] = None):
        """Edit an existing announcement."""
        # Defer the response since this might take time
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Convert message_id to int
            message_id = int(message_id)
        except ValueError:
            await interaction.followup.send("Invalid message ID. Please provide a valid numeric ID.", ephemeral=True)
            return
            
        try:
            # Fetch the message
            announcement_message = await channel.fetch_message(message_id)
            
            # Check if the message is from the bot and has embeds
            if announcement_message.author.id != self.bot.user.id or not announcement_message.embeds:
                await interaction.followup.send("The specified message is not a valid announcement from this bot.", ephemeral=True)
                return
                
            # Get the current embed
            current_embed = announcement_message.embeds[0]
            
            # Prepare the new embed with values from the old one if not provided
            embed_title = title if title is not None else current_embed.title
            embed_description = message if message is not None else current_embed.description
            
            # Parse color if provided
            embed_color = current_embed.color
            if color:
                try:
                    if color.startswith('#'):
                        color = color[1:]
                    embed_color = int(color, 16)
                except ValueError:
                    await interaction.followup.send("Invalid color format. Please use hex format like #3498db", ephemeral=True)
                    return
                    
            # Create the new embed
            new_embed = await utils.create_embed(
                title=embed_title,
                description=embed_description,
                color=embed_color,
                timestamp=True,
                footer={"text": f"Announcement by {interaction.user.display_name} (edited)"}
            )
            
            # Add image if provided or keep the current one
            if image and utils.is_url(image):
                new_embed.set_image(url=image)
            elif current_embed.image:
                new_embed.set_image(url=current_embed.image.url)
                
            # Edit the announcement
            await announcement_message.edit(embed=new_embed)
            
            # Send confirmation to the user
            confirm_embed = await utils.create_embed(
                title="Announcement Edited",
                description=f"Your announcement has been edited in {channel.mention}",
                color=config.SUCCESS_COLOR,
                fields=[
                    {"name": "Message Link", "value": f"[Click here]({announcement_message.jump_url})", "inline": False}
                ]
            )
            
            await interaction.followup.send(embed=confirm_embed, ephemeral=True)
            
        except discord.NotFound:
            await interaction.followup.send("The specified message could not be found.", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(f"I don't have permission to edit messages in {channel.mention}", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to edit announcement: {str(e)}", ephemeral=True)
            
    # Scheduled announcement command
    @app_commands.command(name="scheduleannounce", description="Schedule an announcement for the future")
    @app_commands.describe(
        channel="The channel to send the announcement to",
        time="When to send the announcement (e.g., 1h, 30m, 2h30m)",
        title="The title of the announcement",
        message="The message for the announcement",
        color="The color of the announcement embed (hex format like #3498db)",
        mention="Optional role to mention with the announcement",
        image="Optional image URL to include"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def schedule_announce_command(self, interaction: discord.Interaction,
                                       channel: discord.TextChannel,
                                       time: str,
                                       title: str,
                                       message: str,
                                       color: Optional[str] = None,
                                       mention: Optional[discord.Role] = None,
                                       image: Optional[str] = None):
        """Schedule an announcement to be sent in the future."""
        # Parse the time
        seconds = utils.parse_time(time)
        if seconds <= 0:
            return await interaction.response.send_message("Invalid time format. Please use a format like 1h, 30m, or 2h30m.", ephemeral=True)
            
        # Defer the response
        await interaction.response.defer(ephemeral=True)
        
        # Calculate when the announcement will be sent
        send_time = datetime.datetime.now() + datetime.timedelta(seconds=seconds)
        
        # Validate and parse the color
        embed_color = config.EMBED_COLOR
        if color:
            try:
                if color.startswith('#'):
                    color = color[1:]
                embed_color = int(color, 16)
            except ValueError:
                await interaction.followup.send("Invalid color format. Please use hex format like #3498db", ephemeral=True)
                return
                
        # Store the announcement data
        announcement_data = {
            "channel_id": channel.id,
            "title": title,
            "message": message,
            "color": embed_color,
            "mention_id": mention.id if mention else None,
            "image": image,
            "creator_id": interaction.user.id,
            "send_time": send_time.timestamp()
        }
        
        # Create a confirmation embed
        confirm_embed = await utils.create_embed(
            title="Announcement Scheduled",
            description=f"Your announcement has been scheduled to be sent in {time}",
            color=config.SUCCESS_COLOR,
            fields=[
                {"name": "Channel", "value": channel.mention, "inline": True},
                {"name": "Send Time", "value": f"<t:{int(send_time.timestamp())}:F>", "inline": True},
                {"name": "Title", "value": title, "inline": False}
            ]
        )
        
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        
        # Create a task to send the announcement at the scheduled time
        self.bot.loop.create_task(self.send_scheduled_announcement(announcement_data))
        
    async def send_scheduled_announcement(self, data):
        """Send a scheduled announcement when its time arrives."""
        # Calculate how long to wait
        now = datetime.datetime.now().timestamp()
        wait_time = data["send_time"] - now
        
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            
        # Get the channel
        channel = self.bot.get_channel(data["channel_id"])
        if not channel:
            logger.error(f"Failed to send scheduled announcement: Channel {data['channel_id']} not found")
            return
            
        # Create the announcement embed
        embed = await utils.create_embed(
            title=data["title"],
            description=data["message"],
            color=data["color"],
            timestamp=True,
            footer={"text": f"Scheduled announcement by {self.bot.get_user(data['creator_id']).display_name if self.bot.get_user(data['creator_id']) else 'Unknown'}"}
        )
        
        # Add image if provided
        if data["image"] and utils.is_url(data["image"]):
            embed.set_image(url=data["image"])
            
        # Prepare the mention text if needed
        mention_text = ""
        if data["mention_id"]:
            role = channel.guild.get_role(data["mention_id"])
            if role:
                mention_text = f"{role.mention} "
                
        # Send the announcement
        try:
            await channel.send(content=mention_text, embed=embed)
            logger.info(f"Sent scheduled announcement to channel {channel.name} in {channel.guild.name}")
        except Exception as e:
            logger.error(f"Failed to send scheduled announcement: {e}")

    # Error handlers
    @announce_command.error
    @edit_announce_command.error
    @schedule_announce_command.error
    async def announcement_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
        elif isinstance(error, app_commands.errors.CommandOnCooldown):
            await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
        else:
            logger.error(f"Error in announcement command: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Announcement(bot))
