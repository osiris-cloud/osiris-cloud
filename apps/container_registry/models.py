import asyncio
import logging

import httpx

from asgiref.sync import async_to_sync
from django.db import models
from django.utils import timezone

from core.model_fields import UUID7StringField
from ..k8s.models import Namespace

from core.settings import env
from .utils import get_sub_repositories, get_tags, get_manifest, get_blob_digests, generate_auth_token, delete_blob

from ..k8s.constants import R_STATES, DOCKER_HEADERS


class ContainerRegistry(models.Model):
    crid = UUID7StringField()
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='registries')
    name = models.CharField(max_length=64)
    repo = models.SlugField(max_length=50)
    public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=16, choices=R_STATES, default='creating')

    @property
    def url(self):
        return env.registry_domain + '/' + self.repo

    @property
    def domain(self):
        return env.registry_domain

    def get_role(self, username):
        return self.namespace.get_role(username)

    @property
    def last_pushed_at(self):
        w_hook = self.webhooks.filter(action='push')
        return w_hook.last().timestamp if w_hook.exists() else None

    def info(self):
        return {
            'crid': self.crid,
            'name': self.name,
            'url': self.url,
            'public': self.public,
            'last_pushed_at': self.last_pushed_at,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'state': self.state,
        }

    def stat(self) -> list[dict]:
        async def stat_async() -> list:
            sub_repos = await get_sub_repositories(self.repo)
            result = []

            for sub in sub_repos:
                repo_path = f'{self.repo}/{sub}'
                token, _ = RepoToken.get_or_create(path=repo_path)
                headers = {**DOCKER_HEADERS, 'Authorization': f"Bearer {token.token}"}
                try:
                    async with httpx.AsyncClient(headers=headers) as client:
                        item = {
                            'sub': sub,
                            'tags': [],
                            'size': 0
                        }
                        tags = await get_tags(client, repo_path)
                        if tags:
                            for tag in tags:
                                manifest = await get_manifest(client, repo_path, tag)
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

                except Exception as e:
                    logging.exception(e)
                    return []

            return result

        resp = async_to_sync(stat_async)()
        return resp

    def delete_image(self, sub_repo, tag) -> bool:
        if not self.state == 'active':
            return False

        async def delete_image_async() -> bool:
            repo_path = f'{self.repo}/{sub_repo}'
            token, _ = RepoToken.get_or_create(registry=self, path=repo_path)
            headers = {**DOCKER_HEADERS, 'Authorization': f"Bearer {token.token}"}
            try:
                async with httpx.AsyncClient(headers=headers) as client:
                    manifest = await get_manifest(client, sub_repo, tag)
                    digests = get_blob_digests(manifest)

                    blob_tasks = [delete_blob(client, sub_repo, digest) for digest in digests]
                    await asyncio.gather(*blob_tasks)

                    response = await client.delete(
                        f"https://{env.registry_domain}/v2/{sub_repo}/manifests/{manifest.get('reference')}")

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


class RepoToken(models.Model):
    registry = models.ForeignKey(ContainerRegistry, on_delete=models.CASCADE, related_name='tokens')
    path = models.TextField()
    token = models.TextField()
    expires_at = models.DateTimeField()

    @classmethod
    def get_or_create(cls, registry, path):
        token, created = cls.objects.get_or_create(registry=registry, path=path)
        if token.expires_at <= timezone.now():
            token.renew()
        return token, created

    def generate(self):
        self.token = generate_auth_token('repository', self.path, ['pull', 'delete'], days=30)
        self.expires_at = timezone.now() + timezone.timedelta(days=30)

    def renew(self):
        self.generate()
        self.save()

    def save(self, *args, **kwargs):
        if not self.token:
            self.generate()
        return super().save(*args, **kwargs)


class RegistryWebhook(models.Model):
    registry = models.ForeignKey(ContainerRegistry, on_delete=models.CASCADE, related_name='webhooks')
    target = models.TextField()
    action = models.CharField(max_length=16)
    timestamp = models.DateTimeField(auto_now_add=True)
    content = models.JSONField()

    def save(self, *args, **kwargs):
        repo, target = kwargs['repository'].split('/', 1)
        self.registry = ContainerRegistry.objects.get(repo=repo)
        self.target = target
        del kwargs['repository']
        return super().save(*args, **kwargs)
