"""
AI functionality for the Discord bot.
Provides AI-powered conversation capabilities via OpenAI API.
"""
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import datetime
import logging
import json
import os
import time
from typing import Optional, List, Dict, Any

from openai import OpenAI
import config
import utils
from database import db

logger = logging.getLogger(__name__)

# Initialize OpenAI API client
client = OpenAI(api_key=config.OPENAI_API_KEY)

class AI(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ongoing_conversations = {}
        
    @commands.Cog.listener()
    async def on_ready(self):
        logger.info("AI cog loaded")
        
    # Helper methods
    async def generate_ai_response(self, messages, max_tokens=1000):
        """Generate AI response using OpenAI API."""
        if not config.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is not configured. Please set OPENAI_API_KEY in the environment variables.")
            
        try:
            # Use the newest OpenAI model gpt-4o which was released May 13, 2024.
            # Do not change this unless explicitly requested by the user
            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7
                )
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise ValueError(f"OpenAI API error: {e}")
            
    async def get_conversation_history(self, user_id, channel_id):
        """Get conversation history from the database."""
        conversation = db.get_conversation(user_id, channel_id)
        if conversation:
            return conversation['conversation']
        return []
        
    async def save_conversation_history(self, user_id, guild_id, channel_id, messages):
        """Save conversation history to the database."""
        timestamp = int(time.time())
        db.save_conversation(user_id, guild_id, channel_id, messages, timestamp)
        
    # Command to start a conversation with the AI
    @app_commands.command(name="ask", description="Ask the AI a question")
    @app_commands.describe(
        question="Your question or message for the AI"
    )
    async def ask_command(self, interaction: discord.Interaction, question: str):
        """Ask the AI a question and get a response."""
        # Defer the response to allow time for processing
        await interaction.response.defer()
        
        # Check if OpenAI API key is configured
        if not config.OPENAI_API_KEY:
            return await interaction.followup.send("AI functionality is not configured. Please set the OPENAI_API_KEY environment variable.")
            
        # Sanitize the question to prevent prompt injection
        question = utils.sanitize_text(question)
        
        try:
            # Get conversation history
            conversation = await self.get_conversation_history(interaction.user.id, interaction.channel.id)
            
            # If no history, start a new conversation
            if not conversation:
                conversation = [
                    {"role": "system", "content": "You are a helpful AI assistant in a Discord server."},
                ]
                
            # Add user message to conversation
            conversation.append({"role": "user", "content": question})
            
            # Generate response
            response_text = await self.generate_ai_response(conversation)
            
            # Add AI response to conversation
            conversation.append({"role": "assistant", "content": response_text})
            
            # Save conversation history
            await self.save_conversation_history(
                interaction.user.id, 
                interaction.guild.id, 
                interaction.channel.id, 
                conversation
            )
            
            # Send the response
            # Split into chunks if it's too long
            if len(response_text) > 2000:
                chunks = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await interaction.followup.send(chunk)
                    else:
                        await interaction.channel.send(chunk)
            else:
                await interaction.followup.send(response_text)
                
        except ValueError as e:
            await interaction.followup.send(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Error in ask command: {e}")
            await interaction.followup.send(f"An error occurred while processing your request. Please try again later.")
            
    @app_commands.command(name="chat", description="Chat with the AI in a continuous conversation")
    @app_commands.describe(
        message="Your message for the AI"
    )
    async def chat_command(self, interaction: discord.Interaction, message: str):
        """Start or continue a chat with the AI."""
        # Defer the response to allow time for processing
        await interaction.response.defer()
        
        # Check if OpenAI API key is configured
        if not config.OPENAI_API_KEY:
            return await interaction.followup.send("AI functionality is not configured. Please set the OPENAI_API_KEY environment variable.")
            
        # Sanitize the message to prevent prompt injection
        message = utils.sanitize_text(message)
        
        try:
            # Get conversation history
            conversation = await self.get_conversation_history(interaction.user.id, interaction.channel.id)
            
            # If no history, start a new conversation
            if not conversation:
                conversation = [
                    {"role": "system", "content": "You are a helpful AI assistant in a Discord server. You are having a casual conversation."},
                ]
                # Notify the user that this is a new conversation
                await interaction.followup.send("Starting a new conversation. You can use `/chat` to continue this conversation or `/endchat` to end it.")
                
            # Add user message to conversation
            conversation.append({"role": "user", "content": message})
            
            # Generate response
            response_text = await self.generate_ai_response(conversation)
            
            # Add AI response to conversation
            conversation.append({"role": "assistant", "content": response_text})
            
            # Trim the conversation if it gets too long (keep last 20 messages)
            if len(conversation) > 22:  # 20 messages + system prompt + new message
                # Always keep the system message
                conversation = [conversation[0]] + conversation[-20:]
                
            # Save conversation history
            await self.save_conversation_history(
                interaction.user.id, 
                interaction.guild.id, 
                interaction.channel.id, 
                conversation
            )
            
            # Create an embed for the response
            embed = await utils.create_embed(
                title=f"AI Chat with {interaction.user.display_name}",
                description=response_text[:4000] if len(response_text) > 4000 else response_text,  # Discord embed limits
                color=config.EMBED_COLOR,
                footer={"text": "Use /chat to continue this conversation or /endchat to end it."}
            )
            
            await interaction.followup.send(embed=embed)
            
            # If the response is too long, send the rest as a follow-up
            if len(response_text) > 4000:
                remaining = response_text[4000:]
                chunks = [remaining[i:i+2000] for i in range(0, len(remaining), 2000)]
                for chunk in chunks:
                    await interaction.channel.send(chunk)
                    
        except ValueError as e:
            await interaction.followup.send(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Error in chat command: {e}")
            await interaction.followup.send(f"An error occurred while processing your request. Please try again later.")
            
    @app_commands.command(name="endchat", description="End your current AI conversation")
    async def endchat_command(self, interaction: discord.Interaction):
        """End the current AI conversation and clear history."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Clear the conversation from the database
            db.clear_conversation(interaction.user.id, interaction.channel.id)
            
            await interaction.followup.send("Your AI conversation has been ended. Start a new one anytime with `/chat`.", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in endchat command: {e}")
            await interaction.followup.send(f"An error occurred while ending your conversation. Please try again later.", ephemeral=True)
            
    @app_commands.command(name="summarize", description="Have the AI summarize recent messages in the channel")
    @app_commands.describe(
        messages="Number of messages to summarize (default: 20, max: 100)"
    )
    async def summarize_command(self, interaction: discord.Interaction, messages: Optional[int] = 20):
        """Summarize recent messages in the channel."""
        # Limit the number of messages
        messages = min(max(5, messages), 100)
        
        # Defer the response to allow time for processing
        await interaction.response.defer()
        
        # Check if OpenAI API key is configured
        if not config.OPENAI_API_KEY:
            return await interaction.followup.send("AI functionality is not configured. Please set the OPENAI_API_KEY environment variable.")
            
        try:
            # Fetch the messages
            channel_messages = []
            async for message in interaction.channel.history(limit=messages):
                # Skip bot messages and commands
                if message.author.bot or message.content.startswith(config.PREFIX):
                    continue
                    
                channel_messages.append(f"{message.author.display_name}: {message.content}")
                
            if not channel_messages:
                return await interaction.followup.send("No messages found to summarize.")
                
            # Reverse the messages to get chronological order
            channel_messages.reverse()
            
            # Create the prompt
            prompt = f"Please summarize the following conversation:\n\n{''.join(channel_messages)}"
            
            # Create the messages for the API
            api_messages = [
                {"role": "system", "content": "You are a helpful AI assistant that summarizes conversations. Provide a concise but comprehensive summary."},
                {"role": "user", "content": prompt}
            ]
            
            # Generate summary
            summary = await self.generate_ai_response(api_messages)
            
            # Create an embed for the response
            embed = await utils.create_embed(
                title=f"Summary of Last {len(channel_messages)} Messages",
                description=summary[:4000] if len(summary) > 4000 else summary,  # Discord embed limits
                color=config.EMBED_COLOR,
                footer={"text": f"Requested by {interaction.user.display_name}"},
                timestamp=True
            )
            
            await interaction.followup.send(embed=embed)
            
            # If the summary is too long, send the rest as a follow-up
            if len(summary) > 4000:
                remaining = summary[4000:]
                chunks = [remaining[i:i+2000] for i in range(0, len(remaining), 2000)]
                for chunk in chunks:
                    await interaction.channel.send(chunk)
                    
        except ValueError as e:
            await interaction.followup.send(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Error in summarize command: {e}")
            await interaction.followup.send(f"An error occurred while processing your request. Please try again later.")
            
    @app_commands.command(name="imagine", description="Generate a description of an imaginary image based on your prompt")
    @app_commands.describe(
        prompt="What you want the AI to imagine and describe"
    )
    async def imagine_command(self, interaction: discord.Interaction, prompt: str):
        """Generate a detailed description of an imaginary image."""
        # Defer the response to allow time for processing
        await interaction.response.defer()
        
        # Check if OpenAI API key is configured
        if not config.OPENAI_API_KEY:
            return await interaction.followup.send("AI functionality is not configured. Please set the OPENAI_API_KEY environment variable.")
            
        # Sanitize the prompt
        prompt = utils.sanitize_text(prompt)
        
        try:
            # Create the messages for the API
            api_messages = [
                {"role": "system", "content": "You are a creative AI that generates detailed, vivid descriptions of imaginary images based on prompts. Your descriptions should be visual, descriptive, and engaging."},
                {"role": "user", "content": f"Imagine and describe in detail an image of: {prompt}"}
            ]
            
            # Generate description
            description = await self.generate_ai_response(api_messages)
            
            # Create an embed for the response
            embed = await utils.create_embed(
                title=f"Imagining: {prompt}",
                description=description[:4000] if len(description) > 4000 else description,  # Discord embed limits
                color=config.EMBED_COLOR,
                footer={"text": f"Requested by {interaction.user.display_name}"},
                timestamp=True
            )
            
            await interaction.followup.send(embed=embed)
            
            # If the description is too long, send the rest as a follow-up
            if len(description) > 4000:
                remaining = description[4000:]
                chunks = [remaining[i:i+2000] for i in range(0, len(remaining), 2000)]
                for chunk in chunks:
                    await interaction.channel.send(chunk)
                    
        except ValueError as e:
            await interaction.followup.send(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Error in imagine command: {e}")
            await interaction.followup.send(f"An error occurred while processing your request. Please try again later.")
            
    @app_commands.command(name="translate", description="Translate text to another language")
    @app_commands.describe(
        text="The text to translate",
        language="The target language"
    )
    async def translate_command(self, interaction: discord.Interaction, text: str, language: str):
        """Translate text to another language using AI."""
        # Defer the response to allow time for processing
        await interaction.response.defer()
        
        # Check if OpenAI API key is configured
        if not config.OPENAI_API_KEY:
            return await interaction.followup.send("AI functionality is not configured. Please set the OPENAI_API_KEY environment variable.")
            
        # Sanitize the text
        text = utils.sanitize_text(text)
        
        try:
            # Create the messages for the API
            api_messages = [
                {"role": "system", "content": f"You are a helpful translation assistant. Translate the given text to {language}."},
                {"role": "user", "content": text}
            ]
            
            # Generate translation
            translation = await self.generate_ai_response(api_messages)
            
            # Create an embed for the response
            embed = await utils.create_embed(
                title=f"Translation to {language}",
                description=translation[:4000] if len(translation) > 4000 else translation,  # Discord embed limits
                color=config.EMBED_COLOR,
                fields=[{"name": "Original Text", "value": text[:1024] if len(text) > 1024 else text, "inline": False}],
                footer={"text": f"Requested by {interaction.user.display_name}"},
                timestamp=True
            )
            
            await interaction.followup.send(embed=embed)
            
            # If the translation is too long, send the rest as a follow-up
            if len(translation) > 4000:
                remaining = translation[4000:]
                chunks = [remaining[i:i+2000] for i in range(0, len(remaining), 2000)]
                for chunk in chunks:
                    await interaction.channel.send(chunk)
                    
        except ValueError as e:
            await interaction.followup.send(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Error in translate command: {e}")
            await interaction.followup.send(f"An error occurred while processing your request. Please try again later.")

    # Error handlers
    @ask_command.error
    @chat_command.error
    @endchat_command.error
    @summarize_command.error
    @imagine_command.error
    @translate_command.error
    async def ai_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.errors.CommandInvokeError):
            error = error.original
            
        logger.error(f"Error in AI command: {error}")
        await interaction.followup.send(f"An error occurred: {str(error)}")

async def setup(bot):
    await bot.add_cog(AI(bot))
