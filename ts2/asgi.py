"""
ASGI config for ts2 project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

import django

import ts2.web.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ts2.conf.production')

django.setup()


def create_app():
    # TODO: Remove websocket
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.core.asgi import get_asgi_application

    return ProtocolTypeRouter({
        'http': get_asgi_application(),
        'websocket': AuthMiddlewareStack(URLRouter(ts2.web.routing.websocket_urlpatterns)),
    })


application = create_app()
