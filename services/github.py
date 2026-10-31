import random
from typing import TypedDict

import httpx

from data.dictionaries import GITHUB_TOPICS


class GitHubProject(TypedDict):
    id: int
    full_name: str
    name: str
    description: str
    url: str
    stars: int
    language: str | None
    forks: int
    updated_at: str


def parse_repository(repository: dict) -> GitHubProject:
    return {
        'id': repository['id'],
        'full_name': repository['full_name'],
        'name': repository['name'],
        'description': repository['description'] or 'Описание отсутствует',
        'url': repository['html_url'],
        'stars': repository['stargazers_count'],
        'language': repository['language'],
        'forks': repository['forks_count'],
        'updated_at': repository['updated_at'],
    }


async def get_projects(
        direction: str,
        language: str,
        client: httpx.AsyncClient,
        exclude_ids: set[int] | None = None,
) -> list[GitHubProject]:
    if exclude_ids is None:
        exclude_ids = set()

    topics = random.sample(
        GITHUB_TOPICS[direction],
        k=len(GITHUB_TOPICS[direction])
    )

    repositories = []

    for topic in topics:
        try:
            response = await client.get(
                'https://api.github.com/search/repositories',
                params={
                    'q': (
                        f'language:{language} '
                        f'topic:{topic} '
                        'stars:10..500 archived:false is:public'
                    ),
                    'per_page': 100,
                }
            )
            response.raise_for_status()

        except httpx.TimeoutException:
            print('Превышено время ожидания GitHub API')
            raise

        except httpx.HTTPStatusError as error:
            print(f'Ошибка GitHub API: {error.response.status_code}')
            raise

        except httpx.RequestError as error:
            print(f'Ошибка соединения с GitHub: {error}')
            raise

        data = response.json()

        repositories = [
            repository
            for repository in data['items']
            if repository['id'] not in exclude_ids
        ]

        if repositories:
            break

    projects: list[GitHubProject] = []

    for repository in random.sample(
            repositories,
            k=min(3, len(repositories)),
    ):
        projects.append(parse_repository(repository))

    return projects


async def search_projects(
        query: str,
        client: httpx.AsyncClient,
        exclude_ids: set[int] | None = None,
) -> list[GitHubProject]:
    if exclude_ids is None:
        exclude_ids = set()

    response = await client.get(
        'https://api.github.com/search/repositories',
        params={
            'q': f'{query} archived:false is:public',
            'per_page': 10,
        },
    )

    response.raise_for_status()
    data = response.json()
    repositories = data['items']

    projects: list[GitHubProject] = []

    for repository in repositories:
        if repository['id'] in exclude_ids:
            continue

        projects.append(parse_repository(repository))

        if len(projects) == 3:
            break

    return projects