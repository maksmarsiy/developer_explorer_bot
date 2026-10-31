import aiosqlite

from database.connection import DB_PATH


async def save_project(
        user_id: int,
        repo_id: int,
        repo_name: str,
        repo_url: str,
        query_type: str,
        direction: str | None = None,
        language: str | None = None,
        query_text: str | None = None,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO history (
                user_id,
                repo_id,
                repo_name,
                repo_url,
                query_type,
                direction,
                language,
                query_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                repo_id,
                repo_name,
                repo_url,
                query_type,
                direction,
                language,
                query_text,
            ),
        )
        await db.commit()


async def get_history(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            '''
            SELECT
                repo_name,
                repo_url,
                shown_at,
                query_type,
                direction,
                language,
                query_text
            FROM history
            WHERE user_id = ?
            ORDER BY shown_at DESC, id DESC
            LIMIT 10
            ''',
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()

    return rows