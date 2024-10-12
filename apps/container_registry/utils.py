from core.utils import error_message
from regex import match


def validate_registry_spec(spec: dict) -> tuple[bool, dict | None]:
    """
    Validate registry spec
    """
    if len(name := spec.get('name', '')) < 1 or len(name) > 100:
        return False, error_message('Name should be between 1 and 64 characters')

    slug = spec.get('slug')
    if not slug:
        return False, error_message('Slug is required')

    if len(slug) < 3 or len(slug) > 32:
        return False, error_message('Slug should be between 3 and 32 characters')

    if not match(r'^[a-z0-9]+(-[a-z0-9]+)*$', slug):
        return False, error_message('Invalid slug')

    if not len(spec.get('password', '')) < 8:
        return False, error_message('Password condition not met (at least 8 characters)')

    return True, None


async def get_repositories(client, url, next_url=None, repos=None, page_size=100) -> list[str]:
    if repos is None:
        repos = []

    url = f"{url}/v2/_catalog?n={page_size}"
    if next_url:
        url = next_url

    resp = await client.get(url)
    resp.raise_for_status()

    data = resp.json()
    repos.extend(data.get("repositories", []))

    # Handle pagination if 'Link' header is present
    link = resp.headers.get("Link")
    if link and 'rel="next"' in link:
        # Extract the next URL from the Link header
        parts = link.split(";")
        if len(parts) == 2 and 'rel="next"' in parts[1]:
            next_url = parts[0].strip('<> ')
            await get_repositories(client, next_url, repos)

    return repos


async def get_tags(client, url, repos) -> list[str]:
    url = f"{url}/v2/{repos}/tags/list"
    response = await client.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("tags", [])
    elif response.status_code == 404:
        # Repository exists but has no tags
        return []
    else:
        response.raise_for_status()


async def get_size(client, url, repo, tag):
    url = f"{url}/v2/{repo}/manifests/{tag}"
    resp = await client.get(url)
    return resp.json().get('config', {}).get('size', 0)
