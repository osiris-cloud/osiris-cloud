from __future__ import absolute_import, unicode_literals
from celery import Celery
from django.conf import settings
from os import environ
from ssl import CERT_REQUIRED

environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery('core',
             redis_backend_use_ssl={'ssl_cert_reqs': CERT_REQUIRED},
             broker_connection_retry_on_startup=True,
             worker_cancel_long_running_tasks_on_connection_loss=False,
             )

# Using a string here means the worker doesn't have to serialize the configuration object to child processes
# - namespace='CELERY' means all celery-related configuration keys should have a `CELERY_` prefix

app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print("Request: {0!r}".format(self.request))
