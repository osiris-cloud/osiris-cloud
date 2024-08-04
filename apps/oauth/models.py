from django.db import models
from django.contrib import admin

from ..users.models import User


class NYUUser(models.Model):
    id = models.AutoField(primary_key=True)
    netid = models.CharField(max_length=16, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    affiliation = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nyu')

    class Meta:
        db_table = 'nyu_user'


@admin.register(NYUUser)
class NYUUserAdmin(admin.ModelAdmin):
    list_display = ('netid', 'first_name', 'last_name', 'affiliation')
    search_fields = ('netid', 'first_name', 'last_name')
    list_filter = ('affiliation',)


class GithubUser(models.Model):
    id = models.AutoField(primary_key=True)
    uid = models.IntegerField(unique=True)
    username = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=320, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='github', null=True, blank=True)

    class Meta:
        db_table = 'github_user'


@admin.register(GithubUser)
class GithubUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'name', 'email')
    search_fields = ('username', 'name')

