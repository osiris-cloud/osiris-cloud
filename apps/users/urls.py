from django.urls import path

from . import views

urlpatterns = [
    path('profile', views.profile, name="profile"),
    path('access-keys', views.access_keys, name="access-keys"),
]
