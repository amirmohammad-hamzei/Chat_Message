"""
ASGI config for websocket project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import django

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'websocket.settings')

# Initialize Django before any other imports
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.sessions import SessionMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Import routing after Django is initialized
import chat.routing as chat_routing

# Combine WebSocket URL patterns
websocket_urlpatterns = chat_routing.websocket_urlpatterns

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        SessionMiddlewareStack(
            AuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            )
        )
    ),
})
