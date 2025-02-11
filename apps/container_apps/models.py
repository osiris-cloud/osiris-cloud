from django.db import models
from django.contrib import admin
from core.model_fields import UUID7StringField
from base64 import b64encode

from ..infra.models import Namespace, Volume
from ..infra.constants import R_STATES
from ..secret_store.models import Secret
from ..container_registry.models import ContainerRegistry

from ..container_registry.utils import generate_auth_token

from core.settings import env


class Container(models.Model):
    containerid = UUID7StringField(auto_created=True)
    type = models.CharField(max_length=16,
                            choices=(('init', 'Init Container'),
                                     ('main', 'Main Container'),
                                     ('sidecar', 'Sidecar Container')))
    image = models.TextField()
    pull_secret = models.ForeignKey(Secret, on_delete=models.SET_NULL, null=True, default=None,
                                    related_name='container_pull_secrets')
    env_secret = models.ForeignKey(Secret, on_delete=models.SET_NULL, null=True, default=None,
                                   related_name='container_env_secrets')
    port = models.IntegerField(null=True, default=None)
    port_protocol = models.CharField(max_length=16, choices=(('tcp', 'TCP'), ('udp', 'UDP')), null=True, default=None)
    command = models.JSONField(null=True, default=list)
    args = models.JSONField(null=True, default=list)
    cpu = models.FloatField()
    memory = models.IntegerField()
    metadata = models.JSONField(default=dict)

    def info(self):
        return {
            'containerid': self.containerid,
            'image': self.image,
            'pull_secret': self.pull_secret.secretid if self.pull_secret else None,
            'env_secret': self.env_secret.secretid if self.env_secret else None,
            'port': self.port,
            'port_protocol': self.port_protocol,
            'command': self.command,
            'args': self.args,
            'cpu': self.cpu,
            'memory': self.memory,
        }

    def gen_oc_auth_data(self) -> str | None:
        if self.pull_secret:
            return None

        auth_token = generate_auth_token(r_type='repository',
                                         r_name=f"{self.metadata['repo']}/{self.metadata['image']}",
                                         actions=['pull'],
                                         years=25)
        auth_str = b64encode(f"osiris:{auth_token}".encode()).decode()
        docker_config = {
            "auths": {
                env.registry_domain: {
                    "auth": auth_str
                }
            }
        }
        return b64encode(str(docker_config).encode()).decode()


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('image', 'cpu', 'memory',)
    search_fields = ('containerid',)
    list_filter = ('port_protocol',)


class CustomDomain(models.Model):
    name = models.CharField(max_length=253, unique=True)


@admin.register(CustomDomain)
class CustomDomainAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class Scaler(models.Model):
    min_replicas = models.IntegerField(default=1)
    max_replicas = models.IntegerField(default=1)
    scaleup_stb_window = models.IntegerField(default=0)
    scaledown_stb_window = models.IntegerField(default=150)
    scalers = models.JSONField(default=list)

    def default(self):
        self.min_replicas = 1
        self.max_replicas = 1
        self.scaleup_stb_window = 0
        self.scaledown_stb_window = 150
        self.scalers = []
        self.save()

    def info(self):
        return {
            'min_replicas': self.min_replicas,
            'max_replicas': self.max_replicas,
            'scaleup_stb_window': self.scaleup_stb_window,
            'scaledown_stb_window': self.scaledown_stb_window,
            'scalers': self.scalers,
        }


class AppFW(models.Model):
    deny = models.JSONField(default=list)
    allow = models.JSONField(default=list)
    precedence = models.CharField(max_length=16, choices=(('deny', 'Deny'), ('allow', 'Allow')))
    nyu_only = models.BooleanField(default=False)

    def info(self):
        return {
            'deny': self.deny,
            'allow': self.allow,
            'precedence': self.precedence,
            'nyu_only': self.nyu_only,
        }


class ContainerApp(models.Model):
    appid = UUID7StringField(auto_created=True)
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    slug = models.CharField(max_length=64)
    containers = models.ManyToManyField(Container, blank=True)
    custom_domains = models.ManyToManyField(CustomDomain, blank=True)
    volumes = models.ManyToManyField(Volume, blank=True)
    scaler = models.OneToOneField(Scaler, on_delete=models.CASCADE)
    connection_port = models.IntegerField()
    connection_protocol = models.CharField(max_length=16,
                                           choices=(('http', 'Web app'),
                                                    ('tcp', 'TCP on random port'),
                                                    ('udp', 'UDP on random port')))
    pass_tls = models.BooleanField(default=False)
    restart_policy = models.CharField(max_length=16, default='always', choices=(('always', 'Always'),
                                                                                ('on_failure', 'On Failure'),
                                                                                ('never', 'Never')))
    update_strategy = models.CharField(max_length=16, default='recreate', choices=(('rolling', 'Rolling'),
                                                                                   ('recreate', 'Recreate')))
    ip_rule = models.OneToOneField(AppFW, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=16, choices=R_STATES, default='creating')
    metadata = models.JSONField(default=dict)

    def volume_info(self):
        result = []
        for vol in self.volumes.all():
            result.append({
                **(vol.info()),
                'mode': vol.mode_info()
            })
        return result

    @property
    def url(self):
        if self.connection_protocol == 'http':
            return f'https://{self.slug}.{env.container_apps_domain}'
        return f'{self.slug}.{env.container_apps_domain}'

    @property
    def connect_url(self):
        return f'{self.url}:{self.connection_port}' if self.connection_protocol != 'http' else self.url

    @property
    def display_url(self):
        if self.connection_protocol == 'http':
            return f'{self.url}'
        return f'{self.connection_protocol}://{self.url}:{self.connection_port}'

    @property
    def cpu_limit(self):
        return sum([container.cpu_limit for container in self.containers.all()])

    @property
    def memory_limit(self):
        return sum([container.memory_limit for container in self.containers.all()])

    def info(self):
        container_types = {
            'main': {},
            'init': {},
            'sidecar': {},
        }
        for container in self.containers.all():
            container_types[container.type] = container.info()

        return {
            'appid': self.appid,
            'name': self.name,
            'url': self.url,
            'connection_port': 443 if self.connection_protocol == 'http' else self.connection_port,
            'connection_protocol': self.connection_protocol,
            'state': self.state,
            'restart_policy': self.restart_policy,
            'custom_domains': [custom_domain.name for custom_domain in self.custom_domains.all()],
            **container_types,
            'volumes': self.volume_info(),
            'scaling': self.scaler.info(),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }


@admin.register(ContainerApp)
class ContainerAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'connection_protocol')
    list_filter = ('connection_protocol',)
