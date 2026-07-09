from django.urls import path
from .views.email_verification import VerifyEmailView


urlpatterns = [
    path('email-verify/', VerifyEmailView.as_view(), name='user_login'),
]
