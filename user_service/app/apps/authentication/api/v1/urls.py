from django.urls import path

from .views.email.email_verification import VerifyEmailView
from .views.email.email_login import EmailLoginView
from .views.toekn_refresh import CookieTokenRefreshView
from .views.logout import LogoutAPIView
from .views.phone.phone_send_otp import RequestPhoneOTPView
from .views.phone.verify_phone_otp import VerifyPhoneOTPView
from .views.phone.request_login_otp import RequestLoginOTPView
from .views.phone.verify_login_otp import VerifyLoginOTPView
from .views.phone.request_phone_change import RequestPhoneChangeView
from .views.phone.verify_phone_change import VerifyPhoneChangeView
from .views.password.forgot_password import ForgotPasswordView
from .views.password.reset_password import ResetPasswordView
from .views.password.change_password import ChangePasswordView
from .views.email.email_verify_req import RequestEmailVerificationView
from .views.email.email_change_req import EmailChangeRequestView
from .views.email.email_change_confirm import EmailChangeConfirmView
from .views.oauth.oauth_view import GoogleAuthView
from .views.phone.add_phone import AddPhoneView

urlpatterns = [
    # email
    path("email/verify/request/", RequestEmailVerificationView.as_view()),
    path("email/verify/", VerifyEmailView.as_view()),
    path("email/login/", EmailLoginView.as_view()),
    path("email/change/request/", EmailChangeRequestView.as_view()),
    path("email/change/confirm/", EmailChangeConfirmView.as_view()),
    # password
    path("password/forgot/", ForgotPasswordView.as_view()),
    path("password/reset/", ResetPasswordView.as_view()),
    path("password/change/", ChangePasswordView.as_view()),
    # phone
    path("phone/add/", AddPhoneView.as_view()),
    path("phone/otp/request/", RequestPhoneOTPView.as_view()),
    path("phone/otp/verify/", VerifyPhoneOTPView.as_view()),
    path("phone/login/request/", RequestLoginOTPView.as_view()),
    path("phone/login/verify/", VerifyLoginOTPView.as_view()),
    path("phone/change/request/", RequestPhoneChangeView.as_view()),
    path("phone/change/verify/", VerifyPhoneChangeView.as_view()),
    # Google OAuth
    path("google/", GoogleAuthView.as_view()),
    # common
    path("token/refresh/", CookieTokenRefreshView.as_view()),
    path("logout/", LogoutAPIView.as_view()),
]
