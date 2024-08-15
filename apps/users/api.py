import logging
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from json import loads as json_loads

from core.utils import success_message, error_message, random_str
from .models import User
from ..k8s.models import Namespace, NamespaceRoles
from ..users.utils import sanitize_nsid


def get_user_default_ns(user: User) -> Namespace:
    return NamespaceRoles.objects.filter(user=user, role='owner', namespace__default=True).first().namespace


@csrf_exempt
@api_view(['GET', 'POST', 'PATCH', 'DELETE'])
def namespace(request, ns_name=None):
    """
    Get properties of all namespaces the user is part of, and it's limit
    """
    ns_filter = {}
    if ns_name:
        if ns_name == 'default':
            if request.session.get('namespace') is None:
                request.session['namespace'] = get_user_default_ns(request.user).nsid
            ns_filter['nsid'] = request.session.get('namespace')
        else:
            ns_filter['nsid'] = ns_name

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

                if ns_name:
                    return JsonResponse(success_message('Get namespace', result[0]))

                return JsonResponse(success_message('Get namespaces', {
                    'namespaces': result,
                }))

            case 'POST':
                if not request.body:
                    return JsonResponse(error_message('No data provided'))
                
                ns_data = json_loads(request.body)

                ns_name = ns_data.get('name')
                if not ns_name:
                    return JsonResponse(error_message('No name provided'))

                # Max length 20 chars
                ns_nsid = sanitize_nsid(ns_name)[:20]
                ns_nsid = ns_nsid + '-' + random_str(19 - len(ns_nsid))

                ns_default = ns_data.get('default', False)
                
                # If the new namespace is set as default, update other namespaces owned by the user
                if ns_default:
                    Namespace.objects.filter(users=request.user, default=True).update(default=False)

                # List of usernames with their role to add to the namespace.
                ns_users = ns_data.get('users', [])

                # Create namespace
                ns = Namespace.objects.create(
                    nsid = ns_nsid,
                    name=ns_name,
                    default=ns_default
                )

                if not ns:
                    return JsonResponse(error_message('Failed to create namespace'))

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
                        continue

                    role = user['role']
                    if role not in ['manager', 'viewer']:
                        return JsonResponse(error_message('Invalid role', {}))

                    NamespaceRoles.objects.create(
                        namespace=ns,
                        user=user_obj,
                        role=role
                    )

                ns_info = ns.info()
                ns_info['users'] = ns.get_users_info()
                return JsonResponse(success_message('Create namespace', ns_info))

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
