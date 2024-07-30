from rest_framework.views import exception_handler


def exceptions(exc, context):
    # Call REST framework's default exception handler first, to get the standard error response.
    response = exception_handler(exc, context)

    if response is None:
        return response

    detail = {}

    match response.data['detail'].code:
        case 'not_authenticated':
            detail = {
                'detail': 'Request is unauthenticated. Go to /api/token/ in an existing session to get a token'
            }

        case 'authentication_failed':
            detail = {
                'detail': 'Authentication failed. Auth header should be in the format -> Authorization: "Token <token>"'
            }

    response.data = {
        'status': 'error',
        **detail
    }

    return response
