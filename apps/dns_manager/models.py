from django.db import models

from ..users.models import User


class ARecord(models.Model):
    name = models.CharField(max_length=45)
    value = models.GenericIPAddressField()
    ttl = models.PositiveIntegerField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'a_record'
        verbose_name = 'A Record'
        verbose_name_plural = 'A Records'


class CNameRecord(models.Model):
    name = models.CharField(max_length=45)
    value = models.CharField(max_length=45)
    ttl = models.PositiveIntegerField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'cname_record'
        verbose_name = 'CNAME Record'
        verbose_name_plural = 'CNAME Records'


class TXTRecord(models.Model):
    name = models.CharField(max_length=50)
    value = models.TextField()
    ttl = models.PositiveIntegerField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'txt_record'
        verbose_name = 'TXT Record'
        verbose_name_plural = 'TXT Records'
