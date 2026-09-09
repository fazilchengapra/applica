from django.urls import path
from .views.admin_profile import AdminProfileView
from .views.get_profile import GetProfileView
from .views.update_profile import UpdateProfileView

urlpatterns = [
    path("admin/<int:user_id>/", AdminProfileView.as_view()),
    path("me/", GetProfileView.as_view()),
    path("", UpdateProfileView.as_view()),
]
