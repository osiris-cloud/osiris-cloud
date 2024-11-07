from celery import shared_task
from .models import ContainerRegistry


@shared_task(name='create_registry')
def create_registry(crid) -> None:
    cr = ContainerRegistry.objects.get(crid=crid)
    pass


@shared_task(name='patch_registry')
def patch_registry(crid) -> None:
    cr = ContainerRegistry.objects.get(crid=crid)
    pass


@shared_task(name='delete_registry')
def delete_registry(crid) -> None:
    cr = ContainerRegistry.objects.get(crid=crid)
    cr.delete()
    pass

