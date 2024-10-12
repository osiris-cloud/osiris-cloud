from celery import shared_task
from core.utils import deserialize_obj


@shared_task(name='create_registry')
def create_registry(cr) -> None:
    """
    Create a new registry
    """
    cr = deserialize_obj(cr)
    pass
