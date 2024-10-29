import logging
from rest_framework.decorators import api_view
from django.http import JsonResponse

from core.utils import success_message, error_message

from ..k8s.models import Namespace, Event


@api_view(['GET', 'POST'])
def event(request, event_id=None):
    try:
        match request.method:
            case 'GET':
                # Get all events for all namespaces user is part of 
                namespaces = Namespace.objects.filter(namespaceroles__user=request.user, locked=False)
                # Get all events for those namespaces
                events = Event.objects.filter(namespace__in=namespaces)
                result = []
                for event in events:
                    event_info = event.info()
                    result.append(event_info)

                return JsonResponse(success_message('Get events', {'events': result}))

            case 'POST':
                if not event_id:
                    return JsonResponse(error_message('No event id provided'))

                event = Event.objects.filter(event_id=event_id).first()

                if not event:
                    return JsonResponse(error_message('Event not found'))

                # Update event status to read
                try:
                    event.read = True
                    event.save()

                except Exception as e:
                    logging.error(str(e))
                    return JsonResponse(error_message('Failed to update event status'))

                return JsonResponse(success_message('Update event status', {'event': event.info()}))

    except Exception as e:
        logging.error(str(e))
        return JsonResponse(error_message(str(e)))
