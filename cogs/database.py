import aiosqlite
from discord.ext import commands

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.connection = None

    async def cog_load(self):
        """
        This method is called when the cog is loaded.
        It initializes the database connection.
        """
        self.connection = await aiosqlite.connect("database.db")
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS warns (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                server_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self.connection.commit()

    async def cog_unload(self):
        """
        This method is called when the cog is unloaded.
        It closes the database connection.
        """
        if self.connection:
            await self.connection.close()

    async def add_warn(self, user_id: int, server_id: int, moderator_id: int, reason: str) -> int:
        rows = await self.connection.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (user_id, server_id),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result else 1
            await self.connection.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (warn_id, user_id, server_id, moderator_id, reason),
            )
            await self.connection.commit()
            return warn_id

    async def remove_warn(self, warn_id: int, user_id: int, server_id: int) -> int:
        await self.connection.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (warn_id, user_id, server_id),
        )
        await self.connection.commit()
        rows = await self.connection.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (user_id, server_id),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def get_warnings(self, user_id: int, server_id: int) -> list:
        rows = await self.connection.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (user_id, server_id),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return [row for row in result]

# Setup function to add the cog
async def setup(bot):
    await bot.add_cog(DatabaseManager(bot))
