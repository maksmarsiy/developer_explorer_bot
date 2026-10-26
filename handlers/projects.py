import httpx
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from data.callbacks import DirectionCb, LanguageCb
from data.dictionaries import DIRECTIONS, LANGUAGES, LANGUAGES_BY_DIRECTION
from keyboards.menus import get_directions_keyboard, get_languages_keyboard
from services.github import get_projects

router = Router()


async def get_callback_message(callback: CallbackQuery) -> Message | None:
    if not isinstance(callback.message, Message):
        await callback.answer('Сообщение недоступно. Откройте меню заново.')
        return None

    return callback.message


@router.message(F.text == '🚀 Найти проекты')
async def find_projects_handler(message: Message) -> None:
    await message.answer(
        'Выберите направление',
        reply_markup=get_directions_keyboard()
    )


@router.callback_query(DirectionCb.filter())
async def direction_handler(
        callback: CallbackQuery,
        callback_data: DirectionCb,
) -> None:
    message = await get_callback_message(callback)

    if message is None:
        return

    direction = callback_data.direction

    if direction not in DIRECTIONS:
        await callback.answer('Некорректное направление.', show_alert=True)
        return

    direction_name = DIRECTIONS[direction]
    languages = LANGUAGES_BY_DIRECTION[direction]

    languages_keyboard = get_languages_keyboard(
        direction=direction,
        languages=languages,
    )

    await callback.answer()

    await message.edit_text(
        f'Направление: {direction_name}\n'
        'Выберите язык:',
        reply_markup=languages_keyboard,
    )


@router.callback_query(LanguageCb.filter())
async def language_handler(
        callback: CallbackQuery,
        callback_data: LanguageCb,
        github_client: httpx.AsyncClient,
) -> None:
    message = await get_callback_message(callback)

    if message is None:
        return

    direction = callback_data.direction
    language = callback_data.language

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
        await message.edit_text(
            '⏳ GitHub слишком долго отвечает. Попробуйте позже.'
        )
        return

    except httpx.HTTPStatusError as error:
        if error.response.status_code in (403, 429):
            await message.edit_text(
                '⏳ GitHub временно ограничил количество запросов. '
                'Попробуйте немного позже.'
            )
        else:
            await message.edit_text(
                '⚠️ Ошибка GitHub API. Попробуйте позже.'
            )
        return

    except httpx.RequestError:
        await message.edit_text(
            '🌐 Не удалось подключиться к GitHub. Попробуйте позже.'
        )
        return

    if not projects:
        await message.edit_text(
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

    await message.edit_text(text)
