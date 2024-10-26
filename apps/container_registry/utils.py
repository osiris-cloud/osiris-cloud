from core.utils import error_message
from regex import match
from httpx import AsyncClient


def validate_registry_spec(spec: dict) -> tuple[bool, dict | None]:
    """
    Validate registry spec
    """
    if len(name := spec.get('name', '')) < 1 or len(name) > 64:
        return False, error_message('Name should be between 1 and 64 characters')

    slug = spec.get('slug')
    if not slug:
        return False, error_message('Slug is required')

    if len(slug) < 3 or len(slug) > 32:
        return False, error_message('Slug should be between 3 and 32 characters')

    if not match(r'^[a-z0-9]+(-[a-z0-9]+)*$', slug):
        return False, error_message('Invalid slug')

    if len(spec.get('password', '')) < 8:
        return False, error_message('Password must be at least 8 characters')

    return True, None


def validate_registry_update_spec(spec: dict) -> tuple[bool, dict | None]:
    """
    Validate registry update spec
    """
    if name := spec.get('name', ''):
        if len(name) < 1 or len(name) > 64:
            return False, error_message('Name should be between 1 and 64 characters')

    if psw := spec.get('password', ''):
        if len(psw) < 8:
            return False, error_message('Password must be at least 8 characters')

    return True, None


async def get_repositories(client: AsyncClient, url: str, next_url=None, repos=None, page_size=100) -> list[str]:
    if repos is None:
        repos = []

    url = f"{url}/v2/_catalog?n={page_size}"
    if next_url:
        url = next_url

    try:
        resp = await client.get(url)
    except Exception as e:
        return repos

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


async def get_tags(client: AsyncClient, url: str, repo: str) -> list[str]:
    url = f"{url}/v2/{repo}/tags/list"
    response = await client.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("tags", [])
    elif response.status_code == 404:
        # Repository exists but has no tags
        return []


async def get_manifest(client: AsyncClient, url: str, repo: str, tag: str) -> dict:
    url = f"{url}/v2/{repo}/manifests/{tag}"
    resp = await client.get(url)
    manifest = resp.json()
    manifest['reference'] = resp.headers.get('Docker-Content-Digest', '')
    return manifest


def get_blob_digests(manifest: dict) -> list[str]:
    layers = manifest.get('layers', [])
    return [layer.get('digest', '') for layer in layers] + [manifest.get('config', {}).get('digest', '')]
