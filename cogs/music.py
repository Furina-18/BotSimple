import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repeat = False
        self.last_url = None
        self.last_interaction = None

    async def join_voice(self, interaction: discord.Interaction):
        try:
            if interaction.user.voice:
                channel = interaction.user.voice.channel
                vc = interaction.guild.voice_client
                if vc is None or not vc.is_connected():
                    await channel.connect()
                elif vc.channel != channel:
                    await vc.move_to(channel)
                return True
            else:
                await interaction.response.send_message("❌ You must be in a voice channel.", ephemeral=True)
                return False
        except Exception as e:
            await interaction.response.send_message(f"⚠️ Error: {e}", ephemeral=True)
            return False

    def get_youtube_url(self, query: str):
        ydl_opts = {'format': 'bestaudio'}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                return info['url'], info.get('title', 'Unknown'), info.get('webpage_url', query)
            except Exception as e:
                print("YouTube search error:", e)
                return None, None, None

    def get_spotify_track(self, link: str):
        try:
            if "track" in link:
                track = sp.track(link)
                name = track['name']
                artist = track['artists'][0]['name']
                return f"{name} {artist}"
        except Exception as e:
            print("Spotify error:", e)
        return None

    @app_commands.command(name="join", description="Join the voice channel")
    async def join(self, interaction: discord.Interaction):
        if await self.join_voice(interaction):
            await interaction.response.send_message("✅ Joined your voice channel!")

    @app_commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("👋 Left the voice channel.")
        else:
            await interaction.response.send_message("❌ I'm not connected to a voice channel.")

    @app_commands.command(name="play", description="Play music from YouTube or Spotify")
    @app_commands.describe(query="YouTube/Spotify link or search term")
    async def play(self, interaction: discord.Interaction, query: str):
        if not await self.join_voice(interaction):
            return

        await interaction.response.defer()

        if "spotify.com/track" in query:
            query = self.get_spotify_track(query)
            if not query:
                await interaction.followup.send("❌ Could not fetch song from Spotify.")
                return

        url, title, page_url = self.get_youtube_url(query)
        if not url:
            await interaction.followup.send("❌ Could not find the song.")
            return

        vc = interaction.guild.voice_client
        if vc.is_playing():
            vc.stop()

        self.last_url = url
        self.last_interaction = interaction

        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=lambda e: self._after_play(interaction.guild))

        await interaction.followup.send(f"🎶 Now playing: **[{title}]({page_url})**")

    def _after_play(self, guild):
        if self.repeat and self.last_url:
            coro = self._repeat_play(guild, self.last_url)
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print("Repeat error:", e)

    async def _repeat_play(self, guild, url):
        await asyncio.sleep(1)
        vc = guild.voice_client
        if vc and not vc.is_playing():
            vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS), after=lambda e: self._after_play(guild))

    @app_commands.command(name="pause", description="Pause the music")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Music paused.")
        else:
            await interaction.response.send_message("❌ No music is playing.")

    @app_commands.command(name="resume", description="Resume the music")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Music resumed.")
        else:
            await interaction.response.send_message("❌ No music is paused.")

    @app_commands.command(name="stop", description="Stop the music")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏹️ Music stopped.")
        else:
            await interaction.response.send_message("❌ Nothing to stop.")

    @app_commands.command(name="repeat", description="Toggle repeat (infinite) mode")
    async def repeat(self, interaction: discord.Interaction):
        self.repeat = not self.repeat
        await interaction.response.send_message(f"🔁 Repeat mode is now {'enabled' if self.repeat else 'disabled'}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
