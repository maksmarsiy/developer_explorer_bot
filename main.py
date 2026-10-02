import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)
from dotenv import load_dotenv


load_dotenv()

BOT_TOKEN: str | None = os.getenv('BOT_TOKEN')

if BOT_TOKEN is None:
    raise ValueError('BOT_TOKEN не найден в .env')

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

find_projects_button = KeyboardButton(text='🚀 Найти проекты')
search_button = KeyboardButton(text='🔎 Поиск')
history_button = KeyboardButton(text='🕘 История')
help_button = KeyboardButton(text='❓ Помощь')

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [find_projects_button, search_button],
        [history_button, help_button]
    ]
)

backend_button = InlineKeyboardButton(
    text='⚙️ Backend',
    callback_data='backend'
)
frontend_button = InlineKeyboardButton(
    text='🎨 Frontend',
    callback_data='frontend'
)
ai_ml_button = InlineKeyboardButton(
    text='🤖 AI / ML',
    callback_data='ai_ml'
)
data_button = InlineKeyboardButton(
    text='📊 Data',
    callback_data='data'
)
dev_ops_button = InlineKeyboardButton(
    text='☁️ DevOps',
    callback_data='dev_ops'
)
mobile_button = InlineKeyboardButton(
    text='📱 Mobile',
    callback_data='mobile'
)
game_dev_button = InlineKeyboardButton(
    text='🎮 Game Development',
    callback_data='game_dev'
)

directions_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [backend_button, frontend_button],
        [ai_ml_button, data_button],
        [dev_ops_button, mobile_button],
        [game_dev_button]
    ]
)

DIRECTIONS = {
    'backend': 'Backend',
    'frontend': 'Frontend',
    'ai_ml': 'AI / ML',
    'data': 'Data',
    'dev_ops': 'DevOps',
    'mobile': 'Mobile',
    'game_dev': 'Game Development',
}


@dp.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        'Привет!',
        reply_markup=main_keyboard
)


@dp.message(F.text == '🚀 Найти проекты')
async def find_projects_handler(message: Message) -> None:
    await message.answer(
        'Выберите направление',
        reply_markup=directions_keyboard
)


@dp.callback_query(F.data.in_(DIRECTIONS))
async def direction_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    if callback.data is None:
        return

    direction_name = DIRECTIONS[callback.data]

    await callback.message.answer(
        f'Вы выбрали {direction_name}'
    )


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())