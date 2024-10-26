import asyncio
import logging

import httpx

from asgiref.sync import async_to_sync
from django.db import models
from uuid import UUID
from encrypted_model_fields.fields import EncryptedTextField

from ..k8s.models import Namespace
from core.settings import env

from ..k8s.constants import R_STATES, DOCKER_HEADERS

from .utils import get_repositories, get_tags, get_manifest, get_blob_digests


class ContainerRegistry(models.Model):
    crid = models.UUIDField(primary_key=True, default=UUID, editable=False)
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='registries')
    name = models.CharField(max_length=64)
    slug = models.SlugField(max_length=32)
    public = models.BooleanField(default=False)
    username = models.CharField(max_length=32)
    password = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=16, choices=[(state[0], state[1]) for state in R_STATES], default='creating')

    @property
    def url(self):
        return self.slug + '.' + env.registry_domain

    @property
    def http_url(self):
        return 'https://' + self.url

    def info(self):
        return {
            'crid': self.crid,
            'name': self.name,
            'url': self.url,
            'public': self.public,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'state': self.state,
        }

    def get_login(self):
        return {
            'username': self.username,
            'password': self.password,
        }

    def stat(self) -> list[dict]:
        if not self.state == 'active':
            return []

        async def stat_async() -> list:
            result = []
            async with httpx.AsyncClient(auth=(self.username, self.password), headers=DOCKER_HEADERS) as client:
                try:
                    repositories = await get_repositories(client, self.http_url)
                    for repo in repositories:
                        item = {
                            'repo': repo,
                            'tags': [],
                            'size': 0
                        }
                        tags = await get_tags(client, self.http_url, repo)
                        if tags:
                            for tag in tags:
                                manifest = await get_manifest(client, self.http_url, repo, tag)
                                config = manifest.get('config', {})
                                layers = manifest.get('layers', [])
                                size = sum([layer.get('size', 0) for layer in layers]) + config.get('size', 0)
                                item['tags'].append({
                                    'name': tag,
                                    'size': size,
                                    'digest': config.get('digest', ''),
                                })
                                item['size'] += size
                            result.append(item)
                    return result

                except Exception as e:
                    logging.exception(e)
                    return []

        resp = async_to_sync(stat_async)()
        return resp

    def delete_image(self, repo, tag) -> bool:
        if not self.state == 'active':
            return False

        async def delete_blob(client: httpx.AsyncClient, digest) -> bool:
            resp = await client.delete(f"{self.http_url}/v2/{repo}/blobs/{digest}")
            return resp.status_code == 202

        async def delete_image_async() -> bool:
            async with httpx.AsyncClient(auth=(self.username, self.password)) as client:
                try:
                    manifest = await get_manifest(client, self.http_url, repo, tag)
                    digests = get_blob_digests(manifest)

                    blob_tasks = [delete_blob(client, digest) for digest in digests]
                    await asyncio.gather(*blob_tasks)

                    response = await client.delete(f"{self.http_url}/v2/{repo}/manifests/{manifest.get('reference')}")

                    return response.status_code == 202
                except Exception as e:
                    logging.exception(e)
                    return False

        deleted = async_to_sync(delete_image_async)()
        return deleted

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'container_registry'
        ordering = ['-created_at']
