import aiosqlite
import asyncio

class DatabaseManager:
    def __init__(self, db_path: str = "bot_data.db"):
        self.db_path = db_path

    async def setup(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    join_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            await db.commit()

    async def add_user(self, user_id: int, username: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?);
            """, (user_id, username))
            await db.commit()

    async def get_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,))
            return await cursor.fetchone()

    async def get_all_users(self):
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT * FROM users;")
            return await cursor.fetchall()

    async def remove_user(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM users WHERE user_id = ?;", (user_id,))
            await db.commit()
