from django.urls import path, include

from . import views

from core.settings import DEBUG

urlpatterns = [
    path("", views.index, name="index"),
    path("healthz", views.healthz, name="healthz"),
    path("login", include("apps.oauth.urls")),
    path("logout", views.logout_view, name="logout"),
    path("", include("apps.users.urls")),

    path("faq", views.faq, name="faq"),
    path("about", views.about, name="about"),
    path("privacy", views.privacy, name="privacy"),
    path("eula", views.eula, name="eula"),

    path("dashboard", include("apps.dashboard.urls")),
    path("vm", include("apps.vm.urls")),
    path("container-registry", include("apps.container_registry.urls")),
    path("container-apps", include("apps.container_apps.urls")),
    path("secret-store", include("apps.secret_store.urls")),
]

if DEBUG:
    urlpatterns += [
        path("seed", views.seed, name="seed"),
    ]
