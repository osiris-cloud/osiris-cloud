from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib import admin
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

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


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'last_login')
    search_fields = ('username', 'first_name', 'last_name')
    list_filter = ('role', 'last_login')


class Event(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    message = models.TextField()
    related_link = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)


class Group(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    owners = models.ManyToManyField(User, related_name='groups_owned')
    members = models.ManyToManyField(User, related_name='groups_partof')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
