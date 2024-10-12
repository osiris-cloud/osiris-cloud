from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.container_registry, name='container_registry'),
    path('/create', views.container_registry_create, name='container_registry_create'),
    path('/edit', views.container_registry_edit, name='container_registry_edit'),
    path('/<str:crid>', views.container_registry_view, name='container_registry_view'),
]
