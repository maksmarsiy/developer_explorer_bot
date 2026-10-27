import asyncio
import os

import httpx
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from database.connection import init_db
from handlers.projects import router as projects_router
from handlers.start import router as start_router


load_dotenv()

BOT_TOKEN: str | None = os.getenv('BOT_TOKEN')

if BOT_TOKEN is None:
    raise ValueError('BOT_TOKEN не найден в .env')

GITHUB_TOKEN: str | None = os.getenv('GITHUB_TOKEN')

if GITHUB_TOKEN is None:
    raise ValueError('GITHUB_TOKEN не найден в .env')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start_router)
dp.include_router(projects_router)


async def main() -> None:
    await init_db()
    async with httpx.AsyncClient(
            timeout=10.0,
            headers={
                'Authorization': f'Bearer {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github+json',
            },
    ) as client:
        await dp.start_polling(bot, github_client=client)


if __name__ == '__main__':
    asyncio.run(main())