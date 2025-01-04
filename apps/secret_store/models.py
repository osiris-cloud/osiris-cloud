from django.db import models
from encrypted_model_fields.fields import EncryptedTextField

from json import loads as json_loads

from ..k8s.models import Namespace
from ..k8s.constants import R_STATES, SECRET_TYPES

from core.model_fields import UUID7StringField
from core.utils import similar_time


class Secret(models.Model):
    secretid = UUID7StringField(auto_created=True)
    name = models.CharField(max_length=64)
    type = models.CharField(max_length=16, choices=SECRET_TYPES, default='opaque')
    data = EncryptedTextField()
    namespace = models.ForeignKey(Namespace, on_delete=models.CASCADE, related_name='secrets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def info(self):
        return {
            'secretid': self.secretid,
            'name': self.name,
            'type': self.type,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    def values(self):
        return json_loads(self.data) if self.data else {}

    @property
    def updated_at_pretty(self):
        if similar_time(self.created_at, self.updated_at):
            return 'Never'
        return self.updated_at

    class Meta:
        db_table = 'secret_store'
