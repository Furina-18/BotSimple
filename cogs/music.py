import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.repeat_mode = {}

    def get_queue(self, guild_id):
        return self.queues.setdefault(guild_id, asyncio.Queue())

    @app_commands.command(name="join", description="Bot joins your voice channel")
    async def join(self, interaction: discord.Interaction):
        vc = interaction.user.voice
        if not vc or not vc.channel:
            return await interaction.response.send_message("You're not in a voice channel!", ephemeral=True)
        await vc.channel.connect()
        await interaction.response.send_message(f"✅ Joined {vc.channel.name}!")

    @app_commands.command(name="leave", description="Bot leaves the voice channel")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 Left the voice channel.")
        else:
            await interaction.response.send_message("❌ I'm not in a voice channel.")

    @app_commands.command(name="play", description="Play a song from YouTube URL")
    async def play(self, interaction: discord.Interaction, url: str):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("❌ I'm not in a voice channel.")
            return

        queue = self.get_queue(interaction.guild.id)
        await queue.put(url)
        await interaction.response.send_message(f"🎶 Added to queue: {url}")

        if not vc.is_playing():
            await self.start_playing(interaction, vc, queue)

    async def start_playing(self, interaction, vc, queue):
        while not queue.empty():
            url = await queue.get()
            ydl_opts = {'format': 'bestaudio', 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                source = await discord.FFmpegOpusAudio.from_probe(info['url'], method='fallback')
                vc.play(source)

                await interaction.followup.send(f"🎵 Now playing: {info.get('title')}")
                while vc.is_playing():
                    await asyncio.sleep(1)

    @app_commands.command(name="pause", description="Pause the current track")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused.")
        else:
            await interaction.response.send_message("❌ Nothing is playing.")

    @app_commands.command(name="resume", description="Resume paused music")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed.")
        else:
            await interaction.response.send_message("❌ Nothing to resume.")

    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped.")
        else:
            await interaction.response.send_message("❌ Nothing is playing.")

async def setup(bot):
    await bot.add_cog(Music(bot))
