from django.db import models
from django.utils import timezone
from os import urandom
from binascii import hexlify

from core.model_fields import UUID7StringField

from ..users.models import User

from .utils import extract_app_name


class AccessToken(models.Model):
    keyid = UUID7StringField(primary_key=True)
    key = models.CharField(max_length=40, unique=True)
    user = models.ForeignKey(User, related_name='auth_tokens', on_delete=models.CASCADE)
    name = models.CharField(max_length=64, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list)
    can_write = models.BooleanField(default=False)
    expiration = models.DateTimeField(null=True, default=None)
    attributes = models.JSONField(default=dict)

    def info(self):
        return {
            'keyid': self.keyid,
            'name': self.name,
            'created_at': self.created,
            'last_used': self.last_used,
            'scopes': self.scopes,
            'sub_scope': self.attributes,
            'can_write': self.can_write,
            'expiration': self.expiration,
        }

    def generate_key(self):
        return hexlify(urandom(20)).decode()

    def rotate_key(self):
        self.key = self.generate_key()
        self.save()

    def update_last_used(self):
        self.last_used = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super().save(*args, **kwargs)

    def has_permission(self, url_path: str, method: str) -> bool:
        """
        Check if token has permission for the given URL and HTTP method
        """
        if self.user.role == 'blocked':
            return False

        if self.is_expired():
            return False

        is_write_method = method in ('PUT', 'PATCH', 'DELETE', 'WS:W')

        if (self.user.role == 'guest') and is_write_method:
            return False

        allowed = False

        app = extract_app_name(url_path)

        if ('global' in self.scopes) or (app in self.scopes):
            allowed = True

        if sub_scopes := self.attributes.get(app):
            allowed = 'all' in sub_scopes

        return (allowed and self.can_write) if is_write_method else allowed

    def is_expired(self) -> bool:
        return self.expiration and self.expiration <= timezone.now()

    def has_app_permission(self, app: str, method: str) -> bool:
        return self.has_permission(f"x/{app}", method)
