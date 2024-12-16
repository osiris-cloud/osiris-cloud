from rest_framework.views import exception_handler


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

    return response
