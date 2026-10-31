import asyncio

import httpx
import pytest

from services.github import MAX_SEARCH_PAGES, SEARCH_PAGE_SIZE, search_projects


def repository(repo_id):
    return {
        'id': repo_id, 'name': f'repo{repo_id}', 'full_name': f'test/repo{repo_id}',
        'description': None, 'html_url': f'https://github.com/test/repo{repo_id}',
        'stargazers_count': 20, 'language': 'Python', 'forks_count': 1,
        'updated_at': '2026-10-31T00:00:00Z',
    }


def test_search_moves_to_next_page_and_excludes_duplicates():
    pages = []
    excluded = set(range(1, 100))

    def respond(request):
        page = int(request.url.params['page'])
        assert int(request.url.params['per_page']) == SEARCH_PAGE_SIZE
        assert request.url.params['q'] == 'python archived:false is:public'
        pages.append(page)
        ids = list(range(1, 101)) if page == 1 else [100, 101, 101, 102]
        return httpx.Response(200, json={'items': [repository(i) for i in ids], 'total_count': 104})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            results = await search_projects('python', client, excluded)
        assert [p['id'] for p in results] == [100, 101, 102]
        assert excluded == set(range(1, 100))
        assert pages == [1, 2]

    asyncio.run(run())


def test_search_request_budget():
    pages = []
    excluded = set(range(1, MAX_SEARCH_PAGES * SEARCH_PAGE_SIZE + 1))

    def respond(request):
        page = int(request.url.params['page'])
        pages.append(page)
        first = (page - 1) * SEARCH_PAGE_SIZE + 1
        return httpx.Response(200, json={
            'items': [repository(i) for i in range(first, first + SEARCH_PAGE_SIZE)],
            'total_count': 1000,
        })

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            assert await search_projects('python', client, excluded) == []
        assert pages == list(range(1, MAX_SEARCH_PAGES + 1))

    asyncio.run(run())


@pytest.mark.parametrize('ids', [[], [1, 2]])
def test_search_stops_at_end(ids):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={'items': [repository(i) for i in ids]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            assert await search_projects('python', client, set(ids)) == []
        assert len(calls) == 1

    asyncio.run(run())


@pytest.mark.parametrize('status', [403, 429, 500])
def test_pagination_preserves_http_errors(status):
    def respond(request):
        if request.url.params['page'] == '1':
            return httpx.Response(200, json={'items': [repository(1)] * SEARCH_PAGE_SIZE})
        return httpx.Response(status)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            with pytest.raises(httpx.HTTPStatusError) as error:
                await search_projects('python', client, {1})
            assert error.value.response.status_code == status

    asyncio.run(run())
