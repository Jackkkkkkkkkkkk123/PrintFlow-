"""
ASGI config for yw_crm project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
import sys
import asyncio
import django
from django.core.asgi import get_asgi_application

# 修复Windows事件循环问题
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yw_crm.settings')
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

from crm.consumers import NotificationConsumer
from crm.middleware.websocket_auth_middleware import SessionAuthMiddlewareStack

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": SessionAuthMiddlewareStack(
        URLRouter(
            websocket_urlpatterns
        )
    ),
}) 