import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import Sum
from json import loads as json_loads
from json.decoder import JSONDecodeError

from core.utils import success_message, error_message, random_str
from .models import User, Limit
from ..k8s.models import PVC, Namespace, NamespaceRoles
from ..vm.models import VM
from ..oauth.models import NYUUser
from ..users.utils import schedule_ns_deletion, sanitize_nsid, validate_ns_creation, validate_ns_update, \
    validate_user_update, delete_owner_resources, notify_new_owner


def get_user_default_ns(user: User) -> Namespace:
    return NamespaceRoles.objects.filter(user=user, role='owner', namespace__default=True).first().namespace


@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
def namespace(request, nsid=None):
    """
    Get properties of all namespaces the user is part of
    """
    if nsid == 'default':
        if not (nsid := request.session.get('default_ns')):
            nsid = request.session['default_ns'] = get_user_default_ns(request.user).nsid

    if (request.method in ['PATCH, DELETE']) and nsid is None:
        return JsonResponse(error_message('Namespace id is required'), status=400)

    try:
        ns_data = request.data
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
                    return JsonResponse(success_message('Get namespace', result[0]), status=200)

                return JsonResponse(success_message('Get namespaces', {
                    'namespaces': result,
                }), status=200)

            case 'POST':
                valid, err = validate_ns_creation(ns_data)
                if not valid:
                    return JsonResponse(err)

                new_ns_name = ns_data.get('name')
                if not new_ns_name:
                    return JsonResponse(error_message('Namespace name is required'), status=400)

                ns_nsid = (sanitize_nsid(new_ns_name) or request.user.username) + '-' + random_str(4)
                new_ns_default = ns_data.get('default', False)

                with transaction.atomic():
                    # If the new namespace is set as default, update other namespaces owned by the user
                    if new_ns_default:
                        Namespace.objects.filter(users=request.user, default=True).update(default=False)
                        request.session['default_ns'] = nsid

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
                    request.session['default_ns'] = nsid

                # Update namespace owner
                if new_ns_owner_uname != ns.owner.username:
                    new_owner_obj = User.objects.filter(username=new_ns_owner_uname).first()
                    if not new_owner_obj:
                        return JsonResponse(error_message('New owner\'s username not found'),
                                            status=400)

                    if new_owner_obj == ns.owner:
                        return JsonResponse(error_message('New owner is already the namespace owner'),
                                            status=400)
                    
                    # Compare NS allocated resources with new owner's limit
                    total_resources = VM.objects.filter(namespace=ns).aggregate(
                        cpu=Sum('cpu'),
                        ram=Sum('memory')
                    )

                    total_disk_usage = PVC.objects.filter(namespace=ns).aggregate(
                        total_disk=Sum('size')
                    )

                    user_info = new_owner_obj.detailed_info()

                    user_cpu_used = user_info['resource_used']['cpu']
                    user_ram_used = user_info['resource_used']['memory']
                    user_disk_used = user_info['resource_used']['disk']
                    user_cpu_limit = user_info['resource_limit']['cpu']
                    user_ram_limit = user_info['resource_limit']['memory']
                    user_disk_limit = user_info['resource_limit']['disk']

                    total_cpu_used = user_cpu_used + (total_resources['cpu'] or 0)
                    total_ram_used = user_ram_used + (total_resources['ram'] or 0)
                    total_disk_used = user_disk_used + (total_disk_usage['total_disk'] or 0)

                    # null limit = unlimited
                    if user_cpu_limit is not None and total_cpu_used > user_cpu_limit:
                        return JsonResponse(error_message('Total CPU usage exceeds new owner\'s limit'), status=400)
                    if user_ram_limit is not None and total_ram_used > user_ram_limit:
                        raise JsonResponse(error_message('Total RAM usage exceeds new owner\'s limit'), status=400)
                    if user_disk_limit is not None and total_disk_used > user_disk_limit:
                        raise JsonResponse(error_message('Total disk usage exceeds new owner\'s limit'), status=400)
                    
                    # Remove the current owner role
                    NamespaceRoles.objects.filter(namespace=ns, role='owner').delete()

                    # Check if the new owner is already part of the namespace, if so, update the user's role
                    existing_role = NamespaceRoles.objects.filter(namespace=ns, user=new_owner_obj).first()
                    if existing_role:
                        existing_role.role = 'owner'
                        existing_role.save()
                    else:
                        NamespaceRoles.objects.create(
                            namespace=ns,
                            user=new_owner_obj,
                            role='owner'
                        )
                    
                    notify_new_owner(new_owner_obj.email, ns.nsid, ns.name, request.user.username)

                if new_ns_users is not None:
                    # Remove all current manager and viewer roles
                    NamespaceRoles.objects.filter(namespace=ns, role__in=['manager', 'viewer']).delete()
                    for user in new_ns_users:
                        user_obj = User.objects.filter(username=user['username']).first()
                        if not user_obj:
                            return JsonResponse(error_message(f'User {user["username"]} not found'), status=400)

                        # Ensure the owner cannot assign themselves additional roles
                        if user_obj == ns.owner:
                            return JsonResponse(error_message('Owner cannot be assigned additional roles'),
                                                status=400)

                        NamespaceRoles.objects.create(
                            namespace=ns,
                            user=user_obj,
                            role=user['role']
                        )

                ns.save()

                ns_info = ns.info()
                ns_info['users'] = ns.get_users_info()
                return JsonResponse(success_message('Update namespace', ns_info))

            case 'DELETE':
                ns = Namespace.objects.filter(nsid=nsid).first()

                if not ns:
                    return JsonResponse(error_message(f'Namespace {nsid} not found'), status=404)

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
    try:
        match request.method:
            case 'GET':
                if username:
                    user_obj = User.objects.filter(username=username).first()
                    if not user_obj:
                        return JsonResponse(error_message('User not found'))

                    # Check if requester is the user themselves or a admin or super_admin
                    if request.user != user_obj and request.user.role not in ['admin', 'super_admin']:
                        return JsonResponse(error_message('Permission denied'))

                    return JsonResponse(success_message('Get user', user_obj.detailed_info()))
                else:  # no username provided
                    if request.user.role in ['admin', 'super_admin']:
                        # Admin or super_admin: return all users' detailed info
                        users_info = [user.detailed_info() for user in User.objects.all()]
                        return JsonResponse(success_message('Get users', {'users': users_info}))
                    else:
                        # Normal user: return their own detailed info
                        return JsonResponse(success_message('Get user', request.user.detailed_info()))

            case 'PATCH':
                if not username:
                    return JsonResponse(error_message('No username provided'))

                user_obj = User.objects.filter(username=username).first()
                if not user_obj:
                    return JsonResponse(error_message('User not found'))

                # Non-admins can only update their own info
                if request.user != user_obj and request.user.role not in ['admin', 'super_admin']:
                    return JsonResponse(error_message('Permission denied'))

                if request.data.get('data') is not None:
                    user_data = request.data.get('data')
                else:
                    user_data = request.data

                # Non-admins cannot update cluster_role or resource_limit
                if request.user.role not in ['admin', 'super_admin']:
                    if 'cluster_role' in user_data or 'resource_limit' in user_data:
                        return JsonResponse(error_message('Permission denied'))

                valid, resp = validate_user_update(user_data)

                if not valid:
                    return JsonResponse(resp)

                try:
                    with transaction.atomic():
                        # Update user fields
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
                        if 'resource_limit' in user_data and request.user.role in ['admin', 'super_admin']:
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
