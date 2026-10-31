import aiosqlite


DB_PATH = "bot.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                repo_name TEXT NOT NULL,
                repo_url TEXT NOT NULL,
                query_type TEXT,
                direction TEXT,
                language TEXT,
                query_text TEXT,
                shown_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        columns = [
            "query_type",
            "direction",
            "language",
            "query_text",
        ]

        async with db.execute("PRAGMA table_info(history)") as cursor:
            existing_columns = {
                row[1] for row in await cursor.fetchall()
            }

        for column in columns:
            if column not in existing_columns:
                await db.execute(
                    f"ALTER TABLE history ADD COLUMN {column} TEXT"
                )

        await db.commit()