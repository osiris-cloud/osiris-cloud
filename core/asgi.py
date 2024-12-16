import os
import django

django.setup()  # Need this here to initialize api first

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from apps.api.middleware import KeyAuthMiddleware

from apps.api import urls

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": KeyAuthMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                urls.websocket_urlpatterns,
            )
        )
    ),
})
