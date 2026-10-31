import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parent.parent


def run_import(tmp_path, code, **settings):
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1')
    # Never use real tokens, the user's database or a real network connection.
    env.update(BOT_TOKEN='123456789:' + 'a' * 35, GITHUB_TOKEN='test-token', DB_PATH=str(tmp_path / 'test.db'))
    env.update(settings)
    return subprocess.run(
        [sys.executable, '-B', '-c', code], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=10,
    )


@pytest.mark.parametrize('setting', ['', 'storage/history.db'])
def test_database_path_is_relative_to_project_not_cwd(tmp_path, setting):
    result = run_import(
        tmp_path, 'from database.connection import DB_PATH; print(DB_PATH)',
        DB_PATH=setting,
    )
    assert result.returncode == 0, result.stderr
    expected = ROOT / (setting or 'bot.db')
    assert Path(result.stdout.strip()) == expected


def test_database_path_can_use_persistent_storage(tmp_path):
    target = tmp_path / 'persistent' / 'history.db'
    result = run_import(
        tmp_path,
        'import asyncio; from database.connection import init_db; asyncio.run(init_db())',
        DB_PATH=str(target),
    )
    assert result.returncode == 0, result.stderr
    assert target.is_file()


@pytest.mark.parametrize('name', ['BOT_TOKEN', 'GITHUB_TOKEN'])
def test_empty_token_is_rejected(tmp_path, name):
    result = run_import(tmp_path, 'import main', **{name: '   '})
    assert result.returncode != 0
    assert f'{name} не найден' in result.stderr


def test_initialization_error_stops_polling(tmp_path):
    result = run_import(
        tmp_path, 'import asyncio; import main; asyncio.run(main.main())',
        DB_PATH=str(tmp_path),  # A directory is not a SQLite database.
    )
    assert result.returncode != 0
    assert 'Не удалось инициализировать SQLite' in result.stderr
