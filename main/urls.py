from django.urls import path, include

from . import views

from core.settings import DEBUG

urlpatterns = [
    path("", views.index, name="index"),
    path("login", include("apps.oauth.urls")),
    path("logout", views.logout_view, name="logout"),
    path("profile", include("apps.users.urls")),
    path("faq", views.faq, name="faq"),
    path("about", views.about, name="about"),
    path("architecture", views.architecture, name="architecture"),
    path("observability", views.observability, name="observability"),
    path("privacy", views.privacy, name="privacy"),

    path("dashboard", include("apps.dashboard.urls")),
    path("vm", include("apps.vm.urls")),
]

if DEBUG:
    urlpatterns += [
        path("seed", views.seed, name="seed"),
    ]
