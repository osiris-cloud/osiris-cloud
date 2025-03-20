from django.db import models
from django.db.models import Q

from core.model_fields import UUID7StringField
from django.contrib import admin

from ..users.models import User
from .constants import VOLUME_TYPES
from .constants import NS_ROLES, R_STATES


class Namespace(models.Model):
    nsid = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    default = models.BooleanField(default=False)
    users = models.ManyToManyField(User, through='NamespaceRoles', related_name='namespaces')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    locked = models.BooleanField(default=False)
    state = models.CharField(max_length=16, choices=R_STATES, default='creating')

    @property
    def owner(self):
        return self.users.filter(namespaceroles__role='owner').first()

    def get_users(self):
        return self.users.all()

    def get_role(self, user) -> str | None:
        """
        Returns -> 'owner', 'manager', 'viewer' or None
        """
        try:
            return self.namespaceroles_set.get(user=user).role
        except:
            return None

    def get_users_info(self):
        u_info = lambda u: {
            **u.info(),
            'role': self.get_role(u),
        }
        return [u_info(u) for u in self.users.filter(~Q(namespaceroles__role='owner'))]

    def info(self):
        return {
            'nsid': self.nsid,
            'name': self.name,
            'default': self.default,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'owner': self.owner.info(),
            'users': self.get_users_info(),
        }

    def brief(self):
        return {
            'nsid': self.nsid,
            'name': self.name,
            'default': self.default,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'owner': self.owner.info(),
        }

    class Meta:
        db_table = 'namespaces'
        ordering = ['-created_at']


@admin.register(Namespace)
class NSAdmin(admin.ModelAdmin):
    list_display = ('nsid', 'name', 'default', 'locked')
    search_fields = ('nsid',)
    list_filter = ('default',)


class NamespaceRoles(models.Model):
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=NS_ROLES, default='viewer')

    class Meta:
        db_table = 'namespace_roles'


class Volume(models.Model):
    volid = UUID7StringField(auto_created=True)
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=16, choices=VOLUME_TYPES)
    size = models.FloatField()
    mount_path = models.TextField()
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict)

    def info(self):
        return {
            'volid': self.volid,
            'type': self.type,
            'name': self.name,
            'size': self.size,
            'mount_path': self.mount_path,
        }

    def mode_info(self):
        return self.metadata.get('ca_mode', {})

    @property
    def mounted_to(self):
        modes = self.mode_info()
        modes = {
            'main': modes['main'],
            'sidecar': modes['sidecar'],
            'init': modes['init'],
        }

        if not modes:
            return 'None'

        return ', '.join([f'{k.capitalize()} -> {v.upper() if v else 'NA'}' for k, v in modes.items()])

    class Meta:
        db_table = 'volumes'
        ordering = ['-created_at']


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'size', 'namespace', 'volid')
    search_fields = ('namespace',)


class Event(models.Model):
    eventid = UUID7StringField(auto_created=True)
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='events')
    message = models.TextField()
    related_link = models.CharField(max_length=256, blank=True, null=True)
    time = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def info(self):
        return {
            'eventid': self.eventid,
            'message': self.message,
            'related_link': self.related_link,
            'time': self.time,
            'read': self.read,
        }

    class Meta:
        db_table = 'ns_events'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('namespace', 'time', 'message', 'eventid')
    search_fields = ('namespace',)

# class LBEndpoint(models.Model):
#     name = models.CharField(max_length=64)
#     description = models.CharField(max_length=256, blank=True, null=True)
#     ip = models.GenericIPAddressField()
#     port = models.IntegerField()
#     protocol = models.CharField(max_length=4, choices=LB_PROTOCOLS, default='tcp')
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     state = models.CharField(max_length=16, choices=R_STATES, default='creating')
#
#     class Meta:
#         db_table = 'lb_endpoints'
#         ordering = ['-created_at']
#
#
# @admin.register(LBEndpoint)
# class LBAdmin(admin.ModelAdmin):
#     list_display = ('name', 'ip', 'port', 'protocol', 'state')
#     search_fields = ('ip', 'port')
