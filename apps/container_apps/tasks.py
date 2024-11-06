from celery import shared_task
from core.settings import env

from .models import ContainerApp


@shared_task(bind=True, name='create_deployment', max_retries=3)
def create_deployment(self, appid) -> None:
    pass

@shared_task(name='patch_deployment')
def patch_deployment() -> None:
    pass


@shared_task(name='delete_deployment')
def delete_deployment() -> None:
    pass


@shared_task(name='redeploy')
def redeploy() -> None:
    pass
