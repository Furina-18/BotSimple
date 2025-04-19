import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp, asyncio, spotipy, os
from spotipy.oauth2 import SpotifyClientCredentials

FFMPEG_OPTS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn"
}
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET")
))

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repeat = False
        self.last_url = None
        self.last_guild = None

    async def join_vc(self, interaction):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Join a VC first.", ephemeral=True)
            return False
        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if vc and vc.channel != channel:
            await vc.move_to(channel)
        elif not vc:
            await channel.connect()
        return True

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

    @app_commands.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction):
        if await self.join_vc(interaction):
            await interaction.response.send_message("✅ Joined VC.")

    @app_commands.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("👋 Left VC.")
        else:
            await interaction.response.send_message("❌ Not in a VC.", ephemeral=True)

    @app_commands.command(name="play", description="Play from YouTube or Spotify")
    @app_commands.describe(query="YouTube URL, Spotify link, or search term")
    async def play(self, interaction: discord.Interaction, query: str):
        if not await self.join_vc(interaction): return
        await interaction.response.defer()
        if "spotify.com/track" in query:
            query = self.get_spotify(query)
        url, title, page = self.extract_url(query)
        self.last_url = url
        self.last_guild = interaction.guild
        vc = interaction.guild.voice_client
        if vc.is_playing(): vc.stop()
        vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTS), after=lambda e: self.after_play(interaction.guild))
        await interaction.followup.send(f"▶️ Now playing **{title}**", embed=discord.Embed().set_image(url=page))

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
