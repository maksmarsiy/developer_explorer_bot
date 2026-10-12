from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from keyboards.menus import main_keyboard


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        'Привет!',
        reply_markup=main_keyboard,
    )