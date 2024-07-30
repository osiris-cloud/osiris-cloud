import uuid
from django.db import models

from ..users.models import User
from ..k8s.models import Namespace, PVC


class VM(models.Model):
    id = models.AutoField(primary_key=True)
    vmid = models.UUIDField(auto_created=True, default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=100)
    k8s_name = models.CharField(max_length=100)
    cpu = models.IntegerField()
    memory = models.IntegerField()
    disk = models.ForeignKey(PVC, on_delete=models.CASCADE, related_name='vms')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vms')
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=30, default='Pending')
