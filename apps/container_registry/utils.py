import logging

from regex import match
from httpx import AsyncClient
from datetime import datetime, timedelta, timezone
from os import urandom
from jwt import encode

from core.settings import env
from ..k8s.constants import DOCKER_HEADERS

CATALOG_TOKEN = None


def validate_registry_spec(spec: dict) -> tuple[bool, str | None]:
    """
    Validate registry spec
    """
    if not spec:
        return False, 'Empty request'

    if len(name := spec.get('name', '')) < 1 or len(name) > 64:
        return False, 'Name should be between 1 and 64 characters'

    repo_name = spec.get('repo_name', '').strip()
    if not repo_name:
        return False, 'Repo is required'

    if not match(r'^[a-z0-9]+(-[a-z0-9]+)*$', repo_name):
        return False, 'Invalid repo name'

    if spec.get('public', False) not in (True, False):
        return False, 'Public should be a boolean'

    return True, None


def validate_registry_update_spec(spec: dict) -> tuple[bool, str | None]:
    """
    Validate registry update spec
    """
    if not spec:
        return False, 'Empty request'

    if name := spec.get('name', ''):
        if len(name) < 1 or len(name) > 64:
            return False, 'Name should be between 1 and 64 characters'

    if spec.get('public', False) not in (True, False):
        return False, 'Public should be a boolean'

    return True, None


def generate_auth_token(r_type: str | None = None, r_name: None | str = None, actions: list | None = None,
                        **kwargs) -> str:
    """
    Generate registry authentication token
    """
    if len(kwargs) == 0:
        kwargs = {'hours': 1}

    now = datetime.now(timezone.utc)
    header = {
        'typ': 'JWT',
        'alg': 'RS256',
        'kid': env.registry_kid
    }
    claim = {
        'iss': 'OCR',
        'sub': '',
        'aud': 'OCR',
        'exp': int((now + timedelta(**kwargs)).timestamp()),
        'nbf': int((now - timedelta(seconds=30)).timestamp()),
        'iat': int(now.timestamp()),
        'jti': urandom(32).hex(),
        'access': []
    }

    if r_type and r_name and actions:
        claim['access'] = [
            {
                "type": r_type,
                "name": r_name,
                "actions": actions
            }
        ]

    token = encode(
        headers=header,
        payload=claim,
        algorithm='RS256',
        key=env.registry_signing_key
    )

    return token


def get_registry_permissions(ns_role) -> list:
    """
    Get permissions for container registry based on namespace role
    """
    if ns_role == 'owner' or ns_role == 'manager':
        return ['pull', 'push', '*']
    elif ns_role == 'viewer':
        return ['pull']
    else:
        return []


async def get_all_repositories() -> tuple[str]:
    """
    Get all repositories from the container registry
    """
    global CATALOG_TOKEN
    if not CATALOG_TOKEN:
        CATALOG_TOKEN = generate_auth_token('registry', 'catalog', ['*'], days=360)
    headers = {**DOCKER_HEADERS, 'Authorization': f"Bearer {CATALOG_TOKEN}"}
    url = f"https://{env.registry_domain}/v2/_catalog"

    async with AsyncClient(headers=headers, verify=False) as client:
        try:
            resp = await client.get(url)
            data = resp.json()
            repos = tuple(data.get("repositories", []))
            return repos
        except Exception as e:
            logging.error(e)
            return tuple()


async def get_sub_repositories(repo_name) -> list[str]:
    all_repos = await get_all_repositories()
    prefix = f"{repo_name}/"
    prefix_len = len(prefix)
    return [repo[prefix_len:] for repo in all_repos if repo.startswith(prefix)]


async def get_tags(client: AsyncClient, repo_path: str) -> list[str]:
    url = f"https://{env.registry_domain}/v2/{repo_path}/tags/list"
    try:
        response = await client.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("tags", [])
        elif response.status_code == 404:  # Repository exists but has no tags
            return []
    except Exception as e:
        logging.error(e)
        return []


async def get_manifest(client: AsyncClient, repo_path: str, tag: str) -> dict:
    url = f"https://{env.registry_domain}/v2/{repo_path}/manifests/{tag}"
    try:
        resp = await client.get(url)
        manifest = resp.json()
        manifest['reference'] = resp.headers.get('Docker-Content-Digest', '')
        return manifest
    except Exception as e:
        logging.error(e)
        return {}


def get_blob_digests(manifest: dict) -> list[str]:
    layers = manifest.get('layers', [])
    return [layer.get('digest', '') for layer in layers] + [manifest.get('config', {}).get('digest', '')]


async def delete_blob(client: AsyncClient, repo_path: str, digest: str) -> bool:
    try:
        resp = await client.delete(f"https://{env.registry_domain}/v2/{repo_path}/blobs/{digest}")
        return resp.status_code == 202
    except Exception as e:
        logging.exception(e)
        return False
