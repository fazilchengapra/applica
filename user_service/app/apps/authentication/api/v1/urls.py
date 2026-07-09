from django.urls import path

from .views.email_verification import VerifyEmailView
from .views.email_login import EmailLoginView
from .views.toekn_refresh import CookieTokenRefreshView
from .views.logout import LogoutAPIView

urlpatterns = [
    path('email/verify/', VerifyEmailView.as_view()),
    path('email/login/',EmailLoginView.as_view()),
    path('token/refresh/',CookieTokenRefreshView.as_view()),
    path('logout/', LogoutAPIView.as_view())
]