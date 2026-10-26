# mahdavi_platform/asgi.py
import os
import django
from django.core.asgi import get_asgi_application

# تنظیم محیط Django قبل از import کردن مدل‌ها
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mahdavi_platform.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import mahdavi_app.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            mahdavi_app.routing.websocket_urlpatterns
        )
    ),
})