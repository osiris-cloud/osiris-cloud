from rest_framework.decorators import api_view
from django.http import JsonResponse
from datetime import datetime

from .models import AccessToken
from ..k8s.constants import ACCESS_SCOPES

from core.utils import success_message, error_message
from .utils import validate_create_token


@api_view(['GET'])
def root(request):
    return JsonResponse({
        'status': 'success',
        'user': request.user.username,
    })


@api_view(['GET', 'PUT', 'DELETE'])
def tokens(request, key_id=None):
    if request.method == 'GET':
        keys = AccessToken.objects.filter(user=request.user, system_use=False)
        return JsonResponse(success_message('Get access keys', {
            'keys': [key.info() for key in keys],
        }))

    elif request.method == 'PUT':
        valid, err = validate_create_token(request.data)
        if not valid:
            return JsonResponse(error_message(err), status=400)

        exp = request.data.get('expiration')

        token = AccessToken.objects.create(
            user=request.user,
            name=request.data['name'],
            scopes=['global'] if 'global' in request.data['scopes'] else request.data['scopes'],
            can_write=request.data['can_write'],
            expiration=datetime.fromisoformat(exp) if exp is not None else None,
        )

        return JsonResponse(success_message('Create access key', {
            'key': token.key,
        }))

    elif request.method == 'DELETE':
        if key_id is None:
            return JsonResponse(error_message('Key is required'), status=400)

        token = AccessToken.objects.filter(user=request.user, keyid=key_id, system_use=False).first()
        if token is None:
            return JsonResponse(error_message('Key not found'), status=404)

        token.delete()
        return JsonResponse(success_message('Delete access key'))


@api_view(['GET'])
def access_key_scopes(request):
    return JsonResponse({
        'status': 'success',
        'scopes': ACCESS_SCOPES,
    })
