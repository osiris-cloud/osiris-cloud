import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from django.db.models import Sum
from json import loads as json_loads

from core.utils import success_message, error_message, random_str
from .models import User, Limit, PendingTransfer
from ..k8s.models import PVC, Namespace, NamespaceRoles
from ..vm.models import VM
from ..oauth.models import NYUUser
from ..users.utils import delete_namespace_resources, sanitize_nsid, validate_ns_creation, validate_ns_update, validate_user_update, delete_owner_resources, notify_new_owner


def get_user_default_ns(user: User) -> Namespace:
    return NamespaceRoles.objects.filter(user=user, role='owner', namespace__default=True).first().namespace

def initiate_ns_owner_transfer(requester, ns, ns_owner, ns_users):
    if ns_users:
        for user in ns_users:
            if user['username'] == ns_owner['username']:
                raise ValueError('New owner cannot be assigned additional roles')
            
    new_owner_obj = User.objects.filter(username=ns_owner.get('username')).first()

    if not new_owner_obj:
        raise ValueError('New owner\'s username not found')
    
    if new_owner_obj == ns.owner:
        raise ValueError('New owner is already the namespace owner')
    
    
    try:
        with transaction.atomic():
            # remove PendingTransfer entries for matching namespace, new owner and requester
            PendingTransfer.objects.filter(
                namespace=ns,
                new_owner=new_owner_obj,
                initiated_by=requester
            ).delete()

            # Generate unique token
            token = random_str(64)

            PendingTransfer.objects.create(
                token=token,
                namespace=ns,
                new_owner=new_owner_obj,
                initiated_by=requester,
                ns_users=ns_users
            )

            notify_new_owner(new_owner_obj.email, ns.nsid, ns.name, requester.username, token)

    except Exception as e:
        logging.error(str(e))
        return JsonResponse(error_message('Failed to initiate namespace owner transfer'))
    
    return JsonResponse(success_message('Initiate namespace owner transfer'))


@csrf_exempt
@api_view(['GET', 'POST'])
def accept_ns_owner_transfer(request, token):
    if not token or not isinstance(token, str):
        return JsonResponse(error_message('Invalid or missing token'))
    
    pending_transfer = PendingTransfer.objects.filter(token=token).first()

    if not pending_transfer:
        return JsonResponse(error_message('Invalid or expired token'))
    
    # Check if user is the supposed new owner
    if pending_transfer.new_owner != request.user:
        return JsonResponse(error_message('Invalid or expired token'))
    
    ns = pending_transfer.namespace
    
    try:
        with transaction.atomic():
            # Compare NS allocated resources with new owner's limit
            total_resources = VM.objects.filter(namespace=ns).aggregate(
                cpu=Sum('cpu'),
                ram=Sum('memory')
            )

            total_disk_usage = PVC.objects.filter(namespace=ns).aggregate(
                total_disk=Sum('size')
            )

            user_info = request.user.detailed_info()

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
                raise ValueError('Total CPU usage exceeds the user\'s limit')
            if user_ram_limit is not None and total_ram_used > user_ram_limit:
                raise ValueError('Total RAM usage exceeds the user\'s limit')
            if user_disk_limit is not None and total_disk_used > user_disk_limit:
                raise ValueError('Total disk usage exceeds the user\'s limit')
            

            # Remove the current owner role
            NamespaceRoles.objects.filter(namespace=ns, role='owner').delete()
            
            # Check if the new owner is already part of the namespace, if so, delete the user's role
            existing_role = NamespaceRoles.objects.filter(namespace=ns, user=request.user).first()
            if existing_role:
                existing_role.role = 'owner'
                existing_role.save()
            else:
                NamespaceRoles.objects.create(
                    namespace=ns,
                    user=request.user,
                    role='owner'
                )
            
            ns.default = False
            ns.save()

            ns_users = pending_transfer.ns_users
            if ns_users:
                # Remove all current manager and viewer roles
                NamespaceRoles.objects.filter(namespace=ns, role__in=['manager', 'viewer']).delete()
                
                for user in ns_users:
                    user_obj = User.objects.filter(username=user['username']).first()
                    if not user_obj:
                        raise ValueError(f'User {user["username"]} not found')

                    role = user['role']

                    NamespaceRoles.objects.create(
                        namespace=ns,
                        user=user_obj,
                        role=role
                    )

            # Delete the pending transfer record
            pending_transfer.delete()

            # Delete all other pending transfers with the same namespace
            PendingTransfer.objects.filter(namespace=ns).delete()

    except ValueError as e:
        return JsonResponse(error_message(str(e)))
    except Exception as e:
        logging.error(str(e))
        return JsonResponse(error_message('Failed to accept namespace ownership transfer'))

    return JsonResponse(success_message('Accept namespace ownership transfer'))

@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
def namespace(request, nsid=None):
    """
    Get properties of all namespaces the user is part of
    """
    ns_filter = {}
    if nsid:
        if nsid == 'default':
            if request.session.get('namespace') is None:
                request.session['namespace'] = get_user_default_ns(request.user).nsid
            ns_filter['nsid'] = request.session.get('namespace')
        else:
            ns_filter['nsid'] = nsid

    try:
        match request.method:
            case 'GET':
                # Get all namespaces the user is part of
                namespaces = request.user.namespaces.filter(**ns_filter)

                if not namespaces.exists():
                    return JsonResponse(error_message('No namespace found'))

                result = []

                for ns in namespaces:
                    ns_info = ns.info()
                    ns_info['users'] = ns.get_users_info()
                    result.append(ns_info)

                if nsid:
                    return JsonResponse(success_message('Get namespace', result[0]))

                return JsonResponse(success_message('Get namespaces', {
                    'namespaces': result,
                }))

            case 'POST':
                if 'data' not in request.POST:
                    return JsonResponse(error_message('No data provided'))
                
                ns_data = json_loads(request.POST['data'])
                
                valid, resp = validate_ns_creation(ns_data)

                if not valid:
                    return JsonResponse(resp)

                ns_name = ns_data.get('name')
                ns_nsid = sanitize_nsid(ns_name)

                if ns_nsid:
                    ns_nsid = ns_nsid + '-' + random_str(4)
                else:
                    ns_nsid = random_str(4) + '-' + random_str(4)

                ns_default = ns_data.get('default', False)
                
                try:
                    with transaction.atomic():
                        # If the new namespace is set as default, update other namespaces owned by the user
                        if ns_default:
                            Namespace.objects.filter(users=request.user, default=True).update(default=False)

                        # List of usernames with their role to add to the namespace.
                        ns_users = ns_data.get('users', [])

                        # Create namespace
                        ns = Namespace.objects.create(
                            nsid=ns_nsid,
                            name=ns_name,
                            default=ns_default
                        )
                            
                        # Add creator as owner
                        NamespaceRoles.objects.create(
                            namespace=ns,
                            user=request.user,
                            role='owner'
                        )
                        
                        # Add users to namespace.
                        for user in ns_users:
                            user_obj = User.objects.filter(username=user['username']).first()
                            
                            if not user_obj:
                                raise ValueError(f'User {user["username"]} not found')
                                                        
                            if user_obj == request.user:
                                raise ValueError('Owner cannot be assigned additional roles')
                                                        
                            role = user['role']
                            
                            NamespaceRoles.objects.create(
                                namespace=ns,
                                user=user_obj,
                                role=role
                            )

                except ValueError as e:
                    return JsonResponse(error_message(str(e)))
                except Exception as e:
                    logging.error(str(e))
                    return JsonResponse(error_message('Failed to create namespace'))

                ns_info = ns.info()
                ns_info['users'] = ns.get_users_info()
                return JsonResponse(success_message('Create namespace', ns_info))
            
            case 'DELETE':
                if nsid == 'default':
                    ns_nsid = request.session.get('namespace')
                else:
                    ns_nsid = nsid

                if not ns_nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                ns = Namespace.objects.filter(nsid=ns_nsid).first()

                if not ns or ns.owner != request.user:
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))
                
                # If the namespace is set as default, user has to set another namespace as default before deleting
                if ns.default:
                    return JsonResponse(error_message('Cannot delete default namespace'))

                if delete_namespace_resources(ns):
                    try:
                        ns.delete()
                    except Exception as e:
                        logging.error(str(e))
                        return JsonResponse(error_message('Failed to delete namespace'))
                else:
                    return JsonResponse(error_message('Failed to delete namespace resources'))

                return JsonResponse(success_message('Delete namespace', {'nsid': ns_nsid}))

            case 'PATCH':
                if nsid == 'default':
                    ns_nsid = request.session.get('namespace')
                else:
                    ns_nsid = nsid

                if not ns_nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                if 'data' not in request.POST:
                    return JsonResponse(error_message('No data provided'))
                
                ns_data = json_loads(request.POST['data'])
                
                valid, resp = validate_ns_update(ns_data, ns_nsid)

                if not valid:
                    return JsonResponse(resp)
                
                ns_name = ns_data.get('name')
                ns_default = ns_data.get('default', False)
                ns_owner = ns_data.get('owner')
                ns_users = ns_data.get('users', [])

                if not ns_nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                ns = Namespace.objects.filter(nsid=ns_nsid).first()

                if not ns:
                    return JsonResponse(error_message('No namespace found or user does not have permission to update this namespace'))
                
                if ns.get_role(request.user) not in ['owner', 'manager']:
                    return JsonResponse(error_message('No namespace found or user does not have permission to update this namespace'))

                if ns_default and ns_owner:
                    return JsonResponse(error_message('Cannot specify owner and set namespace as default at the same time'))
                
                # Check if the namespace is the requester's default namespace
                if ns.owner == request.user and ns.default and ns_owner:
                    return JsonResponse(error_message('You must set another namespace as your default before transferring ownership'))
                
                try:
                    with transaction.atomic():
                        if ns_default and not ns_owner:
                            if ns.owner != request.user:
                                raise ValueError('Only the owner can set the namespace as default')
                            
                            # If the namespace is set as default, update other namespaces owned by the user
                            Namespace.objects.filter(users=request.user, default=True).update(default=False)
                            ns.default = ns_default
                            request.session['namespace'] = ns_nsid

                        # Update namespace owner
                        if ns_owner:
                            return(initiate_ns_owner_transfer(request.user, ns, ns_owner, ns_users))

                        if not ns_owner and ns_users:
                            # Remove all current manager and viewer roles
                            NamespaceRoles.objects.filter(namespace=ns, role__in=['manager', 'viewer']).delete()
                            for user in ns_users:
                                user_obj = User.objects.filter(username=user['username']).first()
                                if not user_obj:
                                    raise ValueError(f'User {user["username"]} not found')
                                
                                # Ensure the owner cannot assign themselves additional roles
                                if user_obj == ns.owner:
                                    raise ValueError('Owner cannot be assigned additional roles')

                                role = user['role']
                                
                                NamespaceRoles.objects.create(
                                    namespace=ns,
                                    user=user_obj,
                                    role=role
                                )

                        if ns_name:
                            ns.name = ns_name

                        # push changes to the database
                        ns.save()
                
                except ValueError as e:
                    return JsonResponse(error_message(str(e)))
                except Exception as e:
                    logging.error(str(e))
                    return JsonResponse(error_message('Failed to update namespace'))

                ns_info = ns.info()
                ns_info['users'] = ns.get_users_info()
                return JsonResponse(success_message('Update namespace', ns_info))

    except Exception as e:
        logging.error(str(e))
        return JsonResponse('Internal server error', status=500)

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
                
                if 'data' not in request.POST:
                    return JsonResponse(error_message('No data provided'))
                
                user_data = json_loads(request.POST['data'])
                
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
                            namespace_ids = NamespaceRoles.objects.filter(user=user_obj, role='owner').values_list('namespace_id', flat=True)

                            for namespace_id in namespace_ids:
                                Namespace.objects.filter(id=namespace_id).delete()
                            user_obj.delete()

                            return JsonResponse(success_message('Delete user', {'username': username}))
                    except Exception as e:
                        logging.error(str(e))
                        return JsonResponse(error_message('Failed to delete user'))
                else:
                    return JsonResponse(error_message('Failed to delete user resources'))

    except Exception as e:
        logging.error(str(e))
        return JsonResponse('Internal server error', status=500)
    