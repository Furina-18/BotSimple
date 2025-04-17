"""
Help command functionality for the Discord bot.
Provides detailed help information about available commands.
"""
import discord
from discord import app_commands
from discord.ext import commands
import logging
from typing import Optional, Dict, List

import config
import utils

logger = logging.getLogger(__name__)

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("Help cog loaded")
        
    @app_commands.command(name="help", description="Show help for bot commands")
    @app_commands.describe(
        command="Specific command to get help for"
    )
    async def help_command(self, interaction: discord.Interaction, command: Optional[str] = None):
        """Show help information about available commands."""
        await interaction.response.defer()
        
        if command:
            # Show help for a specific command
            await self.show_command_help(interaction, command)
        else:
            # Show general help with categories
            await self.show_general_help(interaction)
            
    async def show_general_help(self, interaction: discord.Interaction):
        """Show general help with command categories."""
        # Create an embed for the help message
        embed = await utils.create_embed(
            title=f"{self.bot.user.name} Help",
            description=f"Here's a list of available commands. Use `/help command` for more details on a specific command.",
            color=config.EMBED_COLOR,
            thumbnail=self.bot.user.display_avatar.url
        )
        
        # Categorize commands by cog
        commands_by_category = {}
        
        for cmd in self.bot.tree.get_commands():
            # Skip hidden commands
            if getattr(cmd, "hidden", False):
                continue
                
            # Get the cog name from the command
            cog_name = "Miscellaneous"
            for cog in self.bot.cogs.values():
                if any(c.name == cmd.name for c in cog.get_app_commands()):
                    cog_name = cog.__class__.__name__
                    break
                    
            # Add to the category
            if cog_name not in commands_by_category:
                commands_by_category[cog_name] = []
            commands_by_category[cog_name].append(cmd)
            
        # Add fields for each category
        for category, cmds in sorted(commands_by_category.items()):
            # Skip empty categories
            if not cmds:
                continue
                
            # Create a command list string
            command_list = ", ".join(f"`/{cmd.name}`" for cmd in sorted(cmds, key=lambda x: x.name))
            
            embed.add_field(
                name=category,
                value=command_list,
                inline=False
            )
            
        # Add footer with info about command prefix
        embed.set_footer(text=f"Type {config.PREFIX}help or /help command for more info on a command.")
        
        await interaction.followup.send(embed=embed)
        
    async def show_command_help(self, interaction: discord.Interaction, command_name: str):
        """Show detailed help for a specific command."""
        # Find the command
        cmd = None
        for c in self.bot.tree.get_commands():
            if c.name.lower() == command_name.lower():
                cmd = c
                break
                
        if not cmd:
            return await interaction.followup.send(f"Command `/{command_name}` not found.", ephemeral=True)
            
        # Create an embed for the command help
        embed = await utils.create_embed(
            title=f"Help: /{cmd.name}",
            description=cmd.description or "No description provided.",
            color=config.EMBED_COLOR,
            thumbnail=self.bot.user.display_avatar.url
        )
        
        # Add parameters if any
        if hasattr(cmd, "parameters") and cmd.parameters:
            params_text = ""
            for param in cmd.parameters:
                required = "Required" if param.required else "Optional"
                description = param.description or "No description"
                params_text += f"**{param.name}** ({required}): {description}\n"
                
            if params_text:
                embed.add_field(name="Parameters", value=params_text, inline=False)
                
        # Add examples
        example = f"/{cmd.name}"
        if hasattr(cmd, "parameters") and cmd.parameters:
            for param in cmd.parameters:
                if param.required:
                    example += f" <{param.name}>"
                else:
                    example += f" [{param.name}]"
                    
        embed.add_field(name="Usage", value=f"`{example}`", inline=False)
        
        # Add permissions if known
        perms = []
        for check in getattr(cmd, "checks", []):
            if hasattr(check, "permissions") and check.permissions:
                perms.extend(check.permissions)
                
        if perms:
            perms_text = ", ".join(f"`{p}`" for p in perms)
            embed.add_field(name="Required Permissions", value=perms_text, inline=False)
            
        await interaction.followup.send(embed=embed)
        
    @commands.command(name="help", description="Show help for bot commands")
    async def legacy_help_command(self, ctx, command: Optional[str] = None):
        """Legacy help command for prefix-based invocation."""
        # Create a mock interaction for reusing slash command logic
        class MockInteraction:
            async def followup(self, **kwargs):
                return await ctx.send(**kwargs)
                
            async def response(self):
                class MockResponse:
                    async def defer(self, *args, **kwargs):
                        pass
                return MockResponse()
                
        mock_interaction = MockInteraction()
        mock_interaction.followup.send = ctx.send
        mock_interaction.response.defer = lambda: None
        
        if command:
            await self.show_command_help(mock_interaction, command)
        else:
            await self.show_general_help(mock_interaction)

    # Error handler
    @help_command.error
    async def help_error(self, interaction: discord.Interaction, error):
        logger.error(f"Error in help command: {error}")
        await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))
