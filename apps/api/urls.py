from django.urls import path, re_path

from . import routes

from ..vm import api as vm_api
from ..vm import consumers as vm_consumers

from ..users import api as user_api

vm_urlpatterns = [
    path('', routes.root),
    path('/token', routes.get_token),
    re_path(r'^/vm/?$', vm_api.virtual_machines),  # Matches /vm
    re_path(r'^/vm/(?P<vmid>[^/]+)/?$', vm_api.virtual_machines),  # Matches /vm/<vmid>
    re_path(r'^/vnc/?$', vm_api.vnc),  # Matches /vnc and /vnc/
    re_path(r'^/vnc/(?P<vmid>[^/]+)/?$', vm_api.vnc),  # Matches /vnc/<vmid>
]

user_urlpatterns = [
    re_path(r'^/namespace/?$', user_api.namespace),  # Matches /namespace
    re_path(r'^/namespace/(?P<ns_name>[^/]+)/?$', user_api.namespace),  # Matches /namespace/<ns_name>
    re_path(r'^/user-search/?$', user_api.user_search),  # Matches /user-search
]

urlpatterns = vm_urlpatterns + user_urlpatterns

websocket_urlpatterns = [
    re_path('^/api/vnc/(?P<vmid>[^/]+)/?$', vm_consumers.VNCProxyConsumer.as_asgi()),
]
