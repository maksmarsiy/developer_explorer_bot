import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from data.dictionaries import DIRECTIONS, LANGUAGES, LANGUAGES_BY_DIRECTION
from keyboards.menus import directions_keyboard, get_languages_keyboard
from services.github import get_projects

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

    if not isinstance(callback.message, Message):
        await callback.answer('Сообщение недоступно. Откройте меню заново.')
        return

    direction_name = DIRECTIONS[callback.data]
    languages = LANGUAGES_BY_DIRECTION[callback.data]

    languages_keyboard = get_languages_keyboard(
        direction=callback.data,
        languages=languages,
    )

    await callback.answer()

    await callback.message.edit_text(
        f'Направление: {direction_name}\n'
        'Выберите язык:',
        reply_markup=languages_keyboard,
    )


@router.callback_query(F.data.startswith('language:'))
async def language_handler(
        callback: CallbackQuery,
        github_client: httpx.AsyncClient
) -> None:
    if callback.data is None:
        return

    if not isinstance(callback.message, Message):
        await callback.answer('Сообщение недоступно. Откройте меню заново.')
        return

    parts = callback.data.split(':')

    if len(parts) != 3:
        await callback.answer('Некорректные данные. Откройте меню заново.')
        return

    _, direction, language = parts

    if (
            direction not in DIRECTIONS
            or language not in LANGUAGES
            or language not in LANGUAGES_BY_DIRECTION[direction]
    ):
        await callback.answer('Некорректный выбор. Откройте меню заново.')
        return

    await callback.answer()

    try:
        projects = await get_projects(direction, language, github_client)

    except httpx.TimeoutException:
        await callback.message.edit_text(
            '⏳ GitHub слишком долго отвечает. Попробуйте позже.'
        )
        return

    except httpx.HTTPStatusError as error:
        await callback.message.edit_text(
            f'⚠️ GitHub API вернул ошибку: {error.response.status_code}'
        )
        return

    except httpx.RequestError:
        await callback.message.edit_text(
            '🌐 Не удалось подключиться к GitHub. Попробуйте позже.'
        )
        return

    if not projects:
        await callback.message.edit_text(
            '🔎 По выбранному направлению и языку проекты не найдены.'
        )
        return

    direction_name = DIRECTIONS[direction]
    language_name = LANGUAGES[language]

    text = (
        f'🚀 Найденные проекты:\n'
        f'Направление: {direction_name}\n'
        f'Язык: {language_name}\n\n'
    )

    for project in projects:
        text += (
            f"📦 {project['name']}\n"
            f"📝 {project['description']}\n"
            f"⭐ {project['stars']}\n"
            f"🔗 {project['url']}\n\n"
        )

    await callback.message.edit_text(text)
