from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib import admin

ROLES = (
    ('super_admin', 'Level 0: Admin'),
    ('admin', 'Level 1: Admin'),
    ('user', 'Level 3: User'),
    ('guest', 'Level 4: Guest'),
    ('blocked', 'Level 5: Blocked')
)


class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, choices=ROLES, default='guest')
    last_login = models.DateTimeField(null=True, blank=True)
    avatar = models.URLField(null=True, blank=True)

    def not_manager(self):
        return self.username != 'osirisadmin'

    def info(self):
        return {
            'username': self.username,
            'name': f'{self.first_name} {self.last_name}',
            'email': self.email,
            'avatar': self.avatar or 'https://blob.osiriscloud.io/profile.webp',
        }

    def detailed_info(self):
        from .utils import get_default_ns
        if self.username == 'osirisadmin':
            return {}

        return {
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'avatar': self.avatar or 'https://blob.osiriscloud.io/profile.webp',
            'date_joined': self.date_joined,
            'last_login': self.last_login,
            'default_nsid': get_default_ns(self).nsid,
            'cluster_role': self.role,
            'github': self.github.username if hasattr(self, 'github') else None,
            'resource_usage': self.usage.info(),
            'resource_limit': self.limit.info(),
        }

    class Meta:
        db_table = 'users'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'last_login')
    search_fields = ('username', 'first_name', 'last_name')
    list_filter = ('role', 'last_login')


class Usage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='usage')
    cpu = models.IntegerField(null=True, default=0)
    memory = models.IntegerField(null=True, default=0)
    disk = models.IntegerField(null=True, default=0)
    public_ip = models.IntegerField(null=True, default=0)
    gpu = models.IntegerField(null=True, default=0)
    registry = models.IntegerField(null=True, default=0)

    def info(self):
        return {
            'cpu': self.cpu,
            'memory': self.memory,
            'disk': self.disk,
            'public_ip': self.public_ip,
            'gpu': self.gpu,
            'registry': self.registry
        }

    class Meta:
        db_table = 'usage'


@admin.register(Usage)
class UsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpu', 'memory', 'disk', 'public_ip', 'gpu', 'registry')
    search_fields = ('user',)


class Limit(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='limit')
    cpu = models.IntegerField(null=True, default=0)
    memory = models.IntegerField(null=True, default=0)
    disk = models.IntegerField(null=True, default=0)
    public_ip = models.IntegerField(null=True, default=0)
    gpu = models.IntegerField(null=True, default=0)
    registry = models.IntegerField(null=True, default=0)

    def info(self):
        return {
            'cpu': self.cpu,
            'memory': self.memory,
            'disk': self.disk,
            'public_ip': self.public_ip,
            'gpu': self.gpu,
            'registry': self.registry
        }

    def __sub__(self, usage):
        if not isinstance(usage, Usage):
            raise ValueError("Subtraction can only be performed with a Usage instance.")

        remaining_resources = {
            'cpu': max(self.cpu - usage.cpu, 0),
            'memory': max(self.memory - usage.memory, 0),
            'disk': max(self.disk - usage.disk, 0),
            'public_ip': max(self.public_ip - usage.public_ip, 0),
            'gpu': max(self.gpu - usage.gpu, 0),
            'registry': max(self.registry - usage.registry, 0),
        }

        return remaining_resources

    def limit_reached(self, cpu=None, memory=None, disk=None, public_ip=None, gpu=None, registry=None):
        if cpu is not None and self.cpu < cpu:
            return True
        if memory is not None and self.memory < memory:
            return True
        if disk is not None and self.disk < disk:
            return True
        if public_ip is not None and self.public_ip < public_ip:
            return True
        if gpu is not None and self.gpu < gpu:
            return True
        if registry is not None and self.registry < registry:
            return True
        return False

    class Meta:
        db_table = 'limits'


@admin.register(Limit)
class LimitAdmin(admin.ModelAdmin):
    list_display = ('user', 'cpu', 'memory', 'disk', 'public_ip', 'gpu', 'registry')
    search_fields = ('user',)


class Group(models.Model):
    gid = models.CharField(max_length=64, unique=True, primary_key=True)
    name = models.CharField(max_length=64)
    description = models.TextField(null=True, blank=True)
    owners = models.ManyToManyField(User, related_name='groups_owned')
    members = models.ManyToManyField(User, related_name='groups_partof')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'groups'
