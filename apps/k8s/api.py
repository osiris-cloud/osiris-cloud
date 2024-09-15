import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from json import loads as json_loads
from json import dumps as json_dumps

from core.utils import success_message, error_message, random_str
from .utils import validate_secret_creation, validate_secret_update
from ..k8s.models import Namespace, NamespaceRoles, Secret
from ..users.models import User

def get_user_default_ns(user: User) -> Namespace:
    return NamespaceRoles.objects.filter(user=user, role='owner', namespace__default=True).first().namespace

@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
def secret(request, nsid=None, secret_name=None):
    try:
        if not nsid:
            return JsonResponse(error_message('No namespace ID provided'))
        
        if nsid == 'default':
            ns = get_user_default_ns(request.user)
            nsid = ns.nsid
        else:
            ns = Namespace.objects.filter(nsid=nsid).first()

        if not ns:
            return JsonResponse(error_message('Namespace not found or user does not have sufficient permission to access secrets'))
        
        match request.method:
            case 'GET':               
                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('Namespace not found or user does not have sufficient permission to access secrets'))
                
                if secret_name:
                    secret = Secret.objects.filter(namespace=ns, name=secret_name).first()
                    if not secret:
                        return JsonResponse(error_message('Secret not found'))
                    
                    secret_info = secret.info()
                    return JsonResponse(success_message('Get secret', {'nsid': nsid, 'secret': secret_info}))
                else:
                    result = []
                    secrets = Secret.objects.filter(namespace=ns)
                    for secret in secrets:
                        secret_info = secret.info()
                        result.append(secret_info)

                    return JsonResponse(success_message('Get secrets', {'nsid': nsid, 'secrets': result}))

            case 'POST':
                if 'data' not in request.POST:
                    return JsonResponse(error_message('No data provided'))
                
                secret_data = json_loads(request.POST['data'])

                valid, resp = validate_secret_creation(secret_data)

                if not valid:
                    return JsonResponse(resp)
                
                new_secret_name = secret_data.get('name')
                secret_values = secret_data.get('values')

                ns = Namespace.objects.filter(nsid=nsid).first()

                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('Namespace not found or user does not have sufficient permission to access secrets'))

                secret = Secret.objects.filter(namespace=ns, name=new_secret_name).first()
                if secret:
                    return JsonResponse(error_message('Secret already exists'))
                
                try:
                    secret_values_json = json_dumps(secret_values)  # Convert to JSON string
                    secret = Secret.objects.create(namespace=ns, name=new_secret_name, data=secret_values_json)
                except Exception as e:
                    logging.error(str(e))
                    return JsonResponse(error_message('Failed to create secret'))          

                return JsonResponse(success_message('Create Secret', {'nsid': nsid, 'secret': secret.info()}))
            
            case 'PATCH':
                if not secret_name:
                    return JsonResponse(error_message('No secret name provided'))
                
                if 'data' not in request.POST:
                    return JsonResponse(error_message('No data provided'))
                
                secret_data = json_loads(request.POST['data'])
                    
                valid, resp = validate_secret_update(secret_data)

                if not valid:
                    return JsonResponse(resp)
                
                secret_values = secret_data.get('values')

                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('Namespace not found or user does not have sufficient permission to access secrets'))

                secret = Secret.objects.filter(namespace=ns, name=secret_name).first()
                if not secret:
                    return JsonResponse(error_message('Secret not found'))
                
                try:
                    secret_values_json = json_dumps(secret_values)  # Convert to JSON string
                    secret.data = secret_values_json
                    secret.save()
                except Exception as e:
                    logging.error(str(e))
                    return JsonResponse(error_message('Failed to update secret'))          

                return JsonResponse(success_message('Update Secret', {'nsid': nsid, 'secret': secret.info()}))
            
            case "DELETE":
                if not secret_name:
                    return JsonResponse(error_message('No secret name provided'))

                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('Namespace not found or user does not have sufficient permission to access secrets'))

                secret = Secret.objects.filter(namespace=ns, name=secret_name).first()
                if not secret:
                    return JsonResponse(error_message('Secret not found'))
                
                try:
                    secret.delete()
                except Exception as e:
                    logging.error(str(e))
                    return JsonResponse(error_message('Failed to delete secret'))          

                return JsonResponse(success_message('Delete Secret', {'name': secret_name}))
            
    except Exception as e:
        logging.error(str(e))
        return JsonResponse(error_message(str(e)))