from django.db.models import Sum

from ..container_registry.models import ContainerRegistry
from ..k8s.models import Namespace
# from ..vm.models import VM


def get_ns_usage(ns: Namespace) -> dict:  # TODO
    """
    Get the total usage of a namespace
    :param ns: namespace
    :return: total usage
    """
    resources = {
        "cpu": 0,
        "memory": 0,
        "disk": 0,
        "public_ip": 0,
        "gpu": 0,
        "registry": 0,
    }

    # resources["cpu"] = VM.objects.filter(namespace=ns).aggregate(Sum("cpu"))
    # resources["memory"] = VM.objects.filter(namespace=ns).aggregate(Sum("memory"))
    # resources["registry"] = ContainerRegistry.objects.filter(namespace=ns).count()

    return resources
