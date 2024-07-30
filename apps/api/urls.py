from django.urls import path, re_path

from . import routes

from ..vm import api as vm_api
from ..vm import consumers as vm_consumers

from ..users import api as user_api
from ..users import consumers as user_consumers

vm_urlpatterns = [
    path('', routes.root),
    path('/token', routes.get_token),

    re_path(r'^/vm$', vm_api.virtual_machines),  # Matches /vm
    re_path(r'^/vm/(?P<vmid>[^/]+)$', vm_api.virtual_machines),  # Matches /vm/<vmid>

    re_path(r'^/vnc$', vm_api.vnc),  # Matches /vnc
    re_path(r'^/vnc/(?P<vmid>[^/]+)$', vm_api.vnc),  # Matches /vnc/<vmid>
]

user_urlpatterns = [
    re_path(r'^/namespace$', user_api.namespace),  # Matches /namespace
    re_path(r'^/namespace/(?P<ns_name>[^/]+)$', user_api.namespace),  # Matches /namespace/<ns_name>
]

urlpatterns = vm_urlpatterns + user_urlpatterns

websocket_urlpatterns = [
    re_path(r'^api/vnc/(?P<vmid>[^/]+)$', vm_consumers.VNCProxyConsumer.as_asgi()),
    re_path(r'^api/user-search$', user_consumers.UserSearchConsumer.as_asgi()),
]
