import string
import random
import logging

from celery import shared_task
from celery.contrib.abortable import AbortableAsyncResult

from apps.k8s.utils import make_k8s_client, create_namespace
from .models import Namespace
from apps.users.models import Limit

from core.utils import deserialize_obj


@shared_task(bind=True, name='init_k8s_for_user', max_retries=3)
def init_k8s_for_user(self, user):
    user = deserialize_obj(user)
    try:
        v1 = make_k8s_client()
        ns_name = user.username + '-' + ''.join(
            [random.choice(string.ascii_lowercase + string.digits) for _ in range(5)])
        if create_namespace(v1, ns_name):  # Create a namespace for the user
            ns = Namespace.objects.create(name=ns_name, owner=user, default=True)
            Limit.objects.create(user=user, cpu=4, memory=2, disk=30, public_ip=0)
            logging.info(f"Namespace {ns_name} created for user {user.username} with task id {self.request.id}")
            return True
        raise Exception
    except Exception as e:
        logging.exception(f"Failed to create namespace for user {user.username} with task id {self.request.id}: {e}")
        self.retry(exc=e, countdown=60)
