from celery import shared_task

from .resource import AppResource
from .models import ContainerApp


@shared_task(bind=True, name='create_deployment', max_retries=3)
def apply_deployment(self, appid) -> None:
    app = ContainerApp.objects.get(appid=appid)
    app_resource = AppResource(app)
    app_resource.apply()


@shared_task(bind=True, name='delete_deployment', max_retries=3)
def delete_deployment(self, appid) -> None:
    app = ContainerApp.objects.get(appid=appid)
    app_resource = AppResource(app)
    app_resource.delete()


@shared_task(bind=True, name='redeploy', max_retries=3)
def restart(self, appid) -> None:
    app = ContainerApp.objects.get(appid=appid)
    app_resource = AppResource(app)
    app_resource.redeploy()
