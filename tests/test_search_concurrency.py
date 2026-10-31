import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import aiosqlite
import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Chat, Message, User

from data.callbacks import DirectionCb, LanguageCb, RetrySearchCb
from data.states import SearchStates
from handlers import projects
from handlers.start import start_handler


PROJECT = {
    'id': 2,
    'name': 'example',
    'full_name': 'test/example',
    'description': 'Test project',
    'url': 'https://github.com/test/example',
    'stars': 20,
    'forks': 1,
    'language': 'Python',
    'updated_at': '2026-10-30T00:00:00Z',
}


@pytest.fixture
def context(monkeypatch):
    for name in ('search_locks', 'search_versions', 'message_locks'):
        monkeypatch.setattr(projects, name, {})

    message = Message(
        message_id=10, date=0, chat=Chat(id=1, type='private'),
        from_user=User(id=1, is_bot=False, first_name='User'),
        text='old query',
    )
    callback = CallbackQuery(
        id='callback', from_user=message.from_user,
        chat_instance='chat', message=message,
    )
    ctx = SimpleNamespace(
        message=message,
        callback=callback,
        state=FSMContext(
            MemoryStorage(), StorageKey(bot_id=1, chat_id=1, user_id=1),
        ),
        search=AsyncMock(return_value=[PROJECT]),
        answer=AsyncMock(), edit=AsyncMock(), ack=AsyncMock(), save=AsyncMock(),
    )
    monkeypatch.setattr(projects, 'search_projects', ctx.search)
    monkeypatch.setattr(projects, 'get_projects', ctx.search)
    monkeypatch.setattr(projects, 'save_project', ctx.save)
    monkeypatch.setattr(projects, 'get_history', AsyncMock(return_value=[]))
    monkeypatch.setattr(Message, 'answer', ctx.answer)
    monkeypatch.setattr(Message, 'edit_text', ctx.edit)
    monkeypatch.setattr(CallbackQuery, 'answer', ctx.ack)
    return ctx


async def seed_search(ctx):
    ctx.version = projects.next_search_version(1)
    ctx.retry = RetrySearchCb(search_type='text', version=ctx.version)
    await ctx.state.set_state(SearchStates.waiting_for_query)
    await ctx.state.update_data(
        search_type='text', query_text='old query', shown_repo_ids=[1],
    )


async def run_search(ctx, kind):
    if kind == 'text':
        await projects.process_search_query(ctx.message, ctx.state, None)
    elif kind == 'language':
        await projects.language_handler(
            ctx.callback, LanguageCb(direction='backend', language='python'),
            None, ctx.state,
        )
    else:
        await projects.retry_search_handler(
            ctx.callback, ctx.retry, ctx.state, None,
        )


async def navigate(ctx, section):
    if section == 'start':
        await start_handler(ctx.message, ctx.state)
    elif section == 'main':
        await projects.back_to_main_handler(ctx.callback, ctx.state)
    elif section == 'directions':
        await projects.direction_handler(
            ctx.callback, DirectionCb(direction='backend'), ctx.state,
        )
    elif section == 'back':
        await projects.back_to_directions_handler(ctx.callback, ctx.state)
    else:
        handler = {
            'search': projects.search_handler,
            'find': projects.find_projects_handler,
            'help': projects.help_handler,
            'history': projects.history_handler,
        }[section]
        await handler(ctx.message, ctx.state)


@pytest.mark.parametrize('kind', ['text', 'language', 'retry'])
@pytest.mark.parametrize('stage', ['github', 'message', 'sqlite'])
@pytest.mark.parametrize('section', ['start', 'search', 'main'])
def test_navigation_cancels_pending_search(context, kind, stage, section):
    async def run():
        ctx = context
        await seed_search(ctx)
        entered, release = asyncio.Event(), asyncio.Event()

        async def pause(*args, **kwargs):
            if asyncio.current_task() is search_task:
                entered.set()
                await release.wait()
            if stage == 'github':
                return [PROJECT]

        pending = {
            'github': ctx.search,
            'message': ctx.answer if kind == 'text' else ctx.edit,
            'sqlite': ctx.save,
        }[stage]
        pending.side_effect = pause
        search_task = asyncio.create_task(run_search(ctx, kind))
        await asyncio.wait_for(entered.wait(), 2)
        active_version = projects.search_versions[1]

        navigation = asyncio.create_task(navigate(ctx, section))
        try:
            # Let navigation invalidate the search, including while an edit runs.
            await asyncio.sleep(0)
            assert not projects.is_search_current(1, active_version)
            if stage != 'message' or kind == 'text' or section != 'main':
                # Navigation must not wait for GitHub or SQLite.
                await asyncio.wait_for(asyncio.shield(navigation), 2)
        finally:
            release.set()
        await asyncio.wait_for(asyncio.gather(search_task, navigation), 2)

        assert await ctx.state.get_data() == {}
        expected = SearchStates.waiting_for_query.state if section == 'search' else None
        assert await ctx.state.get_state() == expected
        if stage == 'github':
            ctx.save.assert_not_awaited()

    asyncio.run(run())


@pytest.mark.parametrize(
    'section', ['start', 'search', 'main', 'directions', 'back', 'find', 'help', 'history'],
)
def test_navigation_rejects_old_retry(context, section):
    async def run():
        ctx = context
        await seed_search(ctx)
        await navigate(ctx, section)
        assert await ctx.state.get_data() == {}
        await run_search(ctx, 'retry')
        ctx.search.assert_not_awaited()

        # Even a completed new search must not make the old button valid again.
        await run_search(ctx, 'text')
        current_data = await ctx.state.get_data()
        current_version = projects.search_versions[1]
        ctx.search.reset_mock()
        await run_search(ctx, 'retry')

        ctx.search.assert_not_awaited()
        assert await ctx.state.get_data() == current_data
        assert projects.search_versions[1] == current_version
        assert ctx.ack.await_args.args[0] == 'Данные поиска устарели. Начните новый поиск.'

        markup = ctx.answer.await_args.kwargs['reply_markup']
        retry = RetrySearchCb.unpack(markup.inline_keyboard[0][0].callback_data)
        assert retry.version == current_version

    asyncio.run(run())


def test_repeated_retry_uses_latest_ids(context):
    async def run():
        ctx = context
        await seed_search(ctx)
        entered, release = asyncio.Event(), asyncio.Event()
        exclusions = []

        async def search(*args, **kwargs):
            exclusions.append(set(kwargs['exclude_ids']))
            return [dict(PROJECT, id=len(exclusions) + 1)]

        ctx.search.side_effect = search

        async def pause_first_ack(*args, **kwargs):
            if not entered.is_set():
                entered.set()
                await release.wait()

        ctx.ack.side_effect = pause_first_ack
        first = asyncio.create_task(run_search(ctx, 'retry'))
        await asyncio.wait_for(entered.wait(), 2)
        try:
            await run_search(ctx, 'retry')
            ctx.search.assert_not_awaited()
        finally:
            release.set()
        await asyncio.wait_for(first, 2)
        await run_search(ctx, 'retry')

        assert exclusions == [{1}, {1, 2}]
        assert set((await ctx.state.get_data())['shown_repo_ids']) == {1, 2, 3}

    asyncio.run(run())


@pytest.mark.parametrize('kind,result', [
    ('language', 'projects'), ('language', 'empty'),
    ('language', 'error'), ('retry', 'projects'),
])
def test_delayed_edit_cannot_overwrite_main_menu(context, kind, result):
    async def run():
        ctx = context
        await seed_search(ctx)
        if result == 'empty':
            ctx.search.return_value = []
        elif result == 'error':
            ctx.search.side_effect = httpx.ReadTimeout('Test timeout')
        entered, release = asyncio.Event(), asyncio.Event()
        edits = []

        async def edit(text, **kwargs):
            if not entered.is_set():
                entered.set()
                await release.wait()
            edits.append(text)

        ctx.edit.side_effect = edit
        task = asyncio.create_task(run_search(ctx, kind))
        await asyncio.wait_for(entered.wait(), 2)
        navigation = asyncio.create_task(navigate(ctx, 'main'))
        try:
            await asyncio.sleep(0)
            assert not navigation.done()
        finally:
            release.set()
        await asyncio.wait_for(asyncio.gather(task, navigation), 2)

        assert len(edits) == 2
        assert edits[-1] == '🏠 Главное меню'
        assert await ctx.state.get_data() == {}
        ctx.save.assert_not_awaited()

    asyncio.run(run())


def test_direction_retry_keeps_search_version(context):
    async def run():
        ctx = context
        await seed_search(ctx)
        await run_search(ctx, 'language')
        markup = ctx.edit.await_args.kwargs['reply_markup']
        packed = markup.inline_keyboard[0][0].callback_data
        assert len(packed.encode()) <= 64
        retry = RetrySearchCb.unpack(packed)
        version = projects.search_versions[1]
        assert retry.version == version

        ctx.search.reset_mock()
        ctx.search.return_value = [dict(PROJECT, id=3)]
        await projects.retry_search_handler(ctx.callback, retry, ctx.state, None)
        assert ctx.search.await_args.args[:2] == ('backend', 'python')
        assert projects.search_versions[1] == version
        assert set((await ctx.state.get_data())['shown_repo_ids']) == {2, 3}

    asyncio.run(run())


def test_retry_still_works_after_http_error(context):
    async def run():
        ctx = context
        await seed_search(ctx)
        ctx.search.side_effect = [httpx.ReadTimeout('Test timeout'), [PROJECT]]
        await run_search(ctx, 'retry')
        assert not projects.search_locks[1].locked()
        await run_search(ctx, 'retry')
        assert ctx.search.await_count == 2
        assert set((await ctx.state.get_data())['shown_repo_ids']) == {1, 2}

    asyncio.run(run())


@pytest.mark.parametrize('kind', ['text', 'language', 'retry'])
def test_sqlite_write_failure_does_not_break_results(context, kind, caplog):
    async def run():
        ctx = context
        await seed_search(ctx)
        ctx.save.side_effect = aiosqlite.OperationalError('disk is full')
        await run_search(ctx, kind)
        data = await ctx.state.get_data()
        expected = {1, 2} if kind == 'retry' else {2}
        assert set(data['shown_repo_ids']) == expected
        if kind != 'retry':
            assert await ctx.state.get_state() is None
        assert not projects.search_locks[1].locked()
        assert 'Не удалось сохранить проект' in caplog.text

    asyncio.run(run())


def test_history_read_failure_returns_message(context, monkeypatch, caplog):
    monkeypatch.setattr(
        projects, 'get_history',
        AsyncMock(side_effect=aiosqlite.OperationalError('database is locked')),
    )

    async def run():
        await projects.history_handler(context.message, context.state)
        assert 'Не удалось загрузить историю' in context.answer.await_args.args[0]
        assert 'Не удалось прочитать историю' in caplog.text

    asyncio.run(run())


def test_long_history_is_split_without_losing_text(context, monkeypatch):
    # Also exercise a single oversized line and non-BMP Unicode characters.
    query = '😀' * 5000
    rows = [
        (f'test/repo{i}', f'https://github.com/test/repo{i}',
         '2026-10-31', 'text', None, None, query)
        for i in range(10)
    ]
    monkeypatch.setattr(projects, 'get_history', AsyncMock(return_value=rows))

    async def run():
        await projects.history_handler(context.message, context.state)
        texts = [call.args[0] for call in context.answer.await_args_list]
        assert len(texts) > 1
        assert all(0 < len(text.encode('utf-16-le')) // 2 <= 4096 for text in texts)
        combined = ''.join(texts)
        assert combined.startswith('🕘 Последние просмотренные проекты:\n\n')
        assert combined.count(query) == 10
        for i in range(10):
            assert combined.count(f'https://github.com/test/repo{i}\n') == 1

    asyncio.run(run())
