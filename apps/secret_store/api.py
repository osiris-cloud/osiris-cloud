import logging

from django.http import JsonResponse
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view

from json import dumps as json_dumps
from json import JSONDecodeError
from uuid_utils import uuid7

from .models import Secret
from ..k8s.models import Namespace

from core.utils import success_message, error_message, serialize_obj
from ..users.utils import get_default_ns
from .utils import validate_secret_creation, validate_secret_update

from .tasks import create_secret, update_secret, delete_secret


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def secret_store(request, nsid=None, secretid=None):
    """
    API endpoint for Secret Store
    """
    if nsid is None:
        return JsonResponse(error_message('Namespace id is required'), status=400)

    if nsid == 'default':
        if not (nsid := request.session.get('default_ns')):
            nsid = request.session['default_ns'] = get_default_ns(request.user).nsid

    if (request.method in ['PATCH, DELETE']) and secretid is None:
        return JsonResponse(error_message('secretid is required'), status=400)

    try:
        ns = Namespace.objects.filter(nsid=nsid).first()
        if ns is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

        role = ns.get_role(request.user)
        if role is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

        if secretid:
            secretid = uuid7(secretid)

        secret_data = request.data

        match request.method:
            case 'GET':
                secrets_filter = {'secretid': secretid} if secretid else {}
                secrets = Secret.objects.filter(namespace=ns, **secrets_filter)
                result = [sec.info() for sec in secrets]
                if secretid:
                    if not result:
                        return JsonResponse(error_message('Secret not found'), status=404)
                    return JsonResponse(success_message('Get secret', result[0]), status=200)

                return JsonResponse(success_message('Get secrets', {'secrets': result}), status=200)

            case 'PUT':
                if role not in ['owner', 'manager']:
                    return JsonResponse(error_message('Permission denied'), status=403)

                valid, err = validate_secret_creation(secret_data)
                if not valid:
                    return JsonResponse(error_message(err), status=400)

                secret_name = secret_data.get('name').strip()
                secret_values_json = json_dumps(secret_data.get('values'))  # Convert to JSON string

                secret = Secret.objects.create(
                    namespace=ns,
                    name=secret_name,
                    type=secret_data.get('type'),
                    data=secret_values_json,
                )

                secret.save()
                create_secret.delay(serialize_obj(secret))

                return JsonResponse(success_message('Create Secret', secret.info()))

            case 'PATCH':
                if role not in ['owner', 'manager']:
                    return JsonResponse(error_message('Permission denied'), status=403)

                valid, err = validate_secret_update(secret_data)
                if not valid:
                    return JsonResponse(error_message(err))

                secret = Secret.objects.filter(namespace=ns, secretid=secretid).first()
                if not secret:
                    return JsonResponse(error_message('Secret not found'), status=404)

                if secret_name := secret_data.get('name'):
                    secret.name = secret_name
                if secret_values := secret_data.get('values'):
                    secret.data = json_dumps(secret_values)

                secret.save()
                update_secret.delay(serialize_obj(secret))

                return JsonResponse(success_message('Update Secret', secret.info()))

            case "DELETE":
                if role not in ['owner', 'manager']:
                    return JsonResponse(error_message('Permission denied'), status=403)

                secret = Secret.objects.filter(namespace=ns, secretid=secretid).first()
                if not secret:
                    return JsonResponse(error_message('Secret not found'), status=404)

                delete_secret.delay(serialize_obj(secret))

                return JsonResponse(success_message('Delete Secret'))

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except (TypeError, ValidationError):
        return JsonResponse(error_message('Invalid secretid/input data type'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)
