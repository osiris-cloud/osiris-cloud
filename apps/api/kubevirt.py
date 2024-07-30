from __future__ import absolute_import
import httpx
from core.settings import env


class ApiClient:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.headers = {
            'Authorization': f'Token {self.token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Osiris Python API',
        }
        self.rest_client = None

    async def init_rest_client(self):
        self.rest_client = httpx.AsyncClient()

    async def request(self, method: str, query_params=None, post_params=None, body=None):
        """
        Makes the HTTP request using RESTClient.
        """
        if self.rest_client is None:
            await self.init_rest_client()

        if query_params is None:
            query_params = {}

        if post_params is None:
            post_params = {}

        if body is None:
            body = {}

        async with self.rest_client as client:
            response = await client.request(
                method,
                self.url,
                params=query_params,
                data=post_params,
                json=body,
                headers=self.headers,
            )

        return response
