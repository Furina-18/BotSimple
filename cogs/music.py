import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from db import db_manager  # Import the DatabaseManager

YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist': 'True'}
FFMPEG_OPTIONS = {'options': '-vn'}

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = {}
        self.current_song = {}

    def yt_search(self, query):
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                return {'source': info['url'], 'title': info['title']}
            except Exception as e:
                print(f"Error in yt_search: {e}")
                return None

    def get_spotify_tracks(self, url):
        results = []
        try:
            if "track" in url:
                track = sp.track(url)
                results.append(f"{track['name']} {track['artists'][0]['name']}")
            elif "playlist" in url:
                playlist = sp.playlist_tracks(url)
                for item in playlist['items']:
                    track = item['track']
                    results.append(f"{track['name']} {track['artists'][0]['name']}")
        except Exception as e:
            print(f"Spotify error: {e}")
        return results

    async def play_next(self, ctx):
        guild_id = ctx.guild.id
        if guild_id not in self.queue:
            return
        if self.queue[guild_id]:
            data = self.queue[guild_id].pop(0)
            self.current_song[guild_id] = data
            try:
                ctx.voice_client.play(
                    discord.FFmpegPCMAudio(data['source'], **FFMPEG_OPTIONS),
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.play_next(ctx), self.bot.loop
                    )
                )
            except Exception as e:
                print(f"Error playing next song: {e}")

    async def ensure_voice(self, interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("🔈 Join a voice channel first.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="join", description="Join your voice channel.")
    async def join(self, interaction: discord.Interaction):
        if not await self.ensure_voice(interaction):
            return
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client is None:
            await channel.connect()
            await interaction.response.send_message(f"✅ Joined {channel.name}")
        else:
            await interaction.response.send_message("⚠️ I'm already in a voice channel.")

    @app_commands.command(name="leave", description="Leave the voice channel.")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            self.queue.pop(interaction.guild.id, None)
            await interaction.response.send_message("👋 Disconnected.")
        else:
            await interaction.response.send_message("❌ I'm not in a voice channel.")

    @app_commands.command(name="play", description="Play a YouTube/Spotify song or playlist.")
    @app_commands.describe(url="YouTube/Spotify link or search term")
    async def play(self, interaction: discord.Interaction, url: str):
        if not await self.ensure_voice(interaction):
            return

        vc = interaction.guild.voice_client
        if not vc:
            await interaction.user.voice.channel.connect()
            vc = interaction.guild.voice_client

        guild_id = interaction.guild.id
        self.queue.setdefault(guild_id, [])

        # Spotify or YouTube?
        try:
            if "spotify.com" in url:
                songs = self.get_spotify_tracks(url)
                if not songs:
                    await interaction.response.send_message("⚠️ Couldn't fetch Spotify tracks.")
                    return
                for song_name in songs:
                    result = self.yt_search(song_name)
                    if result:
                        self.queue[guild_id].append(result)
                await interaction.response.send_message(f"🎶 Added {len(songs)} track(s) from Spotify.")
            else:
                result = self.yt_search(url)
                if not result:
                    await interaction.response.send_message("❌ Couldn’t find the song.")
                    return
                self.queue[guild_id].append(result)
                await interaction.response.send_message(f"🎧 Queued: **{result['title']}**")

            await db_manager.set_queue(guild_id, [song['title'] for song in self.queue[guild_id]])

            if not vc.is_playing():
                song = self.queue[guild_id].pop(0)
                self.current_song[guild_id] = song
                vc.play(
                    discord.FFmpegPCMAudio(song['source'], **FFMPEG_OPTIONS),
                    after=lambda e: asyncio.run_coroutine_threadsafe(
                        self.play_next(interaction), self.bot.loop
                    )
                )
                await interaction.followup.send(f"▶️ Now playing: **{song['title']}**")
        except Exception as e:
            print(f"Error in play command: {e}")
            await interaction.response.send_message("❌ An error occurred while trying to play the song.")

    @app_commands.command(name="queue", description="Show current music queue.")
    async def show_queue(self, interaction: discord.Interaction):
        try:
            q = await db_manager.get_queue(interaction.guild.id)
            if not q:
                await interaction.response.send_message("🪹 Queue is empty.")
            else:
                msg = "\n".join([f"{idx+1}. {song}" for idx, song in enumerate(q)])
                await interaction.response.send_message(f"🎶 Queue:\n{msg}")
        except Exception as e:
            print(f"Error fetching queue: {e}")
            await interaction.response.send_message("❌ Could not retrieve the queue.")

    @app_commands.command(name="skip", description="Skip the current song.")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        try:
            if vc and vc.is_playing():
                vc.stop()
                await interaction.response.send_message("⏭️ Skipped.")
            else:
                await interaction.response.send_message("❌ Nothing is playing.")
        except Exception as e:
            print(f"Error skipping song: {e}")
            await interaction.response.send_message("❌ An error occurred while trying to skip the song.")

    @app_commands.command(name="pause", description="Pause the music.")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        try:
            if vc and vc.is_playing():
                vc.pause()
                await interaction.response.send_message("⏸️ Paused.")
            else:
                await interaction.response.send_message("❌ Nothing to pause.")
        except Exception as e:
            print(f"Error pausing music: {e}")
            await interaction.response.send_message("❌ An error occurred while trying to pause the music.")

    @app_commands.command(name="resume", description="Resume paused music.")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        try:
            if vc and vc.is_paused():
                vc.resume()
                await interaction.response.send_message("▶️ Resumed.")
            else:
                await interaction.response.send_message("❌ Nothing to resume.")
        except Exception as e:
            print(f"Error resuming music: {e}")
            await interaction.response.send_message("❌ An error occurred while trying to resume the music.")

    @app_commands.command(name="repeat", description="Set repeat mode.")
    @app_commands.describe(mode="none | once | infinite")
    async def repeat(self, interaction: discord.Interaction, mode: str):
        try:
            mode = mode.lower()
            if mode not in ["none", "once", "infinite"]:
                await interaction.response.send_message("❌ Invalid mode. Use: none, once, infinite")
                return
            await db_manager.set_repeat_mode(interaction.guild.id, mode)
            await interaction.response.send_message(f"🔁 Repeat mode set to `{mode}`.")
        except Exception as e:
            print(f"Error setting repeat mode: {e}")
            await interaction.response.send_message("❌ An error occurred while setting repeat mode.")
