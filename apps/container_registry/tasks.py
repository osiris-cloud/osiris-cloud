from celery import shared_task
from core.utils import deserialize_obj


@shared_task(name='create_registry')
def create_registry(cr) -> None:
    cr = deserialize_obj(cr)
    pass


@shared_task(name='patch_registry')
def patch_registry(cr) -> None:
    cr = deserialize_obj(cr)
    pass


@shared_task(name='delete_registry')
def delete_registry(cr) -> None:
    cr = deserialize_obj(cr)
    cr.delete()
    pass

