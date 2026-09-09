from django.urls import path
from .views.register import UserView, AdminUserToggleView
from .views.me import MeView
from .views.user_overview import UserOverviewView

urlpatterns = [
    path("me/", MeView.as_view()),
    path("admin/<int:user_id>/overview/", UserOverviewView.as_view()),
    path("admin/<int:user_id>/toggle-active/", AdminUserToggleView.as_view()),
    path("", UserView.as_view()),
]
