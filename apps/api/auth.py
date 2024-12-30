from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.permissions import BasePermission

from .models import AccessToken


class AccessTokenAuthentication(authentication.BaseAuthentication):
    """
    Authentication class for DRF that uses AccessToken model
    """
    keyword = 'Token'
    model = AccessToken

    def authenticate(self, request):
        auth = authentication.get_authorization_header(request).split()

        # If no Authorization header or not a Bearer token, skip this authentication method
        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            raise exceptions.AuthenticationFailed('Invalid token header. No credentials provided')
        elif len(auth) > 2:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string should not contain spaces')

        try:
            token = auth[1].decode()
        except UnicodeError:
            raise exceptions.AuthenticationFailed('Invalid token header. Token string contains invalid characters')

        return self.authenticate_credentials(token, request)

    def authenticate_credentials(self, key, request):
        try:
            token = self.model.objects.get(key=key)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        if token.is_expired():
            raise exceptions.AuthenticationFailed('Token expired')

        if not token.has_permission(request.path, request.method):
            raise exceptions.AuthenticationFailed('Token does not have permission for this request')

        token.update_last_used()  # Update last used timestamp

        return token.user, token

    def authenticate_header(self, request):
        return self.keyword


class AccessTokenOrIsAuthenticated(BasePermission):
    """
    Permission class that allows access to authenticated users (session auth) OR valid access tokens
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            if request.user.role == 'blocked':
                return False

            if (request.user.role == 'guest') and (request.method in ('PUT', 'PATCH', 'DELETE')):
                return False

        # Allow access if user is authenticated through session
        if request.user and request.user.is_authenticated and (not hasattr(request, 'auth') or request.auth is None):
            return True

        # For token auth, check token permissions
        if hasattr(request, 'auth') and isinstance(request.auth, AccessToken):
            return request.auth.has_permission(request.path, request.method)

        return False
