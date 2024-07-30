from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from django.http import JsonResponse
from json import loads as json_loads

from core.utils import success_message, error_message
from .models import User
from ..k8s.models import Namespace, Namespaces, Limit


def get_user_default_ns(user: User) -> Namespace:
    return user.namespaces.filter(role='owner').filter(namespace__default=True).first().namespace


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
            ns_filter['namespace__nsid'] = request.session.get('namespace')
        else:
            ns_filter['namespace__nsid'] = ns_name

    try:
        match request.method:
            case 'GET':
                namespaces = Namespaces.objects.filter(user=request.user, **ns_filter)
                if not namespaces.exists():
                    return JsonResponse(error_message('No namespace found'))
                namespace_dict = namespaces.first().info() if ns_name else [n.info() for n in namespaces]
                return JsonResponse(success_message('Get namespace(s)', {
                    'namespace' if ns_name else 'namespaces': namespace_dict
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
