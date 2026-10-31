import os
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / '.env')
DB_PATH = Path(os.getenv('DB_PATH') or PROJECT_ROOT / 'bot.db').expanduser()
if not DB_PATH.is_absolute():
    DB_PATH = PROJECT_ROOT / DB_PATH
DB_PATH = DB_PATH.resolve()


async def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
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
