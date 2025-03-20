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

    # Update usage counts
    owner = app.namespace.owner

    owner.usage.cpu -= app.cpu_limit
    owner.usage.memory -= app.memory_limit
    owner.usage.disk -= app.disk_limit

    app_resource.delete()
    owner.usage.save()


@shared_task(bind=True, name='redeploy', max_retries=3)
def restart(self, appid) -> None:
    app = ContainerApp.objects.get(appid=appid)
    app_resource = AppResource(app)
    app_resource.redeploy()
