"""
Server statistics functionality for the Discord bot.
Tracks and displays various server statistics.
"""
import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
import datetime
import logging
import time
import io
import matplotlib
matplotlib.use('Agg')  # Use the Agg backend (for non-interactive environments)
import matplotlib.pyplot as plt
from typing import Optional, Dict, List, Any
from collections import defaultdict

import config
import utils
from database import db

logger = logging.getLogger(__name__)

class ServerStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stats_cache = defaultdict(lambda: {
            "message_count": 0,
            "voice_minutes": 0,
            "last_voice_update": {}  # user_id -> join_time
        })
        self.record_stats.start()
        
    def cog_unload(self):
        self.record_stats.cancel()
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("ServerStats cog loaded")
        
    @commands.Cog.listener()
    async def on_message(self, message):
        """Track message count for statistics."""
        # Ignore bot messages and DMs
        if message.author.bot or not message.guild:
            return
            
        # Increment the message count for this guild
        self.stats_cache[message.guild.id]["message_count"] += 1
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Track voice channel usage for statistics."""
        # Ignore bot voice state changes
        if member.bot:
            return
            
        guild_id = member.guild.id
        user_id = member.id
        now = time.time()
        
        # User joined a voice channel
        if before.channel is None and after.channel is not None:
            self.stats_cache[guild_id]["last_voice_update"][user_id] = now
            
        # User left a voice channel
        elif before.channel is not None and after.channel is None:
            # Calculate how long they were in the voice channel
            join_time = self.stats_cache[guild_id]["last_voice_update"].get(user_id)
            if join_time:
                time_spent = now - join_time
                # Convert to minutes and add to the total
                minutes_spent = time_spent / 60
                self.stats_cache[guild_id]["voice_minutes"] += minutes_spent
                # Remove the user from the tracking dict
                self.stats_cache[guild_id]["last_voice_update"].pop(user_id, None)
                
        # User moved voice channels - count as continuous
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            # Keep the same join time
            pass
            
    @tasks.loop(minutes=60.0)
    async def record_stats(self):
        """Record server statistics to the database every hour."""
        try:
            current_time = int(time.time())
            timestamp = current_time - (current_time % 3600)  # Round to the nearest hour
            
            for guild_id, stats in self.stats_cache.items():
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue
                    
                # Get current member count
                member_count = guild.member_count
                
                # Get message count and voice minutes
                message_count = stats["message_count"]
                voice_minutes = stats["voice_minutes"]
                
                # Record stats in the database
                db.record_stats(guild_id, timestamp, member_count, message_count, voice_minutes)
                
                # Reset counters
                stats["message_count"] = 0
                stats["voice_minutes"] = 0
                
                logger.info(f"Recorded stats for {guild.name}: {member_count} members, {message_count} messages, {voice_minutes:.2f} voice minutes")
                
        except Exception as e:
            logger.error(f"Error recording server stats: {e}")
            
    @record_stats.before_loop
    async def before_record_stats(self):
        """Wait for the bot to be ready before starting the stats recording loop."""
        await self.bot.wait_until_ready()
        
    # Statistics command
    @app_commands.command(name="serverstats", description="View server statistics")
    @app_commands.describe(
        timeframe="The timeframe to show statistics for (default: 24h)",
        type="The type of statistics to show (default: all)"
    )
    @app_commands.choices(timeframe=[
        app_commands.Choice(name="24 Hours", value="24h"),
        app_commands.Choice(name="7 Days", value="7d"),
        app_commands.Choice(name="30 Days", value="30d")
    ])
    @app_commands.choices(type=[
        app_commands.Choice(name="All", value="all"),
        app_commands.Choice(name="Members", value="members"),
        app_commands.Choice(name="Messages", value="messages"),
        app_commands.Choice(name="Voice Activity", value="voice")
    ])
    async def serverstats_command(self, interaction: discord.Interaction,
                                 timeframe: Optional[app_commands.Choice[str]] = None,
                                 type: Optional[app_commands.Choice[str]] = None):
        """Display server statistics."""
        await interaction.response.defer()
        
        # Set default values if not provided
        timeframe_value = timeframe.value if timeframe else "24h"
        type_value = type.value if type else "all"
        
        # Calculate the time range
        now = int(time.time())
        if timeframe_value == "24h":
            from_time = now - (24 * 3600)  # 24 hours ago
            time_label = "24 Hours"
        elif timeframe_value == "7d":
            from_time = now - (7 * 24 * 3600)  # 7 days ago
            time_label = "7 Days"
        elif timeframe_value == "30d":
            from_time = now - (30 * 24 * 3600)  # 30 days ago
            time_label = "30 Days"
        else:
            from_time = now - (24 * 3600)  # Default to 24 hours
            time_label = "24 Hours"
            
        # Get statistics from the database
        stats = db.get_stats(interaction.guild.id, from_time, now)
        
        if not stats:
            return await interaction.followup.send("No statistics available for the selected timeframe.")
            
        # Process the statistics
        timestamps = []
        member_counts = []
        message_counts = []
        voice_minutes = []
        
        for stat in stats:
            timestamps.append(datetime.datetime.fromtimestamp(stat["timestamp"]))
            member_counts.append(stat["member_count"])
            message_counts.append(stat["message_count"])
            voice_minutes.append(stat["voice_minutes"])
            
        # Create the embed
        embed = await utils.create_embed(
            title=f"Server Statistics - Past {time_label}",
            description=f"Statistics for {interaction.guild.name}",
            color=config.EMBED_COLOR,
            timestamp=True
        )
        
        # Add summary fields
        if type_value in ["all", "members"]:
            current_members = interaction.guild.member_count
            member_change = current_members - member_counts[0] if member_counts else 0
            member_change_str = f"+{member_change}" if member_change >= 0 else str(member_change)
            
            embed.add_field(
                name="Members",
                value=f"Current: **{current_members}**\nChange: **{member_change_str}**",
                inline=True
            )
            
        if type_value in ["all", "messages"]:
            total_messages = sum(message_counts)
            
            embed.add_field(
                name="Messages",
                value=f"Total: **{total_messages}**\nAvg/Day: **{total_messages / (len(stats) / 24):.1f}**",
                inline=True
            )
            
        if type_value in ["all", "voice"]:
            total_voice = sum(voice_minutes)
            
            embed.add_field(
                name="Voice Activity",
                value=f"Total: **{total_voice:.1f}** minutes\nAvg/Day: **{total_voice / (len(stats) / 24):.1f}** min",
                inline=True
            )
            
        # Generate graphs
        if len(timestamps) > 1:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if type_value == "all":
                # Create three subplots for all stats
                fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 15))
                
                # Members graph
                ax1.plot(timestamps, member_counts, 'b-', marker='o')
                ax1.set_title('Member Count')
                ax1.set_ylabel('Members')
                ax1.grid(True)
                
                # Messages graph
                ax2.plot(timestamps, message_counts, 'g-', marker='o')
                ax2.set_title('Message Count')
                ax2.set_ylabel('Messages')
                ax2.grid(True)
                
                # Voice activity graph
                ax3.plot(timestamps, voice_minutes, 'r-', marker='o')
                ax3.set_title('Voice Activity')
                ax3.set_ylabel('Minutes')
                ax3.grid(True)
                
                plt.tight_layout()
                
            elif type_value == "members":
                ax.plot(timestamps, member_counts, 'b-', marker='o')
                ax.set_title('Member Count')
                ax.set_ylabel('Members')
                ax.grid(True)
                
            elif type_value == "messages":
                ax.plot(timestamps, message_counts, 'g-', marker='o')
                ax.set_title('Message Count')
                ax.set_ylabel('Messages')
                ax.grid(True)
                
            elif type_value == "voice":
                ax.plot(timestamps, voice_minutes, 'r-', marker='o')
                ax.set_title('Voice Activity')
                ax.set_ylabel('Minutes')
                ax.grid(True)
                
            # Save the figure to a bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            
            # Create a Discord file from the buffer
            stats_file = discord.File(buf, filename='stats.png')
            
            # Send the embed and image
            await interaction.followup.send(embed=embed, file=stats_file)
            
            # Close the figure to free memory
            plt.close(fig)
            
        else:
            await interaction.followup.send(embed=embed)
            
    # Member join/leave tracking
    @app_commands.command(name="joinleave", description="View member join and leave statistics")
    @app_commands.describe(
        timeframe="The timeframe to show statistics for (default: 30d)"
    )
    @app_commands.choices(timeframe=[
        app_commands.Choice(name="7 Days", value="7d"),
        app_commands.Choice(name="30 Days", value="30d"),
        app_commands.Choice(name="90 Days", value="90d")
    ])
    async def joinleave_command(self, interaction: discord.Interaction,
                              timeframe: Optional[app_commands.Choice[str]] = None):
        """Display member join and leave statistics."""
        await interaction.response.defer()
        
        # Set default value if not provided
        timeframe_value = timeframe.value if timeframe else "30d"
        
        # Calculate the time range
        now = datetime.datetime.now()
        if timeframe_value == "7d":
            from_time = now - datetime.timedelta(days=7)
            time_label = "7 Days"
        elif timeframe_value == "30d":
            from_time = now - datetime.timedelta(days=30)
            time_label = "30 Days"
        elif timeframe_value == "90d":
            from_time = now - datetime.timedelta(days=90)
            time_label = "90 Days"
        else:
            from_time = now - datetime.timedelta(days=30)
            time_label = "30 Days"
            
        # Get all members with their join date
        members = interaction.guild.members
        joins = [m for m in members if m.joined_at and m.joined_at.replace(tzinfo=None) > from_time]
        
        # We don't have leave data stored, but we can approximate with stats if available
        stats = db.get_stats(interaction.guild.id, int(from_time.timestamp()), int(now.timestamp()))
        
        # Count joins by day
        join_counts = defaultdict(int)
        for member in joins:
            join_date = member.joined_at.strftime('%Y-%m-%d')
            join_counts[join_date] += 1
            
        # Create the embed
        embed = await utils.create_embed(
            title=f"Member Join Statistics - Past {time_label}",
            description=f"Statistics for {interaction.guild.name}",
            color=config.EMBED_COLOR,
            timestamp=True
        )
        
        # Add summary
        embed.add_field(
            name="New Members",
            value=f"Total Joins: **{len(joins)}**\nAvg/Day: **{len(joins) / int(timeframe_value[:-1]):.1f}**",
            inline=True
        )
        
        # Generate a graph of joins by day
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Get all dates in the range
        date_range = []
        current_date = from_time
        while current_date <= now:
            date_range.append(current_date.strftime('%Y-%m-%d'))
            current_date += datetime.timedelta(days=1)
            
        # Create the counts list ensuring all dates are included
        counts = [join_counts.get(date, 0) for date in date_range]
        
        # Plot the joins
        ax.bar(date_range, counts, color='green')
        ax.set_title('Member Joins by Day')
        ax.set_ylabel('Number of Joins')
        ax.set_xlabel('Date')
        
        # Handle x-axis labels for longer timeframes
        if len(date_range) > 14:
            # Show only some dates to avoid overcrowding
            step = len(date_range) // 10
            if step < 1:
                step = 1
            plt.xticks(range(0, len(date_range), step), [date_range[i] for i in range(0, len(date_range), step)], rotation=45)
        else:
            plt.xticks(rotation=45)
            
        plt.tight_layout()
        
        # Save the figure to a bytes buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Create a Discord file from the buffer
        stats_file = discord.File(buf, filename='joins.png')
        
        # Send the embed and image
        await interaction.followup.send(embed=embed, file=stats_file)
        
        # Close the figure to free memory
        plt.close(fig)
        
    # Active users command
    @app_commands.command(name="activeusers", description="View the most active users in the server")
    @app_commands.describe(
        timeframe="The timeframe to show statistics for (default: 7d)"
    )
    @app_commands.choices(timeframe=[
        app_commands.Choice(name="24 Hours", value="24h"),
        app_commands.Choice(name="7 Days", value="7d"),
        app_commands.Choice(name="30 Days", value="30d")
    ])
    async def activeusers_command(self, interaction: discord.Interaction,
                                timeframe: Optional[app_commands.Choice[str]] = None):
        """Display the most active users based on message count."""
        # This is a placeholder since we don't track individual user message counts in this implementation
        # In a real implementation, you would track this data in the database
        
        await interaction.response.send_message("This command is not fully implemented in the current version. It would require tracking individual user message counts in the database.", ephemeral=True)

    # Error handlers
    @serverstats_command.error
    @joinleave_command.error
    @activeusers_command.error
    async def serverstats_error(self, interaction: discord.Interaction, error):
        logger.error(f"Error in server stats command: {error}")
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServerStats(bot))
