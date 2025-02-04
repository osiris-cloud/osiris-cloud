import logging

from celery import shared_task
from celery.contrib.abortable import AbortableAsyncResult

from apps.infra.utils import create_namespace
from .models import Namespace


@shared_task
def error_handler(request, exc, traceback):
    logger = logging.getLogger('celery')
    logger.error(f'Error in task: {request.id}', exc_info=exc)


@shared_task(bind=True, name='init_k8s_for_user', max_retries=30, default_retry_delay=60)
def init_namespace(self, nsid: str) -> bool:
    try:
        ns = Namespace.objects.get(nsid=nsid)
        if ns.state == 'active':
            return True
        elif create_namespace(nsid):
            ns.state = 'active'
            ns.save()
            return True
        else:
            ns.state = 'error'
            ns.save()
            raise self.retry(countdown=60)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
