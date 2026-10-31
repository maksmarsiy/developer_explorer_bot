
import asyncio
import logging

import aiosqlite
import httpx
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from data.callbacks import DirectionCb, LanguageCb, RetrySearchCb
from data.dictionaries import DIRECTIONS, LANGUAGES, LANGUAGES_BY_DIRECTION
from data.states import SearchStates
from database.history import get_history, save_project
from keyboards.menus import (
    get_directions_keyboard,
    get_languages_keyboard,
    get_results_keyboard,
    get_search_keyboard,
    main_keyboard,
)
from services.github import GitHubProject, get_projects, search_projects


router = Router()
logger = logging.getLogger(__name__)

search_locks: dict[int, asyncio.Lock] = {}
search_versions: dict[int, int] = {}
message_locks: dict[tuple[int, int], asyncio.Lock] = {}


def next_search_version(user_id: int) -> int:
    version = search_versions.get(user_id, 0) + 1
    search_versions[user_id] = version
    return version


def is_search_current(user_id: int, version: int) -> bool:
    return search_versions.get(user_id) == version


async def save_project_safely(**kwargs) -> None:
    try:
        await save_project(**kwargs)
    except aiosqlite.Error:
        logger.exception('Не удалось сохранить проект в историю')


async def edit_current_message(
        message: Message,
        user_id: int,
        version: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    # Navigation waits only for an edit of this message, never for GitHub/SQLite.
    key = (message.chat.id, message.message_id)
    lock = message_locks.setdefault(key, asyncio.Lock())
    async with lock:
        if not is_search_current(user_id, version):
            return False
        await message.edit_text(text, reply_markup=reply_markup)
        return is_search_current(user_id, version)


def get_github_error_message(error: httpx.HTTPError) -> str:
    if isinstance(error, httpx.TimeoutException):
        return '⏳ GitHub слишком долго отвечает. Попробуйте позже.'

    if isinstance(error, httpx.HTTPStatusError):
        if error.response.status_code in (403, 429):
            return (
                '⏳ GitHub временно ограничил количество запросов. '
                'Попробуйте немного позже.'
            )

        return '⚠️ Ошибка GitHub API. Попробуйте позже.'

    if isinstance(error, httpx.RequestError):
        return '🌐 Не удалось подключиться к GitHub. Попробуйте позже.'

    return '⚠️ Неизвестная ошибка GitHub API.'


def format_project(project: GitHubProject) -> str:
    project_language = project['language'] or 'Не указан'
    updated_at = project['updated_at'][:10]

    return (
        f"📦 {project['name']}\n"
        f"📝 {project['description']}\n"
        f"💻 Язык: {project_language}\n"
        f"⭐ Звёзды: {project['stars']}\n"
        f"🍴 Форки: {project['forks']}\n"
        f"📅 Обновлён: {updated_at}\n"
        f"🔗 {project['url']}\n\n"
    )


async def get_callback_message(callback: CallbackQuery) -> Message | None:
    if not isinstance(callback.message, Message):
        await callback.answer('Сообщение недоступно. Откройте меню заново.')
        return None

    return callback.message


@router.message(F.text == '🚀 Найти проекты')
async def find_projects_handler(
        message: Message,
        state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    next_search_version(message.from_user.id)
    await state.clear()

    await message.answer(
        'Выберите направление',
        reply_markup=get_directions_keyboard(),
    )


@router.message(F.text == '🔎 Поиск')
async def search_handler(
        message: Message,
        state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    next_search_version(message.from_user.id)
    await state.clear()
    await state.set_state(SearchStates.waiting_for_query)

    await message.answer(
        '🔎 Введите название проекта или ключевые слова для поиска на GitHub.',
        reply_markup=get_search_keyboard(),
    )


@router.message(F.text == '🕘 История')
async def history_handler(
        message: Message,
        state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    user_id = message.from_user.id
    version = next_search_version(user_id)
    await state.clear()

    try:
        history = await get_history(user_id)
    except aiosqlite.Error:
        logger.exception('Не удалось прочитать историю')
        if is_search_current(user_id, version):
            await message.answer('⚠️ Не удалось загрузить историю. Попробуйте позже.')
        return

    if not is_search_current(user_id, version):
        return

    if not history:
        await message.answer('История просмотров пока пуста.')
        return

    text = '🕘 Последние просмотренные проекты:\n\n'

    for (
            repo_name,
            repo_url,
            shown_at,
            query_type,
            direction,
            language,
            query_text,
    ) in history:
        if query_type == 'direction':
            search_info = (
                f'Направление: {DIRECTIONS.get(direction, direction)}\n'
                f'Язык: {LANGUAGES.get(language, language)}\n'
            )
        elif query_type == 'text':
            search_info = f'Запрос: {query_text}\n'
        else:
            search_info = 'Способ поиска: не указан\n'

        text += (
            f'📦 {repo_name}\n'
            f'{search_info}'
            f'🔗 {repo_url}\n'
            f'📅 {shown_at} UTC\n\n'
        )

    # 2000 Unicode characters fit even when every character uses two UTF-16 units.
    while text:
        if not is_search_current(user_id, version):
            return
        end = min(2000, len(text))
        if end < len(text):
            newline = text.rfind('\n', 0, end)
            if newline >= 0:
                end = newline + 1
        await message.answer(text[:end])
        text = text[end:]


@router.message(F.text == '❓ Помощь')
async def help_handler(
        message: Message,
        state: FSMContext,
) -> None:
    if message.from_user is None:
        return

    next_search_version(message.from_user.id)
    await state.clear()

    await message.answer(
        '❓ Как пользоваться ботом:\n\n'
        '🚀 Найти проекты — поиск по направлению и языку.\n'
        '🔎 Поиск — поиск по ключевым словам.\n'
        '🕘 История — последние 10 просмотренных проектов.\n'
        '🔄 Искать ещё — получить следующие 3 проекта.\n'
        '🏠 Главное меню — вернуться к основным разделам.'
    )


@router.message(SearchStates.waiting_for_query)
async def process_search_query(
        message: Message,
        state: FSMContext,
        github_client: httpx.AsyncClient,
) -> None:
    if message.text is None:
        await message.answer('Пожалуйста, введите текстовый запрос.')
        return

    query = message.text.strip()

    if not query:
        await message.answer('Поисковый запрос не может быть пустым.')
        return

    if message.from_user is None:
        return

    user_id = message.from_user.id
    lock = search_locks.setdefault(user_id, asyncio.Lock())

    if lock.locked():
        await message.answer('⏳ Поиск уже выполняется.')
        return

    async with lock:
        version = next_search_version(user_id)

        try:
            projects = await search_projects(query, github_client)

        except httpx.HTTPError as error:
            if is_search_current(user_id, version):
                await message.answer(get_github_error_message(error))
            return

        if not is_search_current(user_id, version):
            return

        if not projects:
            await message.answer(
                '🔎 По вашему запросу репозитории не найдены.'
            )

            if is_search_current(user_id, version):
                await state.clear()
            return

        text = f'🔎 Результаты поиска по запросу: {query}\n\n'

        for project in projects:
            text += format_project(project)

        if not is_search_current(user_id, version):
            return

        await message.answer(
            text,
            reply_markup=get_results_keyboard('text', version=version),
        )

        if not is_search_current(user_id, version):
            return

        for project in projects:
            await save_project_safely(
                user_id=user_id,
                repo_id=project['id'],
                repo_name=project['full_name'],
                repo_url=project['url'],
                query_type='text',
                query_text=query,
            )

        if not is_search_current(user_id, version):
            return

        await state.update_data(
            search_type='text',
            query_text=query,
            shown_repo_ids=[project['id'] for project in projects],
        )

        if is_search_current(user_id, version):
            await state.set_state(None)


@router.callback_query(DirectionCb.filter())
async def direction_handler(
        callback: CallbackQuery,
        callback_data: DirectionCb,
        state: FSMContext,
) -> None:
    message = await get_callback_message(callback)

    if message is None:
        return

    direction = callback_data.direction

    if direction not in DIRECTIONS:
        await callback.answer('Некорректное направление.', show_alert=True)
        return

    version = next_search_version(callback.from_user.id)
    await state.clear()

    direction_name = DIRECTIONS[direction]
    languages = LANGUAGES_BY_DIRECTION[direction]

    languages_keyboard = get_languages_keyboard(
        direction=direction,
        languages=languages,
    )

    await callback.answer()

    await edit_current_message(
        message, callback.from_user.id, version,
        f'Направление: {direction_name}\n'
        'Выберите язык:',
        reply_markup=languages_keyboard,
    )


@router.callback_query(F.data == 'back_to_directions')
async def back_to_directions_handler(
        callback: CallbackQuery,
        state: FSMContext,
) -> None:
    message = await get_callback_message(callback)

    if message is None:
        return

    version = next_search_version(callback.from_user.id)
    await state.clear()

    await callback.answer()

    await edit_current_message(
        message, callback.from_user.id, version,
        'Выберите направление:',
        reply_markup=get_directions_keyboard(),
    )


@router.callback_query(F.data == 'back_to_main')
async def back_to_main_handler(
        callback: CallbackQuery,
        state: FSMContext,
) -> None:
    message = await get_callback_message(callback)

    if message is None:
        return

    version = next_search_version(callback.from_user.id)

    await state.clear()
    await callback.answer()

    if not await edit_current_message(
        message, callback.from_user.id, version, '🏠 Главное меню',
    ):
        return

    await message.answer(
        'Выберите действие:',
        reply_markup=main_keyboard,
    )


@router.callback_query(RetrySearchCb.filter())
async def retry_search_handler(
        callback: CallbackQuery,
        callback_data: RetrySearchCb,
        state: FSMContext,
        github_client: httpx.AsyncClient,
) -> None:
    message = await get_callback_message(callback)

    if message is None:
        return

    search_type = callback_data.search_type

    if search_type not in ('direction', 'text'):
        await callback.answer('Неизвестный тип поиска.', show_alert=True)
        return

    user_id = callback.from_user.id
    lock = search_locks.setdefault(user_id, asyncio.Lock())

    if lock.locked():
        await callback.answer(
            '⏳ Поиск уже выполняется.',
            show_alert=True,
        )
        return

    async with lock:
        data = await state.get_data()
        version = callback_data.version

        if not is_search_current(user_id, version):
            await callback.answer(
                'Данные поиска устарели. Начните новый поиск.',
                show_alert=True,
            )
            return

        if search_type == 'direction':
            direction = callback_data.direction
            language = callback_data.language

            if (
                direction not in DIRECTIONS
                or language not in LANGUAGES
                or language not in LANGUAGES_BY_DIRECTION[direction]
            ):
                await callback.answer(
                    'Некорректный выбор.',
                    show_alert=True,
                )
                return

            same_search = (
                data.get('search_type') == 'direction'
                and data.get('direction') == direction
                and data.get('language') == language
            )

            query = None

        else:
            direction = None
            language = None
            query = data.get('query_text')

            same_search = (
                isinstance(query, str)
                and bool(query)
                and data.get('search_type') == 'text'
            )

        if not same_search:
            await callback.answer(
                'Данные поиска устарели. Начните новый поиск.',
                show_alert=True,
            )
            return

        await callback.answer()

        if not is_search_current(user_id, version):
            return

        exclude_ids = set(data.get('shown_repo_ids', []))

        try:
            if search_type == 'direction':
                assert isinstance(direction, str)
                assert isinstance(language, str)

                projects = await get_projects(
                    direction,
                    language,
                    github_client,
                    exclude_ids=exclude_ids,
                )
            else:
                assert isinstance(query, str)

                projects = await search_projects(
                    query,
                    github_client,
                    exclude_ids=exclude_ids,
                )

        except httpx.HTTPError as error:
            if is_search_current(user_id, version):
                await message.answer(get_github_error_message(error))
            return

        if not is_search_current(user_id, version):
            return

        if not projects:
            await message.answer('Новых проектов пока не найдено.')
            return

        text = '🔄 Новые проекты:\n\n'

        for project in projects:
            text += format_project(project)

        if not await edit_current_message(
            message, user_id, version,
            text,
            reply_markup=get_results_keyboard(
                search_type=search_type,
                direction=direction or '',
                language=language or '',
                version=version,
            ),
        ):
            return

        if not is_search_current(user_id, version):
            return

        for project in projects:
            await save_project_safely(
                user_id=user_id,
                repo_id=project['id'],
                repo_name=project['full_name'],
                repo_url=project['url'],
                query_type=search_type,
                direction=direction,
                language=language,
                query_text=query,
            )

        if not is_search_current(user_id, version):
            return

        exclude_ids.update(project['id'] for project in projects)

        await state.update_data(
            shown_repo_ids=list(exclude_ids),
        )


@router.callback_query(LanguageCb.filter())
async def language_handler(
        callback: CallbackQuery,
        callback_data: LanguageCb,
        github_client: httpx.AsyncClient,
        state: FSMContext,
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

    user_id = callback.from_user.id
    lock = search_locks.setdefault(user_id, asyncio.Lock())

    if lock.locked():
        await callback.answer(
            '⏳ Поиск уже выполняется. Подождите.',
            show_alert=True,
        )
        return

    async with lock:
        version = next_search_version(user_id)

        await callback.answer()

        if not is_search_current(user_id, version):
            return

        try:
            projects = await get_projects(
                direction,
                language,
                github_client,
            )

        except httpx.HTTPError as error:
            if is_search_current(user_id, version):
                await edit_current_message(
                    message, user_id, version,
                    get_github_error_message(error)
                )
            return

        if not is_search_current(user_id, version):
            return

        if not projects:
            await edit_current_message(
                message, user_id, version,
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
            text += format_project(project)

        if not await edit_current_message(
            message, user_id, version,
            text,
            reply_markup=get_results_keyboard(
                search_type='direction',
                direction=direction,
                language=language,
                version=version,
            ),
        ):
            return

        if not is_search_current(user_id, version):
            return

        for project in projects:
            await save_project_safely(
                user_id=user_id,
                repo_id=project['id'],
                repo_name=project['full_name'],
                repo_url=project['url'],
                query_type='direction',
                direction=direction,
                language=language,
            )

        if not is_search_current(user_id, version):
            return

        await state.update_data(
            search_type='direction',
            direction=direction,
            language=language,
            shown_repo_ids=[project['id'] for project in projects],
        )

        if is_search_current(user_id, version):
            await state.set_state(None)
