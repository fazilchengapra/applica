from django.urls import path
from .views import UserAuthView


urlpatterns = [
    path('login/', UserAuthView.as_view(), name='user_login'),
]
