from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+))?$', views.container_apps, name='container_apps'),
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+)/create)$', views.container_apps_create, name='container_apps_create'),
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+)/(?P<appid>[0-9a-zA-Z_-]+))$', views.container_apps,
            name='container_apps_view'),
    re_path(r'^/(?P<nsid>[0-9a-zA-Z_-]+)/(?P<appid>[0-9a-zA-Z_-]+)(/edit)$', views.container_apps_edit,
            name='container_apps_edit'),
]
