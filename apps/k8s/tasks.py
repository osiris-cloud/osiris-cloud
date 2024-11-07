from celery import shared_task
from celery.contrib.abortable import AbortableAsyncResult

from apps.k8s.utils import create_namespace
from .models import Namespace


@shared_task(bind=True, name='init_k8s_for_user', max_retries=1)
def init_namespace(self, nsid: str) -> bool:
    ns = Namespace.objects.get(nsid=nsid)
    if ns.state == 'active':
        return True

    if create_namespace(nsid):
        ns.state = 'active'
        ns.save()
        return True
    else:
        ns.state = 'error'
        ns.save()
