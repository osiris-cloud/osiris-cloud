from django.urls import path, re_path

from . import routes

from ..vm import api as vm_api
from ..vm import consumers as vm_consumers

from ..users import api as user_api
from ..users import consumers as user_consumers

from ..k8s import api as k8s_api

from ..secret_store import api as secret_store_api
from ..admin_console import api as admin_api
from ..container_registry import api as registry_api
from ..container_apps import api as container_apps_api

root_urlpatterns = [
    path('', routes.root),
    path('/token', routes.get_token),
]

admin_urlpatterns = [
    path('/admin/external-user', admin_api.external_user),
    path('/admin/gh-search', admin_api.gh_user_search),
]

vm_urlpatterns = [
    re_path(r'^/vm$', vm_api.virtual_machines),
    re_path(r'^/vm/(?P<vmid>[^/]+)$', vm_api.virtual_machines),
    re_path(r'^/vnc$', vm_api.vnc),
    re_path(r'^/vnc/(?P<vmid>[^/]+)$', vm_api.vnc),
]

user_urlpatterns = [
    re_path(r'^/namespace$', user_api.namespace),
    re_path(r'^/namespace/(?P<nsid>[^/]+)$', user_api.namespace),
    re_path(r'^/user$', user_api.user),
    re_path(r'^/user/(?P<username>[^/]+)$', user_api.user),
]

secret_store_urlpatterns = [
    re_path(r'^/secret-store$', secret_store_api.secret_store),
    re_path(r'^/secret-store/(?P<nsid>[^/]+)$', secret_store_api.secret_store),
    re_path(r'^/secret-store/(?P<nsid>[^/]+)/(?P<secretid>[^/]+)$', secret_store_api.secret_store),
    re_path(r'^/secret-store/(?P<nsid>[^/]+)/(?P<secretid>[^/]+)/(?P<action>[^/]+)$', secret_store_api.secret_store),
]

event_urlpatterns = [
    re_path(r'^/event$', k8s_api.event),
    re_path(r'^/event/(?P<event_id>[^/]+)$', k8s_api.event)
]

container_registry_urlpatterns = [
    re_path(r'^/container-registry$', registry_api.container_registry),
    re_path(r'^/container-registry/name-check$', registry_api.name_check),
    re_path(r'^/container-registry/(?P<nsid>[^/]+)$', registry_api.container_registry),
    re_path(r'^/container-registry/(?P<nsid>[^/]+)/(?P<crid>[^/]+)$', registry_api.container_registry),
    re_path(r'^/container-registry/(?P<nsid>[^/]+)/(?P<crid>[^/]+)/(?P<action>[^/]+)$', registry_api.container_registry),
]

container_apps_urlpatterns = [
    re_path(r'^/container-apps$', container_apps_api.container_apps),
    re_path(r'^/container-apps/name-check$', container_apps_api.name_check),
    re_path(r'^/container-apps/(?P<nsid>[^/]+)$', container_apps_api.container_apps),
    re_path(r'^/container-apps/(?P<nsid>[^/]+)/(?P<appid>[^/]+)$', container_apps_api.container_apps),
    re_path(r'^/container-apps/(?P<nsid>[^/]+)/(?P<appid>[^/]+)/(?P<action>[^/]+)$', container_apps_api.container_apps),
]

urlpatterns = (
        root_urlpatterns +
        admin_urlpatterns +
        vm_urlpatterns +
        user_urlpatterns +
        secret_store_urlpatterns +
        event_urlpatterns +
        container_registry_urlpatterns
)

websocket_urlpatterns = (
    re_path(r'^api/vnc/(?P<vmid>[^/]+)$', vm_consumers.VNCProxyConsumer.as_asgi()),
    re_path(r'^api/user/search$', user_consumers.UserSearchConsumer.as_asgi()),
)
