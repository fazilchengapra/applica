from django.urls import path


from .views.email_verification import VerifyEmailView
from .views.email_login import EmailLoginView

urlpatterns = [
    path('email/verify/', VerifyEmailView.as_view(), name='user_login'),
    path('email/login/',EmailLoginView.as_view())
]
