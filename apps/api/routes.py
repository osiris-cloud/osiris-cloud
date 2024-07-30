from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from apps.vm.utils import success_message


@api_view(['GET'])
def root(request):
    return Response({
        'status': 'success',
        'user': request.user.username,
    })


@api_view(['GET'])
def get_token(request):
    return Response(success_message('Get auth token', {
        'user': request.user.username,
        'token': Token.objects.get_or_create(user=request.user)[0].key,
    }))
