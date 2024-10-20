from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+))?$', views.container_registry, name='container_registry'),
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+)/create)$', views.container_registry_create, name='container_registry_create'),
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+)/(?P<crid>[0-9a-zA-Z_-]+))$', views.container_registry_view,
            name='container_registry_view'),
    re_path(r'^/(?P<nsid>[0-9a-zA-Z_-]+)/(?P<crid>[0-9a-zA-Z_-]+)(/edit)$', views.container_registry_edit,
            name='container_registry_edit'),
]
