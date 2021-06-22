"""
ASGI config for telescope2 project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

import django

import telescope2.web.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telescope2.settings.production')

django.setup()


def create_app():

    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.core.asgi import get_asgi_application

    return ProtocolTypeRouter({
        'http': get_asgi_application(),
        'websocket': AuthMiddlewareStack(URLRouter(telescope2.web.routing.websocket_urlpatterns)),
    })


application = create_app()
