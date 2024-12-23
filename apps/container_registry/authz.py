import logging

from django.http import JsonResponse
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from base64 import b64decode
from datetime import datetime
from datetime import UTC

from core.utils import error_message
from ..api.models import AccessToken
from .models import ContainerRegistry

from .utils import generate_auth_token, get_registry_permissions


@csrf_exempt
@require_http_methods(["GET"])
def registry_auth(request):
    """
    Implements Registry authentication and authorization.
    If public repo, it skips checking for authorization and generate a token with only pull permissions
    """
    auth_header = request.headers.get('Authorization', '')

    if not auth_header.startswith('Basic '):
        return HttpResponseRedirect('/')

    def decode_creds() -> tuple[str, str]:
        try:
            credentials = b64decode(auth_header[6:]).decode()
            u, p = credentials.split(':', 1)
            return u, p
        except Exception:
            return '', ''

    def check_auth() -> tuple[bool, [AccessToken | None], [str | None]]:
        try:
            user, psw = decode_creds()
            key_ = AccessToken.objects.get(token=psw)
            if not key_ or user != 'osiris':
                return False, None, 'Permission denied'
            if not any(scope_ in ('container-registry', 'global') for scope_ in key.scopes):
                return False, key_, 'Token has inadequate permissions'
            return True, key_, None
        except AccessToken.DoesNotExist:
            return False, None, 'Permission denied'

    try:
        # Authorization
        if scope := request.GET.get('scope'):
            r_type, r_name, r_actions = scope.split(':')
            r_name = r_name.split('/')[0]
            sub_repo = r_name.split('/')[1] if '/' in r_name else None
            repo_path = f'{r_name}/{sub_repo}' if sub_repo else r_name

            if r_type not in ('repository', 'catalog'):
                return JsonResponse({'message': 'Permission denied'}, status=403)

            if r_name == '*':
                return JsonResponse({'message': 'Permission denied'}, status=403)

            repo = ContainerRegistry.objects.get(repo=r_name)

            if repo.public:
                token = generate_auth_token('repository', repo_path, ['pull'])
            else:
                valid, key, err = check_auth()
                if not valid:
                    return JsonResponse({'errors': [{'code': 'UNAUTHORIZED', 'message': err}]}, status=401)

                ns_role = repo.get_role(key.user)
                allowed_actions = get_registry_permissions(ns_role)
                token = generate_auth_token(r_type, repo_path, allowed_actions)

        # Authentication
        else:
            valid, _, err = check_auth()
            if not valid:
                return JsonResponse({'errors': [{'code': 'UNAUTHORIZED', 'message': err}]}, status=401)

            token = generate_auth_token()

        return JsonResponse({
            'token': token,
            'access_token': token,
            'expires_in': 3600,
            'issued_at': datetime.now(UTC).isoformat() + 'Z'
        })

    except (AccessToken.DoesNotExist, ContainerRegistry.DoesNotExist):
        return JsonResponse({
            'errors': [{'code': 'UNAUTHORIZED', 'message': 'Permission denied'}]
        }, status=401)

    except Exception as e:
        logging.exception(e)
        return JsonResponse(error_message(), status=500)
