import asyncio

import httpx

from services.github import get_projects, parse_repository


def test_parse_repository():
    repository = {
        'id': 123,
        'full_name': 'test/example',
        'name': 'example',
        'description': None,
        'html_url': 'https://github.com/test/example',
        'stargazers_count': 100,
        'language': 'Python',
        'forks_count': 10,
        'updated_at': '2026-10-30T12:00:00Z',
    }

    result = parse_repository(repository)

    assert result['id'] == 123
    assert result['full_name'] == 'test/example'
    assert result['name'] == 'example'
    assert result['description'] == 'Описание отсутствует'
    assert result['url'] == 'https://github.com/test/example'
    assert result['stars'] == 100
    assert result['language'] == 'Python'
    assert result['forks'] == 10
    assert result['updated_at'] == '2026-10-30T12:00:00Z'


def test_get_projects():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/search/repositories'

        return httpx.Response(
            status_code=200,
            json={
                'items': [
                    {
                        'id': 123,
                        'full_name': 'test/example',
                        'name': 'example',
                        'description': 'Тестовый проект',
                        'html_url': 'https://github.com/test/example',
                        'stargazers_count': 100,
                        'language': 'Python',
                        'forks_count': 10,
                        'updated_at': '2026-10-30T12:00:00Z',
                    }
                ]
            }
        )

    async def run_test():
        transport = httpx.MockTransport(mock_handler)

        async with httpx.AsyncClient(transport=transport) as client:
            return await get_projects('backend', 'python', client)

    projects = asyncio.run(run_test())

    assert len(projects) == 1
    assert projects[0]['id'] == 123
    assert projects[0]['name'] == 'example'


def test_get_projects_exclude_ids():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                'items': [
                    {
                        'id': 123,
                        'full_name': 'test/example',
                        'name': 'example',
                        'description': 'Тестовый проект',
                        'html_url': 'https://github.com/test/example',
                        'stargazers_count': 100,
                        'language': 'Python',
                        'forks_count': 10,
                        'updated_at': '2026-10-30T12:00:00Z',
                    }
                ]
            }
        )

    async def run_test():
        transport = httpx.MockTransport(mock_handler)

        async with httpx.AsyncClient(transport=transport) as client:
            return await get_projects(
                'backend',
                'python',
                client,
                exclude_ids={123},
            )

    projects = asyncio.run(run_test())

    assert projects == []
