from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("main.urls")),
    path("api", include('apps.api.urls')),
    path("admin", include('apps.admin_console.urls')),
    path("underground", admin.site.urls),
]
