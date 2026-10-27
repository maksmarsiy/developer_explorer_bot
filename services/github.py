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


async def get_projects(
        direction: str,
        language: str,
        client: httpx.AsyncClient
) -> list[GitHubProject]:
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
        repositories = data['items']

        if repositories:
            break

    projects: list[GitHubProject] = []

    for repository in random.sample(repositories, k=min(3, len(repositories))):
        project: GitHubProject = {
            'id': repository['id'],
            'full_name': repository['full_name'],
            'name': repository['name'],
            'description': repository['description'] or 'Описание отсутствует',
            'url': repository['html_url'],
            'stars': repository['stargazers_count']
        }
        projects.append(project)

    return projects