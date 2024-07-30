from django.db import models


class VM(models.Model):
    name = models.CharField(max_length=100)
    cpu = models.IntegerField()
    memory = models.IntegerField()
    disk = models.IntegerField()
    status = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    type = models.CharField(max_length=32)

    def __str__(self):
        return self.name


class VMLog(models.Model):
    vm = models.ForeignKey(VM, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.action


class IPBinds(models.Model):
    ip = models.GenericIPAddressField()
    mac = models.CharField(max_length=100)
    vm = models.ForeignKey(VM, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ip
