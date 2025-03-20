from django.db import models

from ..users.models import User
from ..vm.models import VM


class IP(models.Model):
    namespace = models.ForeignKey('apps.infra.Namespace', on_delete=models.CASCADE)
    address = models.GenericIPAddressField()
    mac = models.CharField(max_length=17, null=True, blank=True)
    vm = models.ForeignKey(VM, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ip_address'
