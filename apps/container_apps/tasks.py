from celery import shared_task

from .resources import AppResource
from .models import ContainerApp


@shared_task(bind=True, name='create_deployment', max_retries=3)
def create_deployment(self, appid) -> None:
    app = ContainerApp.objects.get(appid=appid)
    if app.namespace.state != 'active':
        return
    creator = AppResource()
    creator.create_app(app)


@shared_task(name='patch_deployment')
def patch_deployment(appid) -> None:
    app = ContainerApp.objects.get(appid=appid)
    creator = AppResource()
    creator.update_app(app)
    app.state = 'active'


@shared_task(bind=True, name='delete_deployment', max_retries=3)
def delete_deployment(self, appid) -> None:
    app = ContainerApp.objects.get(appid=appid)

    creator = AppResource()
    creator.delete_app(app)

    for container in app.containers.all():
        container.delete()
    for custom_domain in app.custom_domains.all():
        custom_domain.delete()
    for volume in app.pvcs.all():
        volume.delete()
    if app.hpa:
        app.hpa.delete()
    app.delete()


@shared_task(bind=True, name='redeploy', max_retries=3)
def redeploy(self, appid) -> None:
    app = ContainerApp.objects.get(appid=appid)
    creator = AppResource()
    creator.restart_deployment(app)
