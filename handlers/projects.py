from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from data.dictionaries import DIRECTIONS, LANGUAGES, LANGUAGES_BY_DIRECTION
from keyboards.menus import directions_keyboard, get_languages_keyboard


router = Router()


@router.message(F.text == '🚀 Найти проекты')
async def find_projects_handler(message: Message) -> None:
    await message.answer(
        'Выберите направление',
        reply_markup=directions_keyboard
    )


@router.callback_query(F.data.in_(DIRECTIONS))
async def direction_handler(callback: CallbackQuery) -> None:
    if callback.data is None:
        return

    direction_name = DIRECTIONS[callback.data]
    languages = LANGUAGES_BY_DIRECTION[callback.data]

    languages_keyboard = get_languages_keyboard(
        direction=callback.data,
        languages=languages,
    )

    await callback.message.edit_text(
        f'Направление: {direction_name}\n'
        'Выберите язык:',
        reply_markup=languages_keyboard,
    )

    await callback.answer()


@router.callback_query(F.data.startswith('language:'))
async def language_handler(callback: CallbackQuery) -> None:
    if callback.data is None:
        return

    _, direction, language = callback.data.split(':')

    direction_name = DIRECTIONS[direction]
    language_name = LANGUAGES[language]

    await callback.message.edit_text(
        f'Направление: {direction_name}\n'
        f'Язык: {language_name}'
    )

    await callback.answer()