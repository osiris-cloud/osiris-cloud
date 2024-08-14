from django.urls import path
from core.settings import DEBUG

from . import views

urlpatterns = [
    path('', views.login_view, name="login_view"),
    path('/nyu', views.nyu_login, name="nyu_login"),
    path('/nyu/callback', views.nyu_callback, name="nyu_callback"),
    path('/github', views.github_login, name="github_login"),
    path('/github/callback', views.github_callback, name="github_callback"),
    path('/link-account', views.link_github, name="link_github"),
    path('/unlink-account', views.unlink_github, name="unlink_github"),
]

if DEBUG:
    urlpatterns += [
        path('/seed', views.seed_login, name="seed_login"),
    ]
