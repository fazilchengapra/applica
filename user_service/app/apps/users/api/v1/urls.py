from django.urls import path
from .views.register import UserView

urlpatterns = [
    path('', UserView.as_view(), name='user_create'),
]
