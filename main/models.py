from django.db import models
from django.contrib import admin


class Settings(models.Model):
    key = models.CharField(max_length=64, unique=True)
    value = models.TextField()

    class Meta:
        db_table = 'settings'


@admin.register(Settings)
class SettingsAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')
    search_fields = ('key',)
