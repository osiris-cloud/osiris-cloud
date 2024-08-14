from django.db import models
from django.db.models import Q
from encrypted_model_fields.fields import EncryptedTextField
from ..users.models import User
from core.utils import eastern_time


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

    def get_limit(self):
        return self.limit.first()

    def get_users(self):
        return self.users.all()

    def get_role(self, user):
        return self.namespaceroles_set.filter(user=user).first().role

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
            'created_at': eastern_time(self.created_at),
            'updated_at': eastern_time(self.updated_at),
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


class Limit(models.Model):
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

    class Meta:
        db_table = 'ns_limits'


class Secret(models.Model):
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='secrets')
    name = models.CharField(max_length=100)
    data = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
