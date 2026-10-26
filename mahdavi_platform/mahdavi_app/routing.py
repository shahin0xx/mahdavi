# mahdavi_app/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/live/(?P<stream_id>\w+)/$', consumers.LiveStreamConsumer.as_asgi()),
    re_path(r'ws/live/broadcast/(?P<stream_id>\w+)/$', consumers.LiveStreamBroadcastConsumer.as_asgi()),
]