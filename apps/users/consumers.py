import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from algoliasearch_django import raw_search
from json import dumps as json_dumps
from websockets import exceptions as ws_exceptions

from core.utils import error_message, success_message
from .models import User

search_params = {"hitsPerPage": 5}


class UserSearchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        await self.accept()

        if not user.is_authenticated:
            await self.send(text_data=json_dumps(error_message('Unauthenticated')))
            await self.close()
            return None

        await self.send(text_data=json_dumps(success_message('Connected')))

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            await self.send(text_data=json_dumps(error_message('No query provided')))
            return None

        search = raw_search(User, text_data, search_params).get('hits')
        filter_result = lambda hit: {'username': hit.get('username'),
                                     'first_name': hit.get('first_name'),
                                     'last_name': hit.get('last_name'),
                                     'email': hit.get('email'),
                                     'avatar': hit.get('avatar')
                                     }
        result = {
            'users': [filter_result(hit) for hit in search]
        }

        try:
            await self.send(text_data=json_dumps(result))
        except ws_exceptions.ConnectionClosed:
            pass
        except Exception as e:
            logging.info(e)
