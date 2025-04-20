import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp, asyncio, spotipy, os
import wavelink
from spotipy.oauth2 import SpotifyClientCredentials
from utils.spotify import get_spotify_client

sp = get_spotify_client()


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repeat = False
        self.last_url = None
        self.last_guild = None

   class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def ensure_voice(self, interaction: discord.Interaction):
        """Ensure bot connects to a voice channel if not already."""
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You must be in a voice channel!", ephemeral=True)
            return None

        channel = interaction.user.voice.channel
        node = wavelink.NodePool.get_node()

        if not interaction.guild.voice_client:
            vc: wavelink.Player = await channel.connect(cls=wavelink.Player)
        else:
            vc: wavelink.Player = interaction.guild.voice_client

        return vc
    def extract_url(self, query):
        with yt_dlp.YoutubeDL({"format":"bestaudio", "noplaylist":"True"}) as ydl:
            info = ydl.extract_info(query, download=False)
            if "entries" in info: info = info["entries"][0]
            return info["url"], info.get("title","Unknown"), info.get("webpage_url",query)

    def get_spotify(self, link):
        track = sp.track(link)
        return f"{track['name']} {track['artists'][0]['name']}"

    def after_play(self, guild):
        if self.repeat and self.last_url:
            asyncio.run_coroutine_threadsafe(self._replay(guild), self.bot.loop)

    async def _replay(self, guild):
        await asyncio.sleep(1)
        vc = guild.voice_client
        if vc and not vc.is_playing():
            vc.play(discord.FFmpegPCMAudio(self.last_url, **FFMPEG_OPTS), after=lambda e: self.after_play(guild))

      @app_commands.command(name="join", description="Bot joins your voice channel.")
    async def join(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        vc = await self.ensure_voice(interaction)
        if vc:
            await interaction.followup.send(f"✅ Joined `{vc.channel.name}`")

    @app_commands.command(name="leave", description="Bot leaves the voice channel.")
    async def leave(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        vc: wavelink.Player = interaction.guild.voice_client
        if not vc:
            await interaction.followup.send("❌ I'm not connected to a voice channel.")
            return
        await vc.disconnect()
        await interaction.followup.send("👋 Disconnected from the voice channel.")

      @app_commands.command(name="youtube_play", description="Play a YouTube video by URL or search.")
    async def youtube_play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        vc = await self.ensure_voice(interaction)
        if not vc:
            return

        # Direct URL or YouTube search
        if not re.match(r'https?://', query):
            query = f'ytsearch:{query}'

        tracks = await wavelink.YouTubeTrack.search(query)
        if not tracks:
            await interaction.followup.send("No tracks found.")
            return

        track = tracks[0]
        await vc.play(track)
        await interaction.followup.send(f"Now playing: **{track.title}**")

    @app_commands.command(name="spotify_play", description="Play a Spotify track by searching it on YouTube.")
    async def spotify_play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        vc = await self.ensure_voice(interaction)
        if not vc:
            return

        # You can improve this using Spotipy to get exact metadata.
        query = f"ytsearch:{query}"
        tracks = await wavelink.YouTubeTrack.search(query)
        if not tracks:
            await interaction.followup.send("No related tracks found on YouTube.")
            return

        track = tracks[0]
        await vc.play(track)
        await interaction.followup.send(f"Now playing (from Spotify): **{track.title}**")


    @app_commands.command(name="pause", description="Pause playback")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause(); await interaction.response.send_message("⏸️ Paused.")
        else:
            await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume(); await interaction.response.send_message("▶️ Resumed.")
        else:
            await interaction.response.send_message("❌ Not paused.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop playback")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            vc.stop(); await interaction.response.send_message("⏹️ Stopped.")
        else:
            await interaction.response.send_message("❌ Nothing to stop.", ephemeral=True)

    @app_commands.command(name="repeat", description="Toggle infinite repeat")
    async def repeat(self, interaction: discord.Interaction):
        self.repeat = not self.repeat
        await interaction.response.send_message(f"🔁 Repeat {'enabled' if self.repeat else 'disabled'}.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
