from django.db import models
from django.contrib import admin
from core.model_fields import UUID7StringField

from ..k8s.models import Namespace, PVC
from ..k8s.constants import R_STATES, DEFAULT_HPA_SPEC
from ..secret_store.models import Secret

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
    port = models.IntegerField(null=True, default=None)
    port_protocol = models.CharField(max_length=16, choices=(('tcp', 'TCP'), ('udp', 'UDP')), null=True, default=None)
    env_secret = models.ForeignKey(Secret, on_delete=models.SET_NULL, null=True, default=None,
                                   related_name='container_env_secrets')
    command = models.JSONField(null=True, default=list)
    args = models.JSONField(null=True, default=list)
    cpu_request = models.IntegerField()
    memory_request = models.IntegerField()
    cpu_limit = models.IntegerField()
    memory_limit = models.IntegerField()

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
            'cpu_request': self.cpu_request,
            'memory_request': self.memory_request,
            'cpu_limit': self.cpu_limit,
            'memory_limit': self.memory_limit,
        }


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('image', 'cpu_request', 'memory_request', 'cpu_limit', 'memory_limit')
    search_fields = ('containerid',)
    list_filter = ('port_protocol',)


class CustomDomain(models.Model):
    name = models.CharField(max_length=253)
    gen_tls_cert = models.BooleanField()

    def info(self):
        return {
            'name': self.name,
            'gen_cert': self.gen_tls_cert,
        }


@admin.register(CustomDomain)
class CustomDomainAdmin(admin.ModelAdmin):
    list_display = ('name', 'gen_tls_cert')
    search_fields = ('name',)


class HPA(models.Model):
    enable = models.BooleanField(default=False)
    min_replicas = models.IntegerField(default=1)
    max_replicas = models.IntegerField(default=1)
    scaleup_stb_window = models.IntegerField(default=300)
    scaledown_stb_window = models.IntegerField(default=300)
    cpu_trigger = models.IntegerField(null=True, default=90)
    memory_trigger = models.IntegerField(null=True, default=90)

    def info(self):
        return {
            'enable': self.enable,
            'min_replicas': self.min_replicas,
            'max_replicas': self.max_replicas,
            'scaleup_stb_window': self.scaleup_stb_window,
            'scaledown_stb_window': self.scaledown_stb_window,
            'cpu_trigger': self.cpu_trigger,
            'memory_trigger': self.memory_trigger,
        }


@admin.register(HPA)
class HPAAdmin(admin.ModelAdmin):
    list_display = ('enable', 'min_replicas', 'max_replicas', 'cpu_trigger', 'memory_trigger')
    list_filter = ('enable',)


class ContainerApp(models.Model):
    appid = UUID7StringField(auto_created=True)
    name = models.CharField(max_length=64)
    slug = models.CharField(max_length=64)
    replicas = models.IntegerField(default=1)
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    containers = models.ManyToManyField(Container, blank=True)
    custom_domains = models.ManyToManyField(CustomDomain, blank=True)
    pvcs = models.ManyToManyField(PVC, blank=True)
    hpa = models.ForeignKey(HPA, on_delete=models.SET_NULL, null=True, default=None)
    connection_port = models.IntegerField(null=True, default=None)
    connection_protocol = models.CharField(max_length=16,
                                           choices=(('http', 'Web app'),
                                                    ('tcp', 'TCP on random port'),
                                                    ('udp', 'UDP on random port')))
    restart_policy = models.CharField(max_length=16, default='always', choices=(('always', 'Always'),
                                                                                ('on_failure', 'On Failure'),
                                                                                ('never', 'Never')))
    state = models.CharField(max_length=16, choices=R_STATES, default='creating')
    exposed_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def volume_info(self):
        result = []
        for pvc in self.pvcs.all():
            result.append({
                'volid': pvc.pvcid,
                'name': pvc.name,
                'size': pvc.size,
                'mount_path': pvc.mount_path,
                'modes': {
                    'main': pvc.container_app_mode.main,
                    'init': pvc.container_app_mode.init,
                    'sidecar': pvc.container_app_mode.sidecar,
                }
            })
        return result

    @property
    def url(self):
        return f'https://{self.slug}.{env.container_apps_domain}'

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
            'replicas': self.replicas,
            'connection_port': 443 if self.connection_protocol == 'http' else self.connection_port,
            'connection_protocol': self.connection_protocol,
            'state': self.state,
            'restart_policy': self.restart_policy,
            'custom_domains': [custom_domain.info() for custom_domain in self.custom_domains.all()],
            **container_types,
            'volumes': self.volume_info(),
            'autoscale': self.hpa.info() if self.hpa else None,
            'exposed_public': self.exposed_public,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    def save(self, *args, **kwargs):
        if not self.hpa:
            self.container_app_mode = HPA.objects.create(**DEFAULT_HPA_SPEC)
        super().save(*args, **kwargs)


@admin.register(ContainerApp)
class ContainerAppAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'connection_protocol')
    list_filter = ('connection_protocol',)
