"""
ASGI config for decisionchess project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
from channels.auth import AuthMiddlewareStack 
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

# Import settings before routing import
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'decisionchess.settings')

# Define a function to defer imports
def get_ws_application():
    import main.routing  # Import inside the function to defer the import

    return ProtocolTypeRouter({
        'http': get_asgi_application(),
        'websocket': AuthMiddlewareStack(  
            URLRouter(
                main.routing.websocket_urlpatterns
            )
        ), 
    })

application = get_ws_application()
