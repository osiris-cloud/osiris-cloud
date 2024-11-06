import logging
import uuid
from json import JSONDecodeError

from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.core.exceptions import ValidationError

from .models import ContainerRegistry
from ..k8s.models import Namespace

from core.utils import success_message, error_message
from core.utils import serialize_obj
from .utils import validate_registry_spec, validate_registry_update_spec
from ..users.utils import get_default_ns

from .tasks import create_registry, patch_registry, delete_registry


@api_view(['POST'])
def name_check(request):
    """
    Check if registry name is available
    """
    try:
        slug = request.data.get('slug', '').strip()
        if not slug:
            return JsonResponse(error_message('Slug is required'), status=400)

        return JsonResponse(
            success_message("Check availability", {
                'available': not bool(ContainerRegistry.objects.filter(slug=slug).exists())
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

    if (request.user.role in ('guest', 'blocked')) and (request.method in ('PUT', 'PATCH', 'DELETE')):
        return JsonResponse(error_message('Permission denied'), status=403)

    try:
        ns = Namespace.objects.filter(nsid=nsid).first()
        if ns is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)
        role = ns.get_role(request.user)
        if role is None:
            return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

        cr_data = request.data
        match request.method:
            case 'GET':
                # Get all registries in the namespace
                cr_filter = {'crid': crid} if crid else {}
                registries = ContainerRegistry.objects.filter(namespace=ns, **cr_filter)
                result = [cr.info() for cr in reversed(registries)]
                if crid:
                    if not result:
                        return JsonResponse(error_message('Registry not found'), status=404)
                    return JsonResponse(success_message('Get registry', {'registry': result[0]}), status=200)

                return JsonResponse(success_message('Get registry', {'registries': result}), status=200)

            case 'POST':
                cr = ContainerRegistry.objects.filter(namespace=ns, crid=crid).first()
                if cr is None:
                    return JsonResponse(error_message('Registry not found'), status=404)

                if action == 'creds':
                    return JsonResponse(success_message('Get login', {'creds': cr.get_login()}), status=200)

                elif action == 'stat':
                    result = cr.stat()
                    return JsonResponse(success_message('Get registry stat', {'stats': result}), status=200)

                elif action == 'delete':
                    if role == 'viewer':
                        return JsonResponse(error_message('Permission denied'), status=403)

                    repo = cr_data.get('image')
                    tag = cr_data.get('tag')
                    if (not repo) or (not tag):
                        return JsonResponse(error_message('Image and tag is required'), status=400)
                    result = cr.delete_image(repo, tag)
                    return JsonResponse(
                        success_message('Delete registry image')
                        if result
                        else error_message('Failed to delete image')
                        , status=200 if result else 404
                    )

                return JsonResponse(error_message('Invalid action'), status=400)

            case 'PUT':  # Create a new registry
                if role == 'viewer':
                    return JsonResponse(error_message('Permission denied'), status=403)

                valid, err = validate_registry_spec(cr_data)
                if not valid:
                    return JsonResponse(err, status=400)

                cr = ContainerRegistry(crid=str(uuid.uuid4()), namespace=ns, name=cr_data['name'], slug=cr_data['slug'],
                                       username='osiris', password=cr_data['password'])

                cr.save()

                create_registry.delay(serialize_obj(cr))

                return JsonResponse(success_message('Create registry', cr.info()), status=201)

            case 'PATCH':
                if role == 'viewer':
                    return JsonResponse(error_message('Permission denied'), status=403)

                cr = ContainerRegistry.objects.filter(namespace=ns, crid=crid).first()
                if cr is None:
                    return JsonResponse(error_message('Registry not found'), status=404)

                valid, err = validate_registry_update_spec(cr_data)
                if not valid:
                    return JsonResponse(err, status=400)

                if name := cr_data.get('name'):
                    cr.name = name
                if password := cr_data.get('password'):
                    cr.password = password

                cr.save()

                patch_registry.delay(serialize_obj(cr))

                return JsonResponse(success_message('Update registry', cr.info()), status=200)

            case 'DELETE':
                if role == 'viewer':
                    return JsonResponse(error_message('Permission denied'), status=403)

                cr = ContainerRegistry.objects.filter(namespace=ns, crid=crid).first()
                if cr is None:
                    return JsonResponse(error_message('Registry not found'), status=404)

                delete_registry.delay(serialize_obj(cr))

                return JsonResponse(success_message('Delete registry', {'crid': crid}), status=200)

    except JSONDecodeError:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except ValidationError:
        return JsonResponse(error_message('Invalid crid/input data type'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)
