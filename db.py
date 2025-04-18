import aiosqlite
import os
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DATABASE = os.getenv("DATABASE_URL", "bot_data.db")

class DatabaseManager:
    def __init__(self):
        self.db = None

    async def connect(self):
        try:
            self.db = await aiosqlite.connect(DATABASE)
            await self.db.execute('''CREATE TABLE IF NOT EXISTS guild_data (
                                    guild_id INTEGER PRIMARY KEY,
                                    repeat_mode TEXT,
                                    queue TEXT)''')
            await self.db.commit()
        except Exception as e:
            print(f"Error connecting to the database: {e}")

    async def close(self):
        if self.db:
            try:
                await self.db.close()
            except Exception as e:
                print(f"Error closing the database: {e}")

    async def get_repeat_mode(self, guild_id):
        try:
            async with self.db.execute('SELECT repeat_mode FROM guild_data WHERE guild_id = ?', (guild_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return result[0]
                return 'none'
        except Exception as e:
            print(f"Error fetching repeat mode: {e}")
            return 'none'

    async def set_repeat_mode(self, guild_id, mode):
        try:
            await self.db.execute('REPLACE INTO guild_data (guild_id, repeat_mode) VALUES (?, ?)', (guild_id, mode))
            await self.db.commit()
        except Exception as e:
            print(f"Error setting repeat mode: {e}")

    async def get_queue(self, guild_id):
        try:
            async with self.db.execute('SELECT queue FROM guild_data WHERE guild_id = ?', (guild_id,)) as cursor:
                result = await cursor.fetchone()
                if result:
                    return result[0].split(",")
                return []
        except Exception as e:
            print(f"Error fetching queue: {e}")
            return []

    async def set_queue(self, guild_id, queue):
        try:
            queue_str = ",".join(queue)
            await self.db.execute('REPLACE INTO guild_data (guild_id, queue) VALUES (?, ?)', (guild_id, queue_str))
            await self.db.commit()
        except Exception as e:
            print(f"Error setting queue: {e}")

# Instantiate DatabaseManager
db_manager = DatabaseManager()

async def setup(bot):
    await db_manager.connect()
    bot.add_cog(DatabaseManager())
