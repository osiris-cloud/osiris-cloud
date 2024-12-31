import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from json import loads as json_loads

from .models import RegistryWebhook, ContainerRegistry

from core.utils import success_message, error_message
from core.settings import env


@csrf_exempt
@require_http_methods(["POST"])
def registry_webhook(request):
    try:
        auth = request.headers.get('Authorization')
        if auth != env.registry_webhook_secret:
            return JsonResponse(error_message('Unauthorized'), status=401)

        post_data = json_loads(request.body.decode())
        events = post_data['events']
        for event in events:
            webhook = RegistryWebhook(action=event['action'], content=event)
            repo, target = event['target']['repository'].split('/', 1)
            webhook.registry = ContainerRegistry.objects.get(repo=repo)
            webhook.target = target
            webhook.save()

        return JsonResponse(success_message('Webhook processed'), status=200)
    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message(), status=500)
