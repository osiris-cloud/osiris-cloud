from django.urls import path, re_path
from . import views


urlpatterns = [
    re_path(r'^(/(?P<nsid>[0-9a-zA-Z_-]+))?$', views.dashboard, name='dashboard'),
]
