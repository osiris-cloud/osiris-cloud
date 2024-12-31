from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from apps.api.models import AccessToken


class KeyAuthMiddleware(BaseMiddleware):
    """
    Middleware to authenticate access key on websockets
    """

    @database_sync_to_async
    def get_user(self, token_key):
        try:
            token = AccessToken.objects.get(key=token_key)
            return token.user
        except AccessToken.DoesNotExist:
            return AnonymousUser()

    @database_sync_to_async
    def authenticate(self, token):
        return self.get_user(token)

    async def __call__(self, scope, receive, send):
        headers = dict(scope['headers'])
        token_header = headers.get(b'authorization', b'').decode().split(' ')

        if len(token_header) > 1:
            token = token_header[1]
            scope["user"] = await self.get_user(token)
        else:
            pass  # Auth Middleware will take care of auth in session mode

        return await super().__call__(scope, receive, send)
