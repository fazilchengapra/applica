from django.urls import path
from .views.get_profile import GetProfileView
from .views.update_profile import UpdateProfileView

urlpatterns = [
    path("me/", GetProfileView.as_view()),
    path("", UpdateProfileView.as_view()),
]
