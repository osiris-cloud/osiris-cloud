import asyncio
import websockets
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from core.settings import env
from json import dumps as json_dumps

from apps.vm.models import VM

headers = {
    "Authorization": f"Bearer {env.k8s_token}",
}


class VNCProxyConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vnc_url = f"{env.k8s_ws_url}/apis/subresources.kubevirt.io/v1/namespaces/jp5999/virtualmachineinstances/test-11/vnc"
        self.remote_ws = None
        self.user = None
        self.vmid = None
        self.remote_task = None

    async def backward(self):  # Remote -> Client
        try:
            async for message in self.remote_ws:
                await self.send(bytes_data=message)
        except websockets.exceptions.ConnectionClosedError:
            await self.close()

    async def receive(self, text_data=None, bytes_data=None):  # Client -> Remote
        if not self.remote_ws:
            return
        try:
            await self.remote_ws.send(bytes_data)
        except websockets.exceptions.ConnectionClosedError:
            await self.close()

    async def connect(self):
        self.user = self.scope["user"]
        self.vmid = self.scope['url_route']['kwargs'].get('vmid')
        await self.accept()

        if not self.user.is_authenticated:
            await self.send(text_data=json_dumps({"status": "error", "message": "Unauthenticated"}))
            await self.close()
            return None

        if not self.vmid:
            await self.send(text_data=json_dumps({"status": "error", "message": "No VMID"}))
            await self.close()
            return None

        try:
            await sync_to_async(self.user.vms.get)(vmid=self.vmid)
        except VM.DoesNotExist:
            await self.send(text_data=json_dumps({"status": "error", "message": "VM not found or Unauthorized"}))
            await self.close()
            return None

        self.remote_task = asyncio.create_task(self.connect_to_remote())

    async def connect_to_remote(self):
        try:
            self.remote_ws = await websockets.connect(self.vnc_url, extra_headers=headers)
            await self.backward()
        except Exception as e:
            print(f"Error connecting to remote: {e}")
            await self.close()

    async def disconnect(self, close_code):
        if self.remote_task:
            self.remote_task.cancel()
        if self.remote_ws:
            await self.remote_ws.close()
