"""
Giveaway functionality for the Discord bot.
Handles commands for creating and managing giveaways.
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import datetime
import logging
import random
import time
from typing import Optional, List

import config
import utils
from database import db

logger = logging.getLogger(__name__)

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaways.start()
        
    def cog_unload(self):
        self.check_giveaways.cancel()
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Giveaway cog loaded")
        
    # Start checking for ending giveaways
    @tasks.loop(minutes=1.0)
    async def check_giveaways(self):
        """Check for giveaways that have ended and process them."""
        try:
            current_time = int(time.time())
            active_giveaways = db.get_active_giveaways()
            
            for giveaway in active_giveaways:
                if current_time >= giveaway["end_time"]:
                    # This giveaway has ended, process it
                    await self.end_giveaway(giveaway)
        except Exception as e:
            logger.error(f"Error checking giveaways: {e}")
            
    @check_giveaways.before_loop
    async def before_check_giveaways(self):
        """Wait for the bot to be ready before starting the giveaway check loop."""
        await self.bot.wait_until_ready()
        
    # Create giveaway command
    @app_commands.command(name="giveaway", description="Create a new giveaway")
    @app_commands.describe(
        prize="The prize for the giveaway",
        time="Duration of the giveaway (e.g., 1h, 1d, 1d12h)",
        winners="Number of winners (default: 1)",
        channel="The channel to host the giveaway in (default: current channel)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.checks.cooldown(1, config.GIVEAWAY_COOLDOWN)
    async def giveaway_command(self, interaction: discord.Interaction, 
                              prize: str,
                              time: str,
                              winners: Optional[int] = 1,
                              channel: Optional[discord.TextChannel] = None):
        """Create a new giveaway."""
        # Parse the time
        seconds = utils.parse_time(time)
        if seconds <= 0:
            return await interaction.response.send_message("Invalid time format. Please use a format like 1h, 1d, or 1d12h.", ephemeral=True)
            
        # Use current channel if none specified
        if channel is None:
            channel = interaction.channel
            
        # Validate winners count
        if winners < 1:
            winners = 1
        elif winners > 20:  # Limit to a reasonable number
            winners = 20
            
        # Calculate end time
        end_time = int(time.time() + seconds)
        
        # Defer response since this might take time
        await interaction.response.defer(ephemeral=True)
        
        # Create the giveaway embed
        embed = await utils.create_embed(
            title="🎉 GIVEAWAY 🎉",
            description=f"**{prize}**\n\nReact with 🎉 to enter!",
            color=config.EMBED_COLOR,
            fields=[
                {"name": "End Time", "value": f"<t:{end_time}:R> (<t:{end_time}:F>)", "inline": True},
                {"name": "Winners", "value": str(winners), "inline": True},
                {"name": "Hosted by", "value": interaction.user.mention, "inline": True}
            ],
            footer={"text": f"Giveaway ID: {utils.generate_id()}"}
        )
        
        # Send the giveaway message
        giveaway_message = await channel.send(embed=embed)
        
        # Add the reaction
        await giveaway_message.add_reaction("🎉")
        
        # Store the giveaway in the database
        giveaway_id = db.create_giveaway(
            interaction.guild.id,
            channel.id,
            giveaway_message.id,
            interaction.user.id,
            prize,
            winners,
            end_time
        )
        
        # Send confirmation to the user
        confirm_embed = await utils.create_embed(
            title="Giveaway Created",
            description=f"Your giveaway for **{prize}** has been created in {channel.mention}",
            color=config.SUCCESS_COLOR,
            fields=[
                {"name": "End Time", "value": f"<t:{end_time}:R> (<t:{end_time}:F>)", "inline": True},
                {"name": "Winners", "value": str(winners), "inline": True},
                {"name": "Message Link", "value": f"[Click here]({giveaway_message.jump_url})", "inline": False}
            ]
        )
        
        await interaction.followup.send(embed=confirm_embed, ephemeral=True)
        
    # End giveaway command
    @app_commands.command(name="endgiveaway", description="End a giveaway early")
    @app_commands.describe(
        message_id="The ID of the giveaway message to end"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def end_giveaway_command(self, interaction: discord.Interaction, message_id: str):
        """End a giveaway early."""
        try:
            # Convert message_id to int
            message_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("Invalid message ID. Please provide a valid numeric ID.", ephemeral=True)
            
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        # Find the giveaway in the database
        giveaways = db.get_active_giveaways()
        target_giveaway = None
        
        for giveaway in giveaways:
            if giveaway["message_id"] == message_id:
                target_giveaway = giveaway
                break
                
        if not target_giveaway:
            return await interaction.followup.send("No active giveaway found with that message ID.", ephemeral=True)
            
        # End the giveaway
        success = await self.end_giveaway(target_giveaway)
        
        if success:
            await interaction.followup.send("Giveaway ended successfully.", ephemeral=True)
        else:
            await interaction.followup.send("Failed to end the giveaway. It may have already ended or been deleted.", ephemeral=True)
            
    # Reroll giveaway command
    @app_commands.command(name="reroll", description="Reroll a giveaway to select new winners")
    @app_commands.describe(
        message_id="The ID of the giveaway message to reroll",
        winners="Number of new winners to select (default: 1)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def reroll_command(self, interaction: discord.Interaction, 
                            message_id: str,
                            winners: Optional[int] = 1):
        """Reroll a giveaway to select new winners."""
        try:
            # Convert message_id to int
            message_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("Invalid message ID. Please provide a valid numeric ID.", ephemeral=True)
            
        # Validate winners count
        if winners < 1:
            winners = 1
        elif winners > 20:  # Limit to a reasonable number
            winners = 20
            
        # Defer response
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get the channel and message for the giveaway
            guild = interaction.guild
            
            # Search for the giveaway in all guild channels
            giveaway_channel = None
            giveaway_message = None
            
            for channel in guild.text_channels:
                try:
                    message = await channel.fetch_message(message_id)
                    if message.author.id == self.bot.user.id:
                        giveaway_channel = channel
                        giveaway_message = message
                        break
                except:
                    continue
                    
            if not giveaway_message:
                return await interaction.followup.send("Giveaway message not found.", ephemeral=True)
                
            # Extract the prize from the embed
            if not giveaway_message.embeds:
                return await interaction.followup.send("The message doesn't appear to be a valid giveaway.", ephemeral=True)
                
            embed = giveaway_message.embeds[0]
            
            if not embed.description:
                return await interaction.followup.send("The giveaway embed is missing a description.", ephemeral=True)
                
            # Extract the prize from the description
            prize = embed.description.split('\n')[0].replace('**', '')
            
            # Get the reaction users
            reaction = None
            for r in giveaway_message.reactions:
                if str(r.emoji) == "🎉":
                    reaction = r
                    break
                    
            if not reaction:
                return await interaction.followup.send("No entries found for the giveaway.", ephemeral=True)
                
            # Get users who reacted
            users = []
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
                    
            if not users:
                return await interaction.followup.send("No valid entries found for the giveaway.", ephemeral=True)
                
            # Select new winners
            winners_count = min(winners, len(users))
            if winners_count < len(users):
                new_winners = random.sample(users, winners_count)
            else:
                new_winners = users
                
            # Send the reroll message
            winners_text = ", ".join([winner.mention for winner in new_winners])
            
            reroll_embed = await utils.create_embed(
                title="🎉 GIVEAWAY REROLL 🎉",
                description=f"**{prize}**\n\nNew winners: {winners_text}",
                color=config.EMBED_COLOR,
                timestamp=True
            )
            
            await giveaway_channel.send(
                content=f"Congratulations {winners_text}! You won the reroll for **{prize}**!",
                embed=reroll_embed,
                reference=giveaway_message
            )
            
            # Send confirmation to the user
            await interaction.followup.send(f"Successfully rerolled the giveaway with {winners_count} new winners.", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error rerolling giveaway: {e}")
            await interaction.followup.send(f"An error occurred while rerolling the giveaway: {str(e)}", ephemeral=True)
            
    # List giveaways command
    @app_commands.command(name="giveaways", description="List all active giveaways")
    async def list_giveaways_command(self, interaction: discord.Interaction):
        """List all active giveaways in the server."""
        await interaction.response.defer()
        
        # Get active giveaways for this guild
        all_giveaways = db.get_active_giveaways()
        guild_giveaways = [g for g in all_giveaways if g["guild_id"] == interaction.guild.id]
        
        if not guild_giveaways:
            return await interaction.followup.send("There are no active giveaways in this server.")
            
        # Create an embed with all giveaways
        embed = await utils.create_embed(
            title="Active Giveaways",
            description=f"There are currently {len(guild_giveaways)} active giveaways in this server.",
            color=config.EMBED_COLOR,
            timestamp=True
        )
        
        for giveaway in guild_giveaways:
            channel = interaction.guild.get_channel(giveaway["channel_id"])
            channel_mention = channel.mention if channel else "Unknown Channel"
            
            embed.add_field(
                name=giveaway["prize"],
                value=(
                    f"Channel: {channel_mention}\n"
                    f"Ends: <t:{giveaway['end_time']}:R>\n"
                    f"Winners: {giveaway['winners']}\n"
                    f"Message ID: {giveaway['message_id']}"
                ),
                inline=False
            )
            
        await interaction.followup.send(embed=embed)
            
    async def end_giveaway(self, giveaway):
        """End a giveaway and select winners."""
        try:
            # Mark the giveaway as ended in the database
            db.end_giveaway(giveaway["id"])
            
            # Get the guild, channel, and message
            guild = self.bot.get_guild(giveaway["guild_id"])
            if not guild:
                logger.error(f"Failed to end giveaway: Guild {giveaway['guild_id']} not found")
                return False
                
            channel = guild.get_channel(giveaway["channel_id"])
            if not channel:
                logger.error(f"Failed to end giveaway: Channel {giveaway['channel_id']} not found")
                return False
                
            try:
                message = await channel.fetch_message(giveaway["message_id"])
            except discord.NotFound:
                logger.error(f"Failed to end giveaway: Message {giveaway['message_id']} not found")
                return False
                
            # Get the reaction users
            reaction = None
            for r in message.reactions:
                if str(r.emoji) == "🎉":
                    reaction = r
                    break
                    
            if not reaction:
                # Update the embed to show no one entered
                embed = message.embeds[0]
                
                # Create a new embed with the updated information
                new_embed = await utils.create_embed(
                    title=embed.title,
                    description=f"{embed.description.split('React with')[0]}\n\nGiveaway ended! No valid entries.",
                    color=config.ERROR_COLOR,
                    fields=embed.fields,
                    footer={"text": "Giveaway ended"}
                )
                
                await message.edit(embed=new_embed)
                await channel.send("No one entered the giveaway!")
                return True
                
            # Get users who reacted
            users = []
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
                    
            # Check if there are enough participants
            if not users:
                # Update the embed to show no one entered
                embed = message.embeds[0]
                
                # Create a new embed with the updated information
                new_embed = await utils.create_embed(
                    title=embed.title,
                    description=f"{embed.description.split('React with')[0]}\n\nGiveaway ended! No valid entries.",
                    color=config.ERROR_COLOR,
                    fields=embed.fields,
                    footer={"text": "Giveaway ended"}
                )
                
                await message.edit(embed=new_embed)
                await channel.send("No one entered the giveaway!")
                return True
                
            # Select winners
            winners_count = min(giveaway["winners"], len(users))
            if winners_count < len(users):
                winners = random.sample(users, winners_count)
            else:
                winners = users
                
            winners_text = ", ".join([winner.mention for winner in winners])
            
            # Update the original giveaway embed
            embed = message.embeds[0]
            
            # Create a new embed with the updated information
            new_embed = await utils.create_embed(
                title=embed.title,
                description=f"{embed.description.split('React with')[0]}\n\nGiveaway ended! Winner(s): {winners_text}",
                color=config.SUCCESS_COLOR,
                fields=embed.fields,
                footer={"text": "Giveaway ended"}
            )
            
            await message.edit(embed=new_embed)
            
            # Send a message announcing the winners
            await channel.send(
                f"🎉 Congratulations {winners_text}! You won **{giveaway['prize']}**!",
                reference=message
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error ending giveaway: {e}")
            return False

    # Error handlers
    @giveaway_command.error
    @end_giveaway_command.error
    @reroll_command.error
    @list_giveaways_command.error
    async def giveaway_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You don't have the required permissions to use this command.", ephemeral=True)
        elif isinstance(error, app_commands.errors.CommandOnCooldown):
            await interaction.response.send_message(f"This command is on cooldown. Try again in {error.retry_after:.2f} seconds.", ephemeral=True)
        else:
            logger.error(f"Error in giveaway command: {error}")
            await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
