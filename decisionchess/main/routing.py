# routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
    path('ws/games/', consumers.GameConsumer.as_asgi())
]