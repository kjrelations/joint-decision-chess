# urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("", views.register, name='register'),
    path("validate/<str:uidtoken>/<str:token>/", views.activate_account, name='activate_account'),
    path("account-activation/", views.account_activated, name="account_activated"),
    path("activation-failed/", views.activation_failed, name="activation_failed"),
    path('passwd/', views.password_reset_request, name='password_reset_page'),
    path('pass_reset/<str:uidtoken>/<token>/', views.reset_pass, name='reset_request'),
    path('reset_done/', views.reset_done, name='reset_done'),
]