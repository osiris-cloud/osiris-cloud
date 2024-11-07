import logging
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.db import transaction
from json.decoder import JSONDecodeError

from core.utils import success_message, error_message, random_str
from .models import User, Limit
from ..k8s.models import Namespace, NamespaceRoles
from ..users.utils import (schedule_ns_deletion, sanitize_nsid, validate_ns_creation, validate_ns_update,
                           validate_user_update, delete_owner_resources, notify_new_owner)

from .utils import get_default_ns, greater_than
from ..dashboard.utils import get_ns_usage


@api_view(['GET', 'PUT', 'PATCH', 'DELETE'])
def namespace(request, nsid=None):
    """
    API for all namespaces or a specific namespace
    """
    if nsid == 'default':
        if not (nsid := request.session.get('default_ns')):
            nsid = request.session['default_ns'] = get_default_ns(request.user).nsid

    if (request.method in ['PATCH, DELETE']) and nsid is None:
        return JsonResponse(error_message('nsid is required'), status=400)

    if (request.user.role in ('guest', 'blocked')) and (request.method in ('PUT', 'PATCH', 'DELETE')):
        return JsonResponse(error_message('Permission denied'), status=403)

    ns_data = request.data

    try:
        match request.method:
            case 'GET':
                # Get all namespaces the user is part of
                ns_filter = {'nsid': nsid, 'locked': False} if nsid else {'locked': False}
                namespaces = request.user.namespaces.filter(**ns_filter)

                if not namespaces.exists():
                    return JsonResponse(error_message('Namespace not found or no permission to access'), status=404)

                result = []

                for ns in namespaces:
                    ns_info = ns.info()
                    ns_info['users'] = ns.get_users_info()
                    result.append(ns_info)

                if nsid:
                    return JsonResponse(success_message('Get namespace', {'namespace': result[0]}), status=200)

                return JsonResponse(success_message('Get namespaces', {
                    'namespaces': result,
                }), status=200)

            case 'PUT':
                valid, err = validate_ns_creation(ns_data)
                if not valid:
                    return JsonResponse(err)

                new_ns_name = ns_data.get('name')
                if not new_ns_name:
                    return JsonResponse(error_message('Namespace name is required'), status=400)

                ns_nsid = (sanitize_nsid(new_ns_name) or request.user.username) + '-' + random_str()
                new_ns_default = ns_data.get('default', False)

                with transaction.atomic():
                    # If the new namespace is set as default, update other namespaces owned by the user
                    if new_ns_default:
                        Namespace.objects.filter(users=request.user, default=True).update(default=False)
                        request.session['default_nsid'] = nsid

                    # List of usernames with their role to add to the namespace.
                    new_ns_users = ns_data.get('users', [])
                    ns = Namespace.objects.create(nsid=ns_nsid, name=new_ns_name,
                                                  default=new_ns_default)  # Create namespace
                    NamespaceRoles.objects.create(namespace=ns, user=request.user, role='owner')  # Add creator as owner
                    for user in new_ns_users:  # Add users to namespace
                        user_obj = User.objects.filter(username=user['username']).first()
                        if not user_obj:
                            return JsonResponse(error_message(f'User {user["username"]} not found'), status=400)
                        if user_obj == request.user:
                            return JsonResponse(error_message('Owner cannot be assigned additional roles'), status=400)
                        NamespaceRoles.objects.create(namespace=ns, user=user_obj, role=user['role'])

                ns_info = ns.info()
                ns_info['users'] = ns.get_users_info()
                return JsonResponse(success_message('Create namespace', ns_info), status=201)

            case 'PATCH':
                valid, err = validate_ns_update(ns_data, nsid)
                if not valid:
                    return JsonResponse(err, status=400)

                new_ns_name = ns_data.get('name')
                new_ns_default = ns_data.get('default', False)
                new_ns_owner_uname = ns_data.get('owner', {}).get('username')
                new_ns_users = ns_data.get('users', [])

                ns = Namespace.objects.filter(nsid=nsid, locked=False).first()

                if not ns:
                    return JsonResponse(error_message(f'Namespace {nsid} not found'), status=404)

                request_user_role = ns.get_role(request.user)

                if request_user_role not in ['owner', 'manager']:
                    return JsonResponse(error_message('Permission denied: You need to be either owner or manager'),
                                        status=403)

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

                if new_ns_name:
                    ns.name = new_ns_name

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
                        return JsonResponse(error_message('New owner does not have enough resources'), status=400)

                    # Remove the current owner role
                    NamespaceRoles.objects.filter(namespace=ns, role='owner').delete()

                    # Check if the new owner is already part of the namespace, if so, update the user's role
                    if existing_role := NamespaceRoles.objects.filter(namespace=ns, user=new_owner).first():
                        existing_role.role = 'owner'
                        existing_role.save()
                    else:
                        NamespaceRoles.objects.create(namespace=ns, user=new_owner, role='owner')

                    notify_new_owner(new_owner.email, ns.nsid, ns.name, request.user.username)

                if new_ns_users is not None:  # Remove all current manager and viewer roles
                    NamespaceRoles.objects.filter(namespace=ns, role__in=['manager', 'viewer']).delete()
                    for each_user in new_ns_users:
                        user_obj = User.objects.filter(username=each_user['username']).first()
                        if not user_obj:
                            return JsonResponse(error_message(f'User {each_user["username"]} not found'), status=400)

                        # Ensure the owner cannot assign themselves additional roles
                        if user_obj == ns.owner:
                            return JsonResponse(error_message('Owner cannot be assigned additional roles'), status=400)

                        NamespaceRoles.objects.create(namespace=ns, user=user_obj, role=each_user['role'])

                ns.save()

                ns_info = ns.info()
                ns_info['users'] = ns.get_users_info()
                return JsonResponse(success_message('Update namespace', {'namespace': ns_info}))

            case 'DELETE':
                ns = Namespace.objects.filter(nsid=nsid, locked=False).first()

                if not ns:
                    return JsonResponse(error_message(f'Namespace {nsid} not found'), status=404)

                if ns.default:
                    return JsonResponse(error_message('Cannot delete default namespace'), status=400)

                if ns.owner != request.user:
                    return JsonResponse(
                        error_message('Permission denied: Only the owner can delete the namespace'), status=403)

                # If the namespace is set as default, user has to set another namespace as default before deleting
                if ns.default:
                    return JsonResponse(error_message('Cannot delete default namespace'), status=400)

                # Set namespace to locked
                ns.locked = True
                ns.save()

                schedule_ns_deletion(ns)

                return JsonResponse(success_message('Delete namespace', {'nsid': nsid}), status=200)

    except JSONDecodeError as e:
        return JsonResponse(error_message('Invalid JSON data'), status=400)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message('Internal server error'), status=500)


@api_view(['GET', 'PATCH', 'DELETE'])
def user(request, username=None):
    """
    API for all users or a specific user
    """
    if (request.method in ['PATCH, DELETE']) and username is None:
        return JsonResponse(error_message('username is required'), status=400)

    cluster_admin = request.user.role in ['admin', 'super_admin']

    if username == '_self':
        username = request.user.username

    try:
        match request.method:
            case 'GET':
                user_filter = {'username': username} if username else {}
                users = User.objects.filter(**user_filter)
                user_infos = [u.detailed_info() for u in users]

                if username:
                    if (request.user.username != username) and not cluster_admin:
                        return JsonResponse(error_message('Permission denied'))

                    if not user_infos:
                        return JsonResponse(error_message('User not found'), status=404)

                    return JsonResponse(success_message('Get user', {'user': user_infos[0]}), status=200)

                if not cluster_admin:
                    return JsonResponse(error_message('Permission denied'))

                return JsonResponse(success_message('Get users', {'users': user_infos}), status=200)

            case 'PATCH':
                user_obj = User.objects.filter(username=username).first()
                if not user_obj:
                    return JsonResponse(error_message('User not found'), status=404)

                # Non-admins can only update their own info
                if request.user != user_obj and not cluster_admin:
                    return JsonResponse(error_message('Permission denied'))

                if request.data.get('data') is not None:
                    user_data = request.data.get('data')
                else:
                    user_data = request.data

                # Non-admins cannot update cluster_role or resource_limit
                if not cluster_admin:
                    if 'cluster_role' in user_data or 'resource_limit' in user_data:
                        return JsonResponse(error_message('Permission denied'))

                valid, resp = validate_user_update(user_data)

                if not valid:
                    return JsonResponse(resp)

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
                            if request.user.role in ['admin', 'super_admin']:
                                user_obj.role = user_data['cluster_role']
                        if 'resource_limit' in user_data and cluster_admin:
                            user_limit_obj = Limit.objects.filter(user=user_obj).first()
                            for key, value in user_data['resource_limit'].items():
                                setattr(user_limit_obj, key, value)

                            user_limit_obj.save()

                        user_obj.save()

                except Exception as e:
                    logging.error(str(e))
                    return JsonResponse(error_message('Failed to update user'))

                return JsonResponse(success_message('Update user', user_obj.detailed_info()))

            case 'DELETE':
                if not username:
                    return JsonResponse(error_message('No username provided'))

                if request.user.role not in ['admin', 'super_admin']:
                    return JsonResponse(error_message('Permission denied'))

                user_obj = User.objects.filter(username=username).first()
                if not user_obj:
                    return JsonResponse(error_message('User not found'))

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

                            return JsonResponse(success_message('Delete user', {'username': username}))
                    except Exception as e:
                        logging.error(str(e))
                        return JsonResponse(error_message('Failed to delete user'))
                else:
                    return JsonResponse(error_message('Failed to delete user resources'))

    except JSONDecodeError as e:
        logging.error(e)
        return JsonResponse('Invalid JSON data', status=400)

    except Exception as e:
        logging.error(str(e))
        return JsonResponse('Internal server error', status=500)
