from celery import shared_task
from core.utils import deserialize_obj


@shared_task(name='create_secret')
def create_secret(secret) -> None:
    secret = deserialize_obj(secret)
    pass


@shared_task(name='update_registry')
def update_secret(secret) -> None:
    secret = deserialize_obj(secret)
    pass


@shared_task(name='delete_secret')
def delete_secret(secret) -> None:
    secret = deserialize_obj(secret)
    secret.delete()
    pass
