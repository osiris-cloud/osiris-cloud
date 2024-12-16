from rest_framework.views import exception_handler
from django.http import Http404
from rest_framework.response import Response
from rest_framework import status


def exception_processor(exc, context):
    # Call REST framework's default exception handler first, to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        detail = response.data

        if isinstance(detail, dict) and 'detail' in detail:
            detail = detail['detail']
        elif isinstance(detail, list):
            detail = ' '.join(str(item) for item in detail)

        response.data = {
            'status': 'error',
            'message': str(detail)
        }

    else:
        # If response is None, create a new response for unhandled exceptions
        if isinstance(exc, Http404):
            response = Response({
                'status': 'error',
                'message': 'Resource not found'
            }, status=status.HTTP_404_NOT_FOUND)
        else:
            response = Response({
                'status': 'error',
                'message': str(exc) if str(exc) else 'Internal server error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return response
