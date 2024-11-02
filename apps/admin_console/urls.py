from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name="admin_dashboard"),
    path('/init', views.init_app, name="admin_init"),
    path('/users', views.users, name="admin_users"),
]
