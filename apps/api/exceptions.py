from rest_framework.views import exception_handler


def exceptions(exc, context):
    # Call REST framework's default exception handler first, to get the standard error response.
    response = exception_handler(exc, context)

    if response is None:
        return response

    match response.data['detail'].code:
        case 'not_authenticated':
            detail = {
                'message': 'Request is unauthenticated'
            }
        case 'authentication_failed':
            detail = {
                'message': 'Authentication failed'
            }
        case 'permission_denied':
            detail = {
                'message': 'CSRF check failed'
            }
        case _:
            detail = {
                'message': response.data['detail'].code
            }

    response.data = {
        'status': 'error',
        **detail
    }

    return response
