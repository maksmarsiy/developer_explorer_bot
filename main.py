import asyncio
import logging
import os
from pathlib import Path

import aiosqlite
import httpx
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from database.connection import init_db
from handlers.projects import router as projects_router
from handlers.start import router as start_router


load_dotenv(Path(__file__).resolve().parent / '.env')

BOT_TOKEN = (os.getenv('BOT_TOKEN') or '').strip()

if not BOT_TOKEN:
    raise ValueError('BOT_TOKEN не найден в .env')

GITHUB_TOKEN = (os.getenv('GITHUB_TOKEN') or '').strip()

if not GITHUB_TOKEN:
    raise ValueError('GITHUB_TOKEN не найден в .env')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start_router)
dp.include_router(projects_router)


async def main() -> None:
    try:
        await init_db()
    except (aiosqlite.Error, OSError) as error:
        raise RuntimeError('Не удалось инициализировать SQLite. Проверьте DB_PATH и права записи.') from error
    async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                'Authorization': f'Bearer {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github+json',
            },
    ) as client:
        await dp.start_polling(bot, github_client=client)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
