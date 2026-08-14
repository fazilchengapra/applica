from django.urls import path, include
from .notify_dispatch import NotificationDispatchView

urlpatterns = [path("push/", NotificationDispatchView.as_view())]
