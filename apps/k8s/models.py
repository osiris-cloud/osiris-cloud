from django.db import models
from django.db.models import Q
from encrypted_model_fields.fields import EncryptedTextField
from json import loads as json_loads
import uuid

from ..users.models import User


class Namespace(models.Model):
    nsid = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    default = models.BooleanField(default=False)
    users = models.ManyToManyField(User, through='NamespaceRoles', related_name='namespaces')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
            return self.namespaceroles_set.filter(user=user).first().role
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
        }

    class Meta:
        db_table = 'namespaces'
        ordering = ['-created_at']


NS_ROLES = (
    ('owner', 'Owner: Full control'),
    ('manager', 'Manager: Read/Write'),
    ('viewer', 'Guest: Read only'),
)


class NamespaceRoles(models.Model):
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=NS_ROLES, default='viewer')

    class Meta:
        db_table = 'namespace_roles'


class Secret(models.Model):
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='secrets')
    name = models.CharField(max_length=100)
    data = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def info(self):
        return {
            'name': self.name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'values': json_loads(self.data) if isinstance(self.data, str) else self.data
        }
    
    class Meta:
        db_table = 'ns_secrets'


class PVC(models.Model):
    name = models.CharField(max_length=100)
    size = models.IntegerField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pvcs')
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'pvcs'
        ordering = ['-created_at']


class Event(models.Model):
    event_id = models.UUIDField(auto_created=True, default=uuid.uuid4, unique=True)
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='events')
    message = models.TextField()
    related_link = models.CharField(max_length=256, blank=True, null=True)
    time = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)

    def info(self):
        return {
            'event_id': self.event_id,
            'message': self.message,
            'related_link': self.related_link,
            'time': self.time,
            'read': self.read,
        }

    class Meta:
        db_table = 'ns_events'