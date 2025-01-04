from django.urls import re_path

from . import views

urlpatterns = [
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+))?$', views.secret_store, name='secret_store'),
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+)/create)$', views.secret_store_create, name='secret_store_create'),
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+)/(?P<secret_id>[0-9a-zA-Z_-]+))$', views.secret_store_view,
            name='secret_store_view'),
    re_path(r'^/(?P<nsid>[0-9a-zA-Z_-]+)/(?P<secret_id>[0-9a-zA-Z_-]+)(/edit)$', views.secret_store_edit,
            name='secret_store_edit'),
]
