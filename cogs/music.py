import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from collections import deque
import yt_dlp
import asyncio


TOKEN = 'YOUR_BOT_TOKEN'


music_queue = {}
repeat_count = {}
current_url = {}
is_repeating_forever = {}
volume_level = {}

default_volume = 0.5

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_guild_data(self, guild_id):
        music_queue.setdefault(guild_id, [])
        repeat_count.setdefault(guild_id, 0)
        current_url.setdefault(guild_id, None)
        is_repeating_forever.setdefault(guild_id, False)
        volume_level.setdefault(guild_id, default_volume)
        return music_queue[guild_id], repeat_count[guild_id], current_url[guild_id], is_repeating_forever[guild_id], volume_level[guild_id]

    async def play_next(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        queue, repeat, current, loop, volume = self.get_guild_data(guild_id)
        vc = interaction.guild.voice_client
        if not vc:
            return

        if (repeat > 0 or loop) and current:
            url = current
            if repeat > 0:
                repeat_count[guild_id] -= 1
        elif queue:
            url = queue.pop(0)
            current_url[guild_id] = url
            repeat_count[guild_id] = 0
            is_repeating_forever[guild_id] = False
        else:
            current_url[guild_id] = None
            is_repeating_forever[guild_id] = False
            return

        try:
            ydl_opts = {'format': 'bestaudio', 'noplaylist': True, 'quiet': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info['url']

            source = discord.FFmpegPCMAudio(audio_url)
            vc.play(discord.PCMVolumeTransformer(source, volume=volume), after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_next(interaction), self.bot.loop))

            # AI DJ voice
            await interaction.channel.send(f"🎙️ Now playing: {url}", tts=True)

        except Exception as e:
            await interaction.channel.send(f"❌ Error playing: {e}")
            await self.play_next(interaction)

    @app_commands.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction):
        if interaction.user.voice:
            channel = interaction.user.voice.channel
            await channel.connect()
            await interaction.response.send_message(f"✅ Joined {channel.name}")
        else:
            await interaction.response.send_message("❌ You're not in a voice channel.", ephemeral=True)

    @app_commands.command(name="leave", description="Leave VC and clear queue")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
        music_queue[interaction.guild.id] = []
        repeat_count[interaction.guild.id] = 0
        current_url[interaction.guild.id] = None
        is_repeating_forever[interaction.guild.id] = False
        await interaction.response.send_message("👋 Left voice and cleared queue.")

    @app_commands.command(name="play", description="Play a YouTube URL")
    @app_commands.describe(url="YouTube video URL")
    async def play(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        guild_id = interaction.guild.id

        if not interaction.user.voice:
            await interaction.followup.send("❌ Join a VC first.")
            return

        vc = interaction.guild.voice_client
        if not vc:
            channel = interaction.user.voice.channel
            vc = await channel.connect()

        queue, _, _, _, _ = self.get_guild_data(guild_id)
        queue.append(url)

        if not vc.is_playing():
            await self.play_next(interaction)
        else:
            await interaction.followup.send(f"🎵 Added to queue: {url}")

    @app_commands.command(name="queue", description="Show music queue")
    async def queue_cmd(self, interaction: discord.Interaction):
        queue, repeat, current, loop, _ = self.get_guild_data(interaction.guild.id)
        if not queue and not current:
            await interaction.response.send_message("📭 Queue is empty.")
            return

        text = ""
        if current:
            repeat_status = f"(∞ loop)" if loop else (f"(x{repeat})" if repeat > 0 else "")
            text += f"🎶 Now Playing: {current} {repeat_status}\n"
        if queue:
            text += "\n".join([f"{i+1}. {song}" for i, song in enumerate(queue)])
        await interaction.response.send_message(text)

    @app_commands.command(name="repeat", description="Repeat song N times or ∞")
    @app_commands.describe(times="Repeat times ('inf' = infinite)")
    async def repeat(self, interaction: discord.Interaction, times: str):
        guild_id = interaction.guild.id
        current = current_url.get(guild_id)

        if not current:
            await interaction.response.send_message("❌ No song playing.")
            return

        if times.lower() == "inf":
            is_repeating_forever[guild_id] = True
            repeat_count[guild_id] = 0
            await interaction.response.send_message("🔁 Now repeating infinitely.")
        else:
            try:
                count = int(times)
                if count < 0:
                    raise ValueError
                repeat_count[guild_id] = count
                is_repeating_forever[guild_id] = False
                await interaction.response.send_message(f"🔁 Will repeat {count} more time(s).")
            except ValueError:
                await interaction.response.send_message("❌ Invalid number or use 'inf'.")

    @app_commands.command(name="skip", description="Skip current song")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped.")
        else:
            await interaction.response.send_message("❌ No song playing.")

    @app_commands.command(name="pause", description="Pause song")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused.")
        else:
            await interaction.response.send_message("❌ Nothing to pause.")

    @app_commands.command(name="resume", description="Resume paused song")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed.")
        else:
            await interaction.response.send_message("❌ Nothing is paused.")

    @app_commands.command(name="volume", description="Set playback volume (0.0 to 2.0)")
    async def volume(self, interaction: discord.Interaction, level: float):
        if level < 0.0 or level > 2.0:
            await interaction.response.send_message("❌ Volume must be 0.0 to 2.0")
            return
        volume_level[interaction.guild.id] = level
        await interaction.response.send_message(f"🔊 Volume set to {level*100:.0f}%")

async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
