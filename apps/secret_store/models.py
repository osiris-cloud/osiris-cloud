from django.db import models
from encrypted_model_fields.fields import EncryptedTextField

from json import loads as json_loads
from uuid_utils import uuid7

from ..k8s.models import Namespace
from ..k8s.constants import R_STATES

SECRET_TYPES = (('opaque', 'Key value pair secret'),
                ('auth', 'Auth secret'),
                )


class Secret(models.Model):
    secretid = models.UUIDField(auto_created=True, default=uuid7, unique=True)
    name = models.CharField(max_length=64)
    type = models.CharField(max_length=16, choices=SECRET_TYPES, default='opaque')
    data = EncryptedTextField()
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='secrets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=16, choices=R_STATES, default='creating')

    def info(self):
        return {
            'secretid': self.secretid,
            'name': self.name,
            'type': self.type,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'state': self.state,
        }

    def values(self):
        return json_loads(self.data) if self.data else {}

    class Meta:
        db_table = 'secret_store'
