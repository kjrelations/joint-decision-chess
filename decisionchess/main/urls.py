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
    path('update_connected/', views.update_connected, name='update_connected'),
    path("news/", views.news, name="news"),
    path("profile/<str:username>/", views.profile, name="profile"),
    path("terms-of-service/", views.terms_of_service, name="terms"),
    path("privacy/", views.privacy_policy, name="privacy"),
    path("account/email", views.change_email, name="change_email"),
    path("account/confirm/<str:uidb64>/<str:token>/", views.confirm_email, name='activate_account'),
    path("account/passwd", views.change_password, name="change_password"),
    path("account/profile", views.edit_profile, name="edit_profile"),
]