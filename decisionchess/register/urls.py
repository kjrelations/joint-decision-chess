# urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("", views.register, name='register'),
    path("validate/<str:uidb64>/<str:token>/", views.activate_account, name='activate_account'),
    path("account-activation/", views.account_activated, name="account_activated"),
    path("activation-failed/", views.activation_failed, name="activation_failed"),
]