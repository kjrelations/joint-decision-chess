# urls.py
from django.urls import path
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

from . import views

urlpatterns = [
    path("", views.register, name='register'),
    path("validate/<str:uidtoken>/<str:token>/", views.activate_account, name='activate_account'),
    path("account-activation/", views.account_activated, name="account_activated"),
    path("activation-failed/", views.activation_failed, name="activation_failed"),
    path('password_reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]