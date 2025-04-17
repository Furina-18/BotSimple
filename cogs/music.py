import discord
from discord.ext import commands
from discord import app_commands
import wavelink
from collections import deque

TOKEN = 'YOUR_BOT_TOKEN'

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

class MusicPlayer(wavelink.Player):
    def __init__(self):
        super().__init__()
        self.queue = deque()
        self.loop = False

    async def next_track(self):
        if self.loop and self.current:
            await self.play(self.current)
        elif self.queue:
            track = self.queue.popleft()
            await self.play(track)
        else:
            await self.disconnect()

    async def add_to_queue(self, track):
        self.queue.append(track)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await wavelink.NodePool.create_node(
            bot=self.bot,
            host='127.0.0.1',
            port=2333,
            password='youshallnotpass',
            region='us_central'
        )
        print(f'Bot ready as {self.bot.user}')

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player: MusicPlayer, track, reason):
        await player.next_track()

    @app_commands.command(name="join", description="Make the bot join your voice channel")
    async def join(self, interaction: discord.Interaction):
        vc = interaction.user.voice
        if not vc or not vc.channel:
            return await interaction.response.send_message("Join a voice channel first.")
        if interaction.guild.voice_client:
            return await interaction.response.send_message("I'm already connected.")
        node = wavelink.NodePool.get_node()
        await vc.channel.connect(cls=MusicPlayer)
        await interaction.response.send_message(f"Joined {vc.channel.name}")

    @app_commands.command(name="play", description="Play a YouTube song or add it to the queue")
    @app_commands.describe(url="YouTube URL or search query")
    async def play(self, interaction: discord.Interaction, url: str):
        vc = interaction.user.voice
        if not vc or not vc.channel:
            return await interaction.response.send_message("Join a voice channel first.", ephemeral=True)

        if not interaction.guild.voice_client:
            node = wavelink.NodePool.get_node()
            player: MusicPlayer = await vc.channel.connect(cls=MusicPlayer)
        else:
            player: MusicPlayer = interaction.guild.voice_client

        track = await wavelink.YouTubeTrack.search(query=url, return_first=True)
        if player.is_playing():
            await player.add_to_queue(track)
            return await interaction.response.send_message(f"Added to queue: **{track.title}**")
        else:
            await player.play(track)
            return await interaction.response.send_message(f"Now playing: **{track.title}**")

    @app_commands.command(name="queue", description="See the music queue")
    async def queue(self, interaction: discord.Interaction):
        player: MusicPlayer = interaction.guild.voice_client
        if not player or not player.queue:
            return await interaction.response.send_message("Queue is empty.")
        msg = "**🎶 Upcoming Tracks:**\n"
        for i, track in enumerate(player.queue, start=1):
            msg += f"{i}. {track.title}\n"
        await interaction.response.send_message(msg)

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        player: MusicPlayer = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("I'm not in a voice channel.")
        await interaction.response.send_message("⏭️ Skipping...")
        await player.next_track()

    @app_commands.command(name="pause", description="Pause the current song")
    async def pause(self, interaction: discord.Interaction):
        player: MusicPlayer = interaction.guild.voice_client
        if player and player.is_playing():
            await player.pause()
            await interaction.response.send_message("⏸️ Paused the music.")
        else:
            await interaction.response.send_message("Nothing is playing.")

    @app_commands.command(name="resume", description="Resume the paused song")
    async def resume(self, interaction: discord.Interaction):
        player: MusicPlayer = interaction.guild.voice_client
        if player and player.is_paused():
            await player.resume()
            await interaction.response.send_message("▶️ Resumed the music.")
        else:
            await interaction.response.send_message("Music is not paused.")

    @app_commands.command(name="stop", description="Stop music and clear queue")
    async def stop(self, interaction: discord.Interaction):
        player: MusicPlayer = interaction.guild.voice_client
        if player:
            player.queue.clear()
            player.loop = False
            await player.stop()
            await interaction.response.send_message("🛑 Stopped music and cleared the queue.")
        else:
            await interaction.response.send_message("I'm not in a voice channel.")

    @app_commands.command(name="repeat", description="Toggle repeat mode for the current song")
    async def repeat(self, interaction: discord.Interaction):
        player: MusicPlayer = interaction.guild.voice_client
        if not player or not player.is_connected():
            return await interaction.response.send_message("I'm not in a voice channel.")
        player.loop = not player.loop
        state = "enabled 🔁" if player.loop else "disabled ❌"
        await interaction.response.send_message(f"Repeat mode {state}.")

    @app_commands.command(name="leave", description="Disconnect the bot from voice")
    async def leave(self, interaction: discord.Interaction):
        player: MusicPlayer = interaction.guild.voice_client
        if not player:
            return await interaction.response.send_message("I'm not in a voice channel.")
        await player.disconnect()
        await interaction.response.send_message("👋 Disconnected from the voice channel.")

async def setup():
    await bot.add_cog(Music(bot))
    await bot.tree.sync()

bot.loop.create_task(setup())
bot.run(TOKEN)
