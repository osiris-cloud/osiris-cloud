import logging

from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.db import transaction
from json.decoder import JSONDecodeError

from .models import User, Limit
from ..infra.models import Namespace, NamespaceRoles

from core.utils import success_message, error_message, random_str
from ..users.utils import sanitize_nsid, validate_ns_create, validate_ns_update, validate_user_update, \
    delete_owner_resources
from .utils import get_default_ns, greater_than
from ..dashboard.utils import get_ns_usage

from .tasks import notify_new_owner, delete_namespace


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def namespace(request, nsid=None):
    """
    API for all namespaces or a specific namespace
    """
    ns = None
    if nsid == 'default':
        if not (nsid := request.session.get('default_nsid')):
            ns = get_default_ns(request.user)
            nsid = request.session['default_nsid'] = ns.nsid

    if (request.method in ['PATCH, DELETE']) and nsid is None:
        return JsonResponse(error_message('nsid is required'), status=400)

    if (request.user.role in ('guest', 'blocked')) and (request.method in ('PUT', 'PATCH', 'DELETE')):
        return JsonResponse(error_message('Permission denied'), status=403)

    ns_data = request.data

    try:
        if request.method == 'GET':
            brief_only = request.GET.get('brief') == 'true'

            if ns:
                result = ns.brief(request.user) if brief_only else ns.info(request.user)
                return JsonResponse(success_message('Get namespace', {'namespace': result}), status=200)

            if nsid:
                ns = Namespace.objects.get(nsid=nsid, locked=False)
                role = ns.get_role(request.user)
                if role is None:
                    return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

                result = ns.brief() if brief_only else ns.info()
                result['_role'] = role
            else:
                namespaces = Namespace.objects.filter(users=request.user, locked=False)
                result = [ns.brief(request.user) if brief_only else ns.info(request.user) for ns in namespaces]

            return JsonResponse(success_message('Get namespaces', {
                'namespace' if nsid else 'namespaces': result,
            }), status=200)

        elif request.method == 'PUT':
            valid, err = validate_ns_create(ns_data)
            if not valid:
                return JsonResponse(error_message(err), status=400)

            new_ns_name = ns_data['name']
            ns_nsid = (sanitize_nsid(new_ns_name) or request.user.username) + '-' + random_str()
            new_ns_default = ns_data.get('default', False)

            with transaction.atomic():
                # If the new namespace is set as default, update other namespaces owned by the user
                if new_ns_default:
                    Namespace.objects.filter(users=request.user, default=True).update(default=False)
                    request.session['default_nsid'] = nsid

                # List of usernames with their role to add to the namespace.
                new_ns_users = ns_data.get('users', [])
                ns = Namespace.objects.create(nsid=ns_nsid, name=new_ns_name, default=new_ns_default)
                NamespaceRoles.objects.create(namespace=ns, user=request.user, role='owner')  # Add creator as owner

                for ns_user in new_ns_users:  # Add users to namespace
                    try:
                        user_obj = User.objects.get(username=ns_user['username'])
                        if user_obj == request.user:
                            return JsonResponse(error_message('Owner cannot be assigned additional roles'), status=400)

                        NamespaceRoles.objects.create(namespace=ns, user=user_obj, role=ns_user['role'])

                    except User.DoesNotExist:
                        return JsonResponse(error_message(f'User {ns_user["username"]} not found'), status=400)

            return JsonResponse(success_message('Create namespace', {'namespace': ns.info()}), status=201)

        elif request.method == 'PATCH':
            valid, err = validate_ns_update(ns_data)
            if not valid:
                return JsonResponse(error_message(err), status=400)

            if not ns:
                ns = Namespace.objects.get(nsid=nsid, locked=False)

            new_ns_default = ns_data.get('default', False)
            new_ns_owner_uname = ns_data.get('owner', {}).get('username')
            new_ns_users = ns_data.get('users', [])
            request_user_role = ns.get_role(request.user)

            if request_user_role not in ('owner', 'manager'):
                return JsonResponse(error_message('Permission denied'), status=403)

            # request user is owner POV
            if request_user_role == 'owner':
                # transfer ownership criteria -> current owner needs to have another namespace set as default
                if ns.default and (new_ns_owner_uname != request.user.username):
                    return JsonResponse(
                        error_message('You must set another namespace as default before transferring ownership'),
                        status=400
                    )

            # request user is manager POV
            elif request_user_role == 'manager':
                # set default criteria -> only owner can set namespace as default
                if new_ns_default:
                    return JsonResponse(error_message('Only the owner can set namespace as default'),
                                        status=403)
                if new_ns_owner_uname != ns.owner.username:
                    return JsonResponse(error_message('Permission denied: You need to be the owner'),
                                        status=403)

            if new_ns_name := ns_data.get('name'):
                ns.name = new_ns_name.strip()

            if new_ns_default:
                # If the context namespace is set to default, unset 'default' on prev default namespace
                Namespace.objects.filter(users=request.user, default=True).update(default=False)
                ns.default = True
                request.session['default_nsid'] = nsid

            # Update namespace owner
            if new_ns_owner_uname != ns.owner.username:
                new_owner = User.objects.filter(username=new_ns_owner_uname).first()
                if not new_owner:
                    return JsonResponse(error_message('New owner not found'), status=400)

                # Compare ns usage with new owner's (limit - usage) to ensure new owner has enough resources

                if greater_than(get_ns_usage(ns), new_owner.limit - new_owner.usage):
                    return JsonResponse(error_message("Cannot transfer namespace due to new owner's resource "
                                                      "quota limitations"),
                                        status=400)

                # Remove the current owner role
                NamespaceRoles.objects.filter(namespace=ns, role='owner').delete()

                # Check if the new owner is already part of the namespace, if so, update the user's role
                if existing_role := NamespaceRoles.objects.filter(namespace=ns, user=new_owner).first():
                    existing_role.role = 'owner'
                    existing_role.save()
                else:
                    NamespaceRoles.objects.create(namespace=ns, user=new_owner, role='owner')

                notify_new_owner.delay(new_owner.email, ns.nsid, ns.name, request.user.username)

            if new_ns_users is not None:  # Remove all current manager and viewer roles
                NamespaceRoles.objects.filter(namespace=ns, role__in=['manager', 'viewer']).delete()
                for each_user in new_ns_users:
                    try:
                        user_obj = User.objects.get(username=each_user['username'])

                    except User.DoesNotExist:
                        return JsonResponse(error_message(f'User {each_user["username"]} not found'), status=400)

                    # Ensure the owner cannot assign themselves additional roles
                    if user_obj == ns.owner:
                        return JsonResponse(error_message('Owner cannot be assigned additional roles'), status=400)

                    NamespaceRoles.objects.create(namespace=ns, user=user_obj, role=each_user['role'])

            ns.save()

            return JsonResponse(success_message('Update namespace', {'namespace': ns.info()}))

        elif request.method == 'DELETE':
            ns = Namespace.objects.get(nsid=nsid)

            if ns.owner != request.user:
                return JsonResponse(
                    error_message('Permission denied: Only the owner can delete the namespace'), status=403)

            # If the namespace is set as default, user has to set another namespace as default before deleting
            if ns.default:
                return JsonResponse(error_message('Cannot delete namespace when it is set as default'), status=400)

            # Set namespace to locked
            ns.locked = True
            ns.save()

            delete_namespace.delay(ns.nsid)

            return JsonResponse(success_message('Delete namespace', {'nsid': nsid}), status=200)

    except User.DoesNotExist:
        return JsonResponse(error_message('Invalid user'), status=404)

    except Namespace.DoesNotExist:
        return JsonResponse(error_message('Namespace not found'), status=404)

    except JSONDecodeError as e:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)


@api_view(['GET', 'PATCH', 'DELETE'])
def user_api(request, username=None):
    """
    API for all users or a specific user
    """
    if (request.method in ['PATCH, DELETE']) and username is None:
        return JsonResponse(error_message('username is required'), status=400)

    cluster_admin = request.user.role in ('admin', 'super_admin')

    if username == '_self':
        username = request.user.username

    try:
        match request.method:
            case 'GET':
                brief_only = request.GET.get('brief') == 'true'

                if username:
                    if (request.user.username != username) and not cluster_admin:
                        return JsonResponse(error_message('Permission denied'), status=403)

                    user = User.objects.get(username=username)
                    result = user.brief() if brief_only else user.detailed_info()

                else:
                    if not cluster_admin:
                        return JsonResponse(error_message('Permission denied'), status=403)

                    users = User.objects.all()
                    result = [user.brief() if brief_only else user.detailed_info() for user in users]

                return JsonResponse(success_message('Get users', {
                    'user' if username else 'users': result,
                }), status=200)

            case 'PATCH':
                user_obj = User.objects.get(username=username)

                # Non-admins can only update their own info
                if request.user != user_obj and not cluster_admin:
                    return JsonResponse(error_message('Permission denied'), status=403)

                user_data = request.data

                # Non-admins cannot update cluster_role or resource_limit
                if not cluster_admin:
                    if 'cluster_role' in user_data or 'resource_limit' in user_data:
                        return JsonResponse(error_message('Permission denied'), status=403)

                valid, err = validate_user_update(user_data)
                if not valid:
                    return JsonResponse(error_message(err), status=400)

                try:
                    with transaction.atomic():
                        if 'first_name' in user_data:
                            user_obj.first_name = user_data['first_name']
                        if 'last_name' in user_data:
                            user_obj.last_name = user_data['last_name']
                        if 'email' in user_data:
                            user_obj.email = user_data['email']
                        if 'avatar' in user_data:
                            user_obj.avatar = user_data['avatar']
                        if 'cluster_role' in user_data:
                            if request.user.role == 'admin' and user_data['cluster_role'] == 'super_admin':
                                return JsonResponse(error_message('Admin cannot assign super_admin role'))
                            if request.user.role in ('admin', 'super_admin'):
                                user_obj.role = user_data['cluster_role']
                        if 'resource_limit' in user_data and cluster_admin:
                            user_limit_obj = Limit.objects.get(user=user_obj)
                            for key, value in user_data['resource_limit'].items():
                                setattr(user_limit_obj, key, value)

                            user_limit_obj.save()

                        user_obj.save()

                except Exception as e:
                    logging.error(str(e))
                    return JsonResponse(error_message('Failed to update user'), status=500)

                return JsonResponse(success_message('Update user', user_obj.info()))

            case 'DELETE':
                if not username:
                    return JsonResponse(error_message('No username provided'), status=400)

                if not cluster_admin:
                    return JsonResponse(error_message('Permission denied'), status=403)

                user_obj = User.objects.get(username=username)

                # Nuke all resources of namespaces owned by the user
                if delete_owner_resources(user_obj):
                    # Update DB tables
                    try:
                        with transaction.atomic():
                            # Get namespace ids user owns from NamespaceRoles
                            namespace_ids = NamespaceRoles.objects.filter(user=user_obj, role='owner').values_list(
                                'namespace_id', flat=True)

                            for namespace_id in namespace_ids:
                                Namespace.objects.filter(id=namespace_id).delete()
                            user_obj.delete()

                            return JsonResponse(success_message('Delete user', {'username': username}), status=200)
                    except Exception as e:
                        logging.error(str(e))
                        return JsonResponse(error_message('Failed to delete user'), status=500)
                else:
                    return JsonResponse(error_message('Failed to delete user resources'), status=500)

    except User.DoesNotExist:
        return JsonResponse(error_message('User not found'), status=404)

    except JSONDecodeError as e:
        return JsonResponse('Invalid JSON data', status=400)

    except Exception as e:
        logging.error(str(e))
        return JsonResponse('Internal server error', status=500)
