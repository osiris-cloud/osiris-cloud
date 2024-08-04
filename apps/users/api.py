from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from json import loads as json_loads

from core.utils import success_message, error_message
from .models import User
from ..k8s.models import Namespace, NamespaceRoles


def get_user_default_ns(user: User) -> Namespace:
    return Namespace.objects.filter(user=user, default=True).first()


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

                result = [ns.info() for ns in namespaces]

                if ns_name:
                    return JsonResponse(success_message('Get namespace', result[0]))

                return JsonResponse(success_message('Get namespaces', {
                    'namespaces': result,
                }))

            case 'POST':
                ns_data = request.data.get('data')
                if not ns_data:
                    return JsonResponse(error_message('No data provided'))
                ns_data = json_loads(ns_data)
                print(ns_data)

                JsonResponse(success_message('Create namespace', {}))

    except Exception as e:
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
