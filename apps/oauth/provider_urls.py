from django.views.decorators.csrf import csrf_exempt
from oidc_provider import settings, views
from django.urls import re_path


app_name = "oidc_provider"

urlpatterns = [
    re_path(r"^/authorize/?$", views.AuthorizeView.as_view(), name="authorize"),
    re_path(r"^/token/?$", csrf_exempt(views.TokenView.as_view()), name="token"),
    re_path(r"^/userinfo/?$", csrf_exempt(views.userinfo), name="userinfo"),
    re_path(r"^/end-session/?$", views.EndSessionView.as_view(), name="end-session"),
    re_path(r"^/end-session-prompt/?$", views.EndSessionPromptView.as_view(), name="end-session-prompt"),
    re_path(r"^/introspect/?$", views.TokenIntrospectionView.as_view(), name="token-introspection"),
    re_path(r"^/jwks/?$", views.JwksView.as_view(), name="jwks"),
    re_path(r"^/\.well-known/openid-configuration/?$", views.ProviderInfoView.as_view(), name="provider-info"),
]

if settings.get("OIDC_SESSION_MANAGEMENT_ENABLE"):
    urlpatterns += [
        re_path(r"^/check-session-iframe/?$", views.CheckSessionIframeView.as_view(), name="check-session-iframe"),
    ]
