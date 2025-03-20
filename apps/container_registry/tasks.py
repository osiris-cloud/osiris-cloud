import logging

from celery import shared_task
from .models import ContainerRegistry


@shared_task(name='delete_registry')
def delete_registry(crid) -> None:
    cr = ContainerRegistry.objects.get(crid=crid)
    stats = cr.stat()
    try:
        for sub in stats:
            for tag in sub['tags']:
                cr.delete_image(sub['sub'], tag['name'])

        owner = cr.namespace.owner

        owner.usage.registry -= 1

        cr.delete()

    except Exception as e:
        logging.exception(e)
