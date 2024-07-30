from django.db import models
from ..users.models import User
from core.utils import eastern_time


class Namespace(models.Model):
    id = models.AutoField(primary_key=True)
    nsid = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=64)
    default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_limit(self):
        return self.limit.first()

    def info(self):
        return {
            'nsid': self.nsid,
            'name': self.name,
            'immutable': self.default,
            'created_at': eastern_time(self.created_at),
            'updated_at': eastern_time(self.updated_at),
        }


NS_ROLES = (
    ('owner', 'Owner: Full control'),
    ('manager', 'Manager: Read/Write'),
    ('viewer', 'Guest: Read only'),
)


class Namespaces(models.Model):
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='users')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='namespaces')
    role = models.CharField(max_length=20, choices=NS_ROLES, default='guest')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_limit(self):
        return self.namespace.limit.first()

    def info(self):
        return {
            'nsid': self.namespace.nsid,
            'name': self.namespace.name,
            'role': self.role,
            'mutable': not self.namespace.default,
            'created_at': eastern_time(self.created_at),
            'updated_at': eastern_time(self.updated_at),
            'resources': self.get_limit().info(),
        }


class Limit(models.Model):
    id = models.AutoField(primary_key=True)
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='limit')
    cpu = models.IntegerField(default=0)
    memory = models.IntegerField(default=0)
    disk = models.IntegerField(default=0)
    public_ip = models.IntegerField(default=0)
    gpu = models.IntegerField(default=0)

    def info(self):
        return {
            'vcpu': self.cpu,
            'memory': self.memory,
            'disk': self.disk,
            'public_ip': self.public_ip,
            'gpu': self.gpu,
        }


class Secret(models.Model):
    id = models.AutoField(primary_key=True)
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='secrets')
    name = models.CharField(max_length=100)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PVC(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    size = models.IntegerField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pvcs')
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
