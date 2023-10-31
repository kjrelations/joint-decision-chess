# urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name='home'),
    path("quick_pair/", views.quick_pair, name='quick_pair'),
    path("create_new_game/", views.create_new_game, name='create_new_game'),
    path('check_game_availability/', views.check_game_availability, name='available'),
    path('get_lobby_games/', views.get_lobby_games, name='get_lobby_games'),
    path('play/<uuid:game_uuid>/', views.play, name='join_new_game'),
    path('update_connected/', views.update_connected, name='update_connected')
]