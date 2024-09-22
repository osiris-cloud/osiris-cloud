from django.urls import path, re_path

from . import routes

from ..vm import api as vm_api
from ..vm import consumers as vm_consumers

from ..users import api as user_api
from ..users import consumers as user_consumers

from ..k8s import api as k8s_api

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
    re_path(r'^/namespace/(?P<nsid>[^/]+)$', user_api.namespace),  # Matches /namespace/<nsid>
    re_path(r'^/user$', user_api.user),  # Matches /user
    re_path(r'^/user/(?P<username>[^/]+)$', user_api.user)  # Matches /user/<username>
]

secret_urlpatterns = [
    re_path(r'^/secret$', k8s_api.secret),  # Matches /secret
    re_path(r'^/secret/(?P<nsid>[^/]+)$', k8s_api.secret),  # Matches /secret/<secretid>
    re_path(r'^/secret/(?P<nsid>[^/]+)/(?P<secret_name>[^/]+)$', k8s_api.secret)  # Matches /secret/<nsid>/<secret_name>
]

urlpatterns = vm_urlpatterns + user_urlpatterns + secret_urlpatterns

websocket_urlpatterns = [
    re_path(r'^api/vnc/(?P<vmid>[^/]+)$', vm_consumers.VNCProxyConsumer.as_asgi()),
    re_path(r'^api/user/search$', user_consumers.UserSearchConsumer.as_asgi()),
]
