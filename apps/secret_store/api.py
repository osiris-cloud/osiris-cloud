import logging

from django.http import JsonResponse
from rest_framework.decorators import api_view

from json import dumps as json_dumps
from json import JSONDecodeError

from .models import Secret
from ..k8s.models import Namespace

from core.utils import success_message, error_message
from ..users.utils import get_default_ns
from .utils import validate_secret_creation, validate_secret_update


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def secret_store(request, nsid=None, secretid=None, action=None):
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
        ns = Namespace.objects.get(nsid=nsid)
        role = ns.get_role(request.user)
        if role is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

        if request.method in ('PUT', 'PATCH', 'DELETE') and role == 'viewer':
            return JsonResponse(error_message('Permission denied'), status=403)

        secret_data = request.data
        match request.method:
            case 'GET':
                if s_type := request.GET.get('type'):
                    print(s_type)
                    if s_type not in ('opaque', 'dockerconfig'):
                        return JsonResponse(error_message('Invalid secret type'), status=400)

                secrets_filter = {'secretid': secretid} if secretid else {}
                if s_type:
                    secrets_filter['type'] = s_type

                secrets = Secret.objects.filter(namespace=ns, **secrets_filter)
                result = [sec.info() for sec in secrets]
                if secretid:
                    if not result:
                        return JsonResponse(error_message('Secret not found'), status=404)
                    return JsonResponse(success_message('Get secret', {'secret': result[0]}), status=200)

                return JsonResponse(success_message('Get secrets', {'secrets': result}), status=200)

            case 'POST':
                secret = Secret.objects.get(namespace=ns, secretid=secretid)
                if action == 'values':
                    return JsonResponse(success_message('Get secret values', {'values': secret.values()}), status=200)

                return JsonResponse(error_message('Invalid action'), status=400)

            case 'PUT':
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

                return JsonResponse(success_message('Create Secret', {'secret': secret.info()}))

            case 'PATCH':
                valid, err = validate_secret_update(secret_data)
                if not valid:
                    return JsonResponse(error_message(err))

                secret = Secret.objects.get(namespace=ns, secretid=secretid)
                if secret_name := secret_data.get('name'):
                    secret.name = secret_name

                secret_values = secret_data.get('values')
                if secret_values is not None:
                    secret.data = json_dumps(secret_values)

                secret.save()

                return JsonResponse(success_message('Update Secret', {'secret': secret.info()}))

            case "DELETE":
                secret = Secret.objects.get(namespace=ns, secretid=secretid)
                secret.delete()

                return JsonResponse(success_message('Delete Secret'))

    except Namespace.DoesNotExist:
        return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

    except Secret.DoesNotExist:
        return JsonResponse(error_message('Secret not found'), status=404)

    except (JSONDecodeError, ValueError):
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)
