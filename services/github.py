import httpx


async def get_projects(
        language: str,
        client: httpx.AsyncClient
) -> list[dict[str, str | int | None]]:
    try:
        response = await client.get(
            'https://api.github.com/search/repositories',
            params={'q': f'language:{language}'}
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

    projects = []

    for repository in repositories[:3]:
        project = {
            'name': repository['name'],
            'description': repository['description'],
            'url': repository['html_url'],
            'stars': repository['stargazers_count']
        }
        projects.append(project)

    return projects