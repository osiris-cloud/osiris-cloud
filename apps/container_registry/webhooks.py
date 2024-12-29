import logging

from django.http import JsonResponse
from .models import RegistryWebhook
from core.utils import success_message, error_message
from core.settings import env


def registry_webhook(request):
    if request.method != 'POST':
        return JsonResponse(error_message('Not allowed'), status=400)
    try:
        auth = request.headers.get('Authorization')
        if auth != env.registry_webhook_token:
            return JsonResponse(error_message('Unauthorized'), status=401)

        events = request.data.get('events')
        for event in events:
            RegistryWebhook.objects.create(repository=event['target']['repository'],
                                           action=event['action'],
                                           content=event
                                           ).save()

        return JsonResponse(success_message('Webhook processed'), status=200)
    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message(), status=500)
