from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.api.models import AccessToken


class KeyAuthMiddleware(BaseMiddleware):
    """
    Middleware to authenticate access key on websockets
    """
    @database_sync_to_async
    def get_token(self, token):
        try:
            token = AccessToken.objects.get(key=token)
            return token
        except AccessToken.DoesNotExist:
            return None

    @database_sync_to_async
    def get_user(self, token: AccessToken | str):
        if isinstance(token, str):
            token = self.get_token(token)

        if token is None:
            return AnonymousUser()

        return token.user

    @database_sync_to_async
    def authenticate(self, token):
        return self.get_user(token)

    async def __call__(self, scope, receive, send):
        headers = dict(scope['headers'])
        key_header = headers.get(b'authorization', b'').decode().split(' ')

        if len(key_header) == 2:  # With token
            access_key = key_header[1]

            token = await self.get_token(access_key)
            user = await self.get_user(token)

            scope["token"] = token
            scope["user"] = user

        # Auth Middleware will take care of auth in session mode

        return await super().__call__(scope, receive, send)
