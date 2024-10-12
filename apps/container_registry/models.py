import httpx

from asgiref.sync import async_to_sync
from django.db import models
from uuid import UUID
from encrypted_model_fields.fields import EncryptedTextField

from ..k8s.models import Namespace
from core.settings import env

from .utils import get_repositories, get_tags, get_size

DOCKER_HEADERS = {
    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
}


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

    @property
    def url(self):
        return self.slug + '.' + env.registry_domain

    def info(self):
        return {
            'crid': self.crid,
            'name': self.name,
            'url': self.url,
            'public': self.public,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    def get_login(self):
        return {
            'username': self.username,
            'password': self.password,
        }

    def stat(self) -> list[dict]:
        url = self.url
        result = []

        async def stat_async() -> list[dict]:
            async with httpx.AsyncClient(auth=(self.username, self.password), headers=DOCKER_HEADERS) as client:
                try:
                    repositories = await get_repositories(client, url)
                    for repo in repositories:
                        item = {
                            'repo': repo,
                            'tags': [],
                            'size': 0
                        }
                        tags = await get_tags(client, url, repo)
                        if tags:
                            for tag in tags:
                                size = await get_size(client, url, repo, tag)
                                item['tags'].append({
                                    'name': tag,
                                    'size': size,
                                })
                                item['size'] += size
                        result.append(item)
                    return result

                except Exception:
                    return [{}]

        async_to_sync(stat_async)()
        return result

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'container_registry'
        ordering = ['-created_at']
