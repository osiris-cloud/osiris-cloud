import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from django.db import transaction, IntegrityError
from json import loads as json_loads

from core.utils import success_message, error_message, random_str
from .models import User
from ..k8s.models import Namespace, NamespaceRoles
from ..users.utils import sanitize_nsid, validate_ns_creation, validate_ns_update


def get_user_default_ns(user: User) -> Namespace:
    return NamespaceRoles.objects.filter(user=user, role='owner', namespace__default=True).first().namespace


@csrf_exempt
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
                if not request.body:
                    return JsonResponse(error_message('No data provided'))
                
                ns_data = json_loads(request.body)
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

                except (IntegrityError, ValueError) as e:
                    return JsonResponse(error_message(str(e)))

                ns_info = ns.info()
                ns_info['users'] = ns.get_users_info()
                return JsonResponse(success_message('Create namespace', ns_info))
            
            case 'DELETE':
                ns_nsid = nsid

                if not ns_nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                ns = Namespace.objects.filter(nsid=ns_nsid).first()

                if not ns or ns.owner != request.user:
                    return JsonResponse(error_message('Namespace not found or user does not have permission to delete this namespace'))
                
                ns.delete()

                return JsonResponse(success_message('Delete namespace', {'nsid': ns_nsid}))

            case 'PATCH':
                ns_nsid = nsid
            
                if not ns_nsid:
                    return JsonResponse(error_message('No namespace ID provided'))
                
                ns_data = json_loads(request.body)
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
                
                # Check if user is the owner or a manager
                if request.user not in ns.get_users():
                    return JsonResponse(error_message('No namespace found or user does not have permission to update this namespace'))
                
                if ns.get_role(request.user) == 'viewer':
                    return JsonResponse(error_message('Only the owner or a manager can update the namespace'))

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

                        existing_role = None
            
                        if ns_owner:
                            new_owner_obj = User.objects.filter(username=ns_owner.get('username')).first()

                            if not new_owner_obj:
                                raise ValueError('New owner\'s username not found')
                            
                            if new_owner_obj == ns.owner:
                                raise ValueError('User is already the owner of the namespace')
                            
                            # Remove the current owner role
                            NamespaceRoles.objects.filter(namespace=ns, role='owner').delete()

                            # Check if the new owner is already part of the namespace, if so, delete the user's role
                            existing_role = NamespaceRoles.objects.filter(namespace=ns, user=new_owner_obj).first()
                            if existing_role:
                                existing_role.role = 'owner'
                            else:
                                NamespaceRoles.objects.create(
                                    namespace=ns,
                                    user=new_owner_obj,
                                    role='owner'
                                )
                        
                            ns.default = False

                        if ns_users:
                            # Check if the new owner is also in ns_users
                            if ns_owner:
                                for user in ns_users:
                                    if user['username'] == ns_owner['username']:
                                        raise ValueError('New owner cannot be assigned additional roles')

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
                                if role not in ['manager', 'viewer']:
                                    raise ValueError('Invalid role')
                                
                                NamespaceRoles.objects.create(
                                    namespace=ns,
                                    user=user_obj,
                                    role=role
                                )

                        if ns_name:
                            ns.name = ns_name

                        # push changes to the database
                        ns.save()

                        # Save the existing role changes
                        if existing_role:
                            existing_role.save()
                
                except (IntegrityError, ValueError) as e:
                    return JsonResponse(error_message(str(e)))

                ns_info = ns.info()
                ns_info['users'] = ns.get_users_info()
                return JsonResponse(success_message('Update namespace', ns_info))

    except Exception as e:
        logging.error(str(e))
        return JsonResponse(error_message(str(e)))

@csrf_exempt
@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
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

    except Exception as e:
        logging.error(str(e))
        return JsonResponse(error_message(str(e)))
    
# @csrf_exempt
# @api_view(['GET'])
# def namespace_info(request, ns_name):
#     """
#     Get properties of a single namespace
#     """
#     try:
#         namespace = Namespaces.objects.filter(user=request.user, namespace__nsid=ns_name).first()
#         if not namespace:
#             return JsonResponse(error_message('No namespace found'))
#
#         current_user = list(filter(lambda u: u['username'] == request.user.username, ns_users_list))[0]
#         ns_users = list(filter(lambda u:
#                                u['role'] != 'owner' or
#                                not (current_user['username'] == u['username'] and current_user[
#                                    'role'] == 'owner'),
#                                ns_users_list))
#         ns_owners = list(filter(lambda u: u['role'] == 'owner', ns_users_list))
#
#         ns_owners = sorted(ns_owners, key=lambda u: u['name'])
#         ns_users = sorted(ns_users, key=lambda u: u['name'])
#
#         for ns in namespace_list:
#             ns['requester'] = current_user
#             ns['owners'] = ns_owners
#             ns['users'] = ns_users
#
#         return JsonResponse(success_message('Get namespace', namespace.info()))
#
#     except Exception as e:
#         return JsonResponse(error_message(str(e)))

"""
{
	"status": "success",
	"namespaces": [
		{
			"nsid": "jp5999-naoa",
			"name": "Joe Prakash",
			"default": true,
			"created_at": "00:23:36, Sun 04 Aug 2024",
			"updated_at": "00:23:36, Sun 04 Aug 2024",
			"owner": {
				"username": "jp5999",
				"name": "Joe Prakash",
				"email": "jp5999@nyu.edu",
				"avatar": "https://blob.osiriscloud.io/profile.webp"
			}
		}
	],
	"message": "Get namespaces"
}

"""
