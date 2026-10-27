import aiosqlite


async def init_db() -> None:
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                repo_name TEXT NOT NULL,
                repo_url TEXT NOT NULL,
                shown_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await db.commit()