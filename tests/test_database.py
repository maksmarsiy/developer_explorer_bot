import asyncio

import aiosqlite

from database import connection, history


def test_save_and_get_history(tmp_path, monkeypatch):
    test_db = tmp_path / 'test_bot.db'

    monkeypatch.setattr(history, 'DB_PATH', str(test_db))
    monkeypatch.setattr(connection, 'DB_PATH', str(test_db))

    async def run_test():
        await connection.init_db()
        await connection.init_db()

        await history.save_project(
            user_id=123,
            repo_id=456,
            repo_name='test/example',
            repo_url='https://github.com/test/example',
            query_type='direction',
            direction='backend',
            language='python',
        )

        return await history.get_history(123)

    rows = asyncio.run(run_test())

    assert len(rows) == 1
    assert rows[0][0] == 'test/example'
    assert rows[0][1] == 'https://github.com/test/example'
    assert rows[0][3] == 'direction'
    assert rows[0][4] == 'backend'
    assert rows[0][5] == 'python'


def test_history_limit_order_and_user_isolation(tmp_path, monkeypatch):
    path = tmp_path / 'nested' / 'history.db'
    monkeypatch.setattr(connection, 'DB_PATH', path)
    monkeypatch.setattr(history, 'DB_PATH', path)

    async def run():
        await connection.init_db()
        for user_id in (1, 2):
            for index in range(12):
                await history.save_project(
                    user_id, index, f'{user_id}/repo{index}',
                    f'https://github.com/{user_id}/repo{index}',
                    'text', query_text="python ' sqlite",
                )
        # Force timestamp ties so the id DESC tie breaker is exercised.
        async with aiosqlite.connect(path) as db:
            await db.execute("UPDATE history SET shown_at = '2026-10-31 12:00:00'")
            await db.commit()
        for user_id in (1, 2):
            rows = await history.get_history(user_id)
            assert [r[0] for r in rows] == [f'{user_id}/repo{i}' for i in range(11, 1, -1)]
            assert all(r[6] == "python ' sqlite" for r in rows)
        assert await history.get_history(3) == []

    asyncio.run(run())


def test_init_db_migrates_existing_history(tmp_path, monkeypatch):
    path = tmp_path / 'legacy.db'
    monkeypatch.setattr(connection, 'DB_PATH', path)
    monkeypatch.setattr(history, 'DB_PATH', path)

    async def run():
        async with aiosqlite.connect(path) as db:
            await db.execute('''CREATE TABLE history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, repo_id INTEGER NOT NULL,
                repo_name TEXT NOT NULL, repo_url TEXT NOT NULL,
                shown_at TEXT DEFAULT CURRENT_TIMESTAMP
            )''')
            await db.execute("INSERT INTO history(user_id, repo_id, repo_name, repo_url) VALUES (1, 1, 'old/repo', 'https://github.com/old/repo')")
            await db.commit()
        await connection.init_db()
        await connection.init_db()
        rows = await history.get_history(1)
        assert rows[0][0] == 'old/repo'
        assert rows[0][3:] == (None, None, None, None)
        await history.save_project(1, 2, 'new/repo', 'https://github.com/new/repo', 'text', query_text='python')
        rows = await history.get_history(1)
        assert len(rows) == 2
        assert rows[0][6] == 'python'

    asyncio.run(run())
