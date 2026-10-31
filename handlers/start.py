from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.projects import next_search_version
from keyboards.menus import main_keyboard


router = Router()


@router.message(CommandStart())
async def start_handler(
        message: Message,
        state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    next_search_version(message.from_user.id)
    await state.clear()

    await message.answer(
        '🏠 Главное меню',
        reply_markup=main_keyboard,
    )
