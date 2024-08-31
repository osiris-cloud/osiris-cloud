import ast
import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from json import loads as json_loads

from core.utils import success_message, error_message, random_str
from .utils import validate_secret_creation, validate_secret_update
from ..k8s.models import Namespace, Secret

@csrf_exempt
@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
def secret(request, nsid=None, secret_name=None):
    try:
        match request.method:
            case 'GET':
                if not nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                ns = Namespace.objects.filter(nsid=nsid).first()

                if not ns:
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))
                
                if request.user not in ns.get_users():
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))

                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('Only the owner or a manager can access secrets'))
                
                if secret_name:
                    secret = Secret.objects.filter(namespace=ns, name=secret_name).first()
                    if not secret:
                        return JsonResponse(error_message('Secret not found'))
                    
                    secret_info = secret.info()
                    secret_info['values'] = ast.literal_eval(secret_info['values'])  # Convert str to dict
                    return JsonResponse(success_message('Get secret', {'secret': secret_info}))
                else:
                    result = []
                    secrets = Secret.objects.filter(namespace=ns)
                    for secret in secrets:
                        secret_info = secret.info()
                        secret_info['values'] = ast.literal_eval(secret_info['values'])  # Convert str to dict
                        result.append(secret_info)

                    return JsonResponse(success_message('Get secrets', {'secrets': result}))

            case 'POST':
                if not nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                secret_data = json_loads(request.body)
                valid, resp = validate_secret_creation(secret_data)

                if not valid:
                    return JsonResponse(resp)
                
                new_secret_name = secret_data.get('name')
                secret_values = secret_data.get('values')

                ns = Namespace.objects.filter(nsid=nsid).first()
                
                # If user is not owner or manager of namespace, return error
                if not ns:
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))

                if request.user not in ns.get_users():
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))

                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('Only the owner or a manager can access secrets'))

                secret = Secret.objects.filter(namespace=ns, name=new_secret_name).first()
                if secret:
                    return JsonResponse(error_message('Secret already exists'))
                
                try:
                    with transaction.atomic():
                        secret = Secret.objects.create(namespace=ns, name=new_secret_name, data=secret_values)

                except IntegrityError:
                    return JsonResponse(error_message(str(e)))          

                return JsonResponse(success_message('Create Secret', secret.info()))
            
            case 'PATCH':
                if not nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                if not secret_name:
                    return JsonResponse(error_message('No secret name provided'))
                
                secret_data = json_loads(request.body)
                valid, resp = validate_secret_update(secret_data)

                if not valid:
                    return JsonResponse(resp)
                
                secret_values = secret_data.get('values')

                ns = Namespace.objects.filter(nsid=nsid).first()
                
                if not ns:
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))

                if request.user not in ns.get_users():
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))

                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('Only the owner or a manager can access secrets'))

                secret = Secret.objects.filter(namespace=ns, name=secret_name).first()
                if not secret:
                    return JsonResponse(error_message('Secret not found'))
                
                try:
                    with transaction.atomic():
                        secret.data = secret_values
                        secret.save()
                except IntegrityError:
                    return JsonResponse(error_message(str(e)))          

                return JsonResponse(success_message('Update Secret', secret.info()))
            
            case "DELETE":
                if not nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                if not secret_name:
                    return JsonResponse(error_message('No secret name provided'))
                
                ns = Namespace.objects.filter(nsid=nsid).first()
                
                if not ns:
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))

                if request.user not in ns.get_users():
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))

                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('Only the owner or a manager can access secrets'))

                secret = Secret.objects.filter(namespace=ns, name=secret_name).first()
                if not secret:
                    return JsonResponse(error_message('Secret not found'))
                
                try:
                    with transaction.atomic():
                        secret.delete()
                except IntegrityError:
                    return JsonResponse(error_message(str(e)))          

                return JsonResponse(success_message('Delete Secret', {'name': secret_name}))
            
    except Exception as e:
        logging.error(str(e))
        return JsonResponse(error_message(str(e)))