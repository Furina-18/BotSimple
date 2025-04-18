import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from youtube_dl import YoutubeDL

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.is_playing = False

    # Join the user's voice channel
    @app_commands.command(name="join", description="Bot joins your voice channel")
    async def join(self, interaction: discord.Interaction):
        voice_channel = interaction.user.voice.channel if interaction.user.voice else None

        if not voice_channel:
            return await interaction.response.send_message("❌ You must be in a voice channel to use this.", ephemeral=True)

        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(voice_channel)
        else:
            await voice_channel.connect()

        await interaction.response.send_message(f"🔊 Joined {voice_channel.name}!", ephemeral=True)

    # Play a song from a YouTube URL
    @app_commands.command(name="play", description="Play music from a YouTube URL")
    async def play(self, interaction: discord.Interaction, url: str):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("❌ Bot is not connected to any voice channel.", ephemeral=True)

        YDL_OPTIONS = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
        }

        FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn',
        }

        vc = interaction.guild.voice_client

        # Extract audio URL using youtube_dl
        with YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            url2 = info['formats'][0]['url']
            song_title = info['title']

        if not self.is_playing:
            self.is_playing = True
            await vc.play(discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS), after=lambda e: self.after_playing(interaction))
            await interaction.response.send_message(f"🎶 Now playing: {song_title}")
        else:
            self.queue.append(url2)
            await interaction.response.send_message(f"✅ Added to queue: {song_title}")

    # After song finishes playing, check for next in queue
    def after_playing(self, interaction):
        if len(self.queue) > 0:
            next_song_url = self.queue.pop(0)
            vc = interaction.guild.voice_client
            asyncio.run_coroutine_threadsafe(vc.play(discord.FFmpegPCMAudio(next_song_url), after=lambda e: self.after_playing(interaction)), self.bot.loop)
        else:
            self.is_playing = False
            vc = interaction.guild.voice_client
            asyncio.run_coroutine_threadsafe(vc.disconnect(), self.bot.loop)

    # Skip the current song
    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("❌ I'm not connected to a voice channel.", ephemeral=True)

        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.stop()
            await interaction.response.send_message("⏭️ Skipped the current song.")
        else:
            await interaction.response.send_message("❌ No song is currently playing.", ephemeral=True)

    # Pause the current song
    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("❌ I'm not connected to a voice channel.", ephemeral=True)

        if interaction.guild.voice_client.is_playing():
            interaction.guild.voice_client.pause()
            await interaction.response.send_message("⏸️ Paused the current song.")
        else:
            await interaction.response.send_message("❌ No song is currently playing.", ephemeral=True)

    # Resume the paused song
    @app_commands.command(name="resume", description="Resume the paused song")
    async def resume(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("❌ I'm not connected to a voice channel.", ephemeral=True)

        if interaction.guild.voice_client.is_paused
