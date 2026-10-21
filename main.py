import asyncio
import os

import httpx
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers.projects import router as projects_router
from handlers.start import router as start_router


load_dotenv()

BOT_TOKEN: str | None = os.getenv('BOT_TOKEN')

if BOT_TOKEN is None:
    raise ValueError('BOT_TOKEN не найден в .env')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(start_router)
dp.include_router(projects_router)


async def main() -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        await dp.start_polling(bot, github_client=client)


if __name__ == '__main__':
    asyncio.run(main())