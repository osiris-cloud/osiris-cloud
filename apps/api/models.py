from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from os import urandom
from binascii import hexlify

from core.model_fields import UUID7StringField

from .utils import extract_app_name


class AccessToken(models.Model):
    keyid = UUID7StringField(primary_key=True)
    key = models.CharField(max_length=40, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='auth_tokens', on_delete=models.CASCADE)
    name = models.CharField(max_length=64, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list)
    can_write = models.BooleanField(default=False)
    expiration = models.DateTimeField(null=True, default=None)
    system_use = models.BooleanField(default=False)

    def info(self):
        return {
            'keyid': self.keyid,
            'name': self.name,
            'created_at': self.created,
            'last_used': self.last_used,
            'scopes': self.scopes,
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

    def has_permission(self, url_path, method):
        """
        Check if token has permission for the given URL and HTTP method
        """

        is_write_method = method in ('PUT', 'PATCH', 'DELETE')
        allowed = False

        if ('global' in self.scopes) or (extract_app_name(url_path) in self.scopes):
            allowed = True

        return (allowed and self.can_write) if is_write_method else allowed

    def is_expired(self):
        return self.expiration and self.expiration <= timezone.now()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        AccessToken.objects.create(user=instance,
                                   name='SYS_KEY',
                                   scopes=['container_registry'],
                                   can_write='True',
                                   system_use=True)
