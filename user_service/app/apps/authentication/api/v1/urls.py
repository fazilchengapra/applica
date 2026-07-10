from django.urls import path

from .views.email.email_verification import VerifyEmailView
from .views.email.email_login import EmailLoginView
from .views.toekn_refresh import CookieTokenRefreshView
from .views.logout import LogoutAPIView
from .views.phone.phone_send_otp import RequestPhoneOTPView
from .views.phone.verify_phone_otp import VerifyPhoneOTPView
from .views.phone.request_login_otp import RequestLoginOTPView
from .views.phone.verify_login_otp import VerifyLoginOTPView

urlpatterns = [
    path("email/verify/", VerifyEmailView.as_view()),
    path("email/login/", EmailLoginView.as_view()),
    path("token/refresh/", CookieTokenRefreshView.as_view()),
    path("logout/", LogoutAPIView.as_view()),

    # phone
    path("phone/otp/request/", RequestPhoneOTPView.as_view()),
    path("phone/otp/verify/", VerifyPhoneOTPView.as_view()),

    path('phone/login/request/', RequestLoginOTPView.as_view()),
    path('phone/login/verify/', VerifyLoginOTPView.as_view())
]
