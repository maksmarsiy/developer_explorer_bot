import aiosqlite


async def save_project(
        user_id: int,
        repo_id: int,
        repo_name: str,
        repo_url: str,
) -> None:
    async with aiosqlite.connect('bot.db') as db:
        await db.execute(
            '''
            INSERT INTO history (user_id, repo_id, repo_name, repo_url)
            VALUES (?, ?, ?, ?)
            ''',
            (user_id, repo_id, repo_name, repo_url)
        )
        await db.commit()


async def get_history(user_id):
    async with aiosqlite.connect('bot.db') as db:
        async with db.execute(
            '''
            SELECT repo_name, repo_url, shown_at
            FROM history
            WHERE user_id = ?
            ORDER BY shown_at DESC, id DESC
            LIMIT 10
            ''',
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()

    return rows