from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib import admin
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from django.db.models import Q, Case, When, Value, BooleanField, Sum

ROLES = (
    ('super_admin', 'Level 0: Admin'),
    ('admin', 'Level 1: Admin'),
    ('user', 'Level 3: User'),
    ('guest', 'Level 4: Guest'),
    ('blocked', 'Level 5: Blocked')
)


class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    role = models.CharField(max_length=20, choices=ROLES, default='user')
    last_login = models.DateTimeField(null=True, blank=True)
    avatar = models.URLField(null=True, blank=True)

    def not_manager(self):
        return self.username != 'manager'

    def get_limit(self):
        return self.limit.first()

    def info(self):
        return {
            'username': self.username,
            'name': f'{self.first_name} {self.last_name}',
            'email': self.email,
            'avatar': self.avatar or 'https://blob.osiriscloud.io/profile.webp',
        }

    def detailed_info(self):
        from ..k8s.models import Namespace, PVC  # Avoid circular import
        from ..vm.models import VM

        # Retrieve all namespaces the user is associated with
        namespaces = Namespace.objects.filter(
            namespaceroles__user=self
        ).annotate(
            is_default_owner=Case(
                When(Q(namespaceroles__role='owner') & Q(default=True), then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            ),
            is_owner=Case(
                When(namespaceroles__role='owner', then=Value(True)),
                default=Value(False),
                output_field=BooleanField()
            )
        )

        # Extract the default namespace ID and collect namespace IDs
        default_nsid = None
        namespace_ids = []
        owner_namespace_ids = []
        for ns in namespaces:
            namespace_ids.append(ns.id)
            if ns.is_default_owner:
                default_nsid = ns.nsid
            if ns.is_owner:
                owner_namespace_ids.append(ns.id)

        # Query the VM table to get total resources used in owner namespaces
        total_resources = VM.objects.filter(namespace_id__in=owner_namespace_ids).aggregate(
            cpu=Sum('cpu'),
            ram=Sum('memory')
        )

        disk_ids = VM.objects.filter(namespace_id__in=owner_namespace_ids).values_list('disk_id', flat=True)

        # Query the PVC table to get total disk usage
        total_disk_usage = PVC.objects.filter(id__in=disk_ids).aggregate(
            total_disk=Sum('size')
        )

        return {
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'avatar': self.avatar or 'https://blob.osiriscloud.io/profile.webp',
            'date_joined': self.date_joined,
            'last_login': self.last_login,
            'default_nsid': default_nsid,
            'cluster_role': self.role,
            'github': None,  # for now
            'namespaces': [ns.nsid for ns in namespaces],
            'resource_used': {
                'cpu': total_resources['cpu'] or 0,
                'ram': total_resources['ram'] or 0,
                'disk': total_disk_usage['total_disk'] or 0,
                'public_ip': 0,  # for now
                'gpu': 0  # for now
            },
            'resource_limit': self.get_limit().info()
        }


    class Meta:
        db_table = 'users'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'last_login')
    search_fields = ('username', 'first_name', 'last_name')
    list_filter = ('role', 'last_login')


class Event(models.Model):
    namespace = models.ForeignKey('k8s.Namespace', on_delete=models.CASCADE, related_name='events')
    message = models.TextField()
    related_link = models.CharField(max_length=256, blank=True, null=True)
    time = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def info(self):
        return {
            'message': self.message,
            'related_link': self.related_link,
            'time': self.time,
            'read': self.read,
        }

    class Meta:
        db_table = 'ns_events'


class Group(models.Model):
    gid = models.CharField(max_length=64, unique=True, primary_key=True)
    name = models.CharField(max_length=128)
    owners = models.ManyToManyField(User, related_name='groups_owned')
    members = models.ManyToManyField(User, related_name='groups_partof')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'groups'

class Limit(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='limit')
    cpu = models.IntegerField(default=0)
    memory = models.IntegerField(default=0)
    disk = models.IntegerField(default=0)
    public_ip = models.IntegerField(default=0)
    gpu = models.IntegerField(default=0)

    def info(self):
        return {
            'cpu': self.cpu,
            'ram': self.memory,
            'disk': self.disk,
            'public_ip': self.public_ip,
            'gpu': self.gpu,
        }

    class Meta:
        db_table = 'user_limits'

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
