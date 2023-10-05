# urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name='home'),
    path("home/", views.home, name='home'),
    path("play/", views.play, name="play"),
    path("news/", views.news, name="news"),
    path("profile/<str:username>/", views.profile, name="profile"),
    path("terms-of-service/", views.terms_of_service, name="terms"),
    path("privacy/", views.privacy_policy, name="privacy"),
    path("account/email", views.change_email, name="change_email"),
    path("account/confirm/<str:uidb64>/<str:token>/", views.confirm_email, name='activate_account'),
    path("account/passwd", views.change_password, name="change_password"),
    path("account/profile", views.edit_profile, name="edit_profile"),
]