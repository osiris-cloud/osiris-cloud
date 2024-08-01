import logging
from django.http import HttpResponsePermanentRedirect
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from urllib.parse import parse_qs
from rest_framework.authtoken.models import Token


class TokenAuthMiddleware(BaseMiddleware):

    @database_sync_to_async
    def get_user(self, token_key):
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
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
            pass  # Auth Middleware will take care of this

        return await super().__call__(scope, receive, send)


class RemoveSlashMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.split('/')
        if len(path) > 1:
            if 'admin' in path[1]:
                pass
            elif request.path.endswith('/') and len(request.path) > 1:
                return HttpResponsePermanentRedirect(request.path[:-1])
        try:
            response = self.get_response(request)
            return response
        except Exception as e:
            logging.exception(e)
            return HttpResponsePermanentRedirect('/')
