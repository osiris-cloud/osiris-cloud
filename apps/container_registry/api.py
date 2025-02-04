import logging

from json import JSONDecodeError
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.core.exceptions import ValidationError

from .models import ContainerRegistry
from ..infra.models import Namespace

from core.utils import success_message, error_message
from .utils import validate_registry_spec, validate_registry_update_spec
from ..users.utils import get_default_ns

from .tasks import delete_registry


@api_view(['POST'])
def name_check(request):
    """
    Check if registry name is available
    """
    try:
        repo_name = request.data.get('repo', '').strip()
        if not repo_name:
            return JsonResponse(error_message('Repo name is required'), status=400)

        return JsonResponse(
            success_message("Check availability", {
                'available': not bool(ContainerRegistry.objects.filter(repo=repo_name).exists())
            })
        )

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
def container_registry(request, nsid=None, crid=None, action=None):
    """
    API endpoint for Container Registry
    """
    if nsid is None:
        return JsonResponse(error_message('Namespace id is required'), status=400)

    if nsid == 'default':
        if not (nsid := request.session.get('default_ns')):
            nsid = request.session['default_ns'] = get_default_ns(request.user).nsid

    if (request.method in ['PATCH, DELETE']) and crid is None:
        return JsonResponse(error_message('crid is required'), status=400)

    try:
        ns = Namespace.objects.filter(nsid=nsid).first()
        if ns is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)
        role = ns.get_role(request.user)
        if role is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

        if role == 'viewer' and request.method in ('PUT', 'PATCH', 'DELETE'):
            return JsonResponse(error_message('Permission denied'), status=403)

        cr_data = request.data
        match request.method:
            case 'GET':  # Get all registries in the namespace
                cr_filter = {'crid': crid} if crid else {}
                registries = ContainerRegistry.objects.filter(namespace=ns, **cr_filter)
                result = [cr.info() for cr in reversed(registries)]
                if crid:
                    if not result:
                        return JsonResponse(error_message('Registry not found'), status=404)
                    return JsonResponse(success_message('Get registry', {'registry': result[0]}), status=200)

                return JsonResponse(success_message('Get registry', {'registries': result}), status=200)

            case 'POST':
                cr = ContainerRegistry.objects.get(namespace=ns, crid=crid)

                if action == 'stat':
                    result = cr.stat()
                    return JsonResponse(success_message('Get registry stat', {'stats': result}), status=200)

                elif action == 'delete':
                    if role == 'viewer':
                        return JsonResponse(error_message('Permission denied'), status=403)

                    image = cr_data.get('image')
                    tag = cr_data.get('tag')
                    if (not image) or (not tag):
                        return JsonResponse(error_message('Image and tag are required'), status=400)
                    result = cr.delete_image(image, tag)
                    return JsonResponse(
                        success_message('Delete registry image')
                        if result
                        else error_message('Failed to delete image')
                        , status=200 if result else 500
                    )

                return JsonResponse(error_message('Invalid action'), status=400)

            case 'PUT':  # Create a new registry
                valid, err = validate_registry_spec(cr_data)
                if not valid:
                    return JsonResponse(error_message(err), status=400)

                cr = ContainerRegistry(namespace=ns, name=cr_data['name'], repo=cr_data['repo_name'],
                                       public=cr_data.get('public', False), state='active')

                cr.save()

                return JsonResponse(success_message('Create registry', {'registry': cr.info()}), status=201)

            case 'PATCH':  # Update registry
                cr = ContainerRegistry.objects.get(namespace=ns, crid=crid)

                valid, err = validate_registry_update_spec(cr_data)
                if not valid:
                    return JsonResponse(error_message(err), status=400)

                name = cr_data.get('name')
                r_pub = cr_data.get('public')

                if name is not None:
                    cr.name = name
                if r_pub is not None:
                    cr.public = r_pub

                cr.save()

                return JsonResponse(success_message('Update registry', {'registry': cr.info()}), status=200)

            case 'DELETE':  # Delete registry
                if role == 'viewer':
                    return JsonResponse(error_message('Permission denied'), status=403)

                cr = ContainerRegistry.objects.get(namespace=ns, crid=crid)

                cr.state = 'deleting'
                cr.save()

                delete_registry.delay(crid)

                return JsonResponse(success_message('Delete registry'), status=200)

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except ValidationError:
        return JsonResponse(error_message('Invalid crid/input data type'), status=400)

    except ContainerRegistry.DoesNotExist:
        return JsonResponse(error_message('Registry not found'), status=404)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)
