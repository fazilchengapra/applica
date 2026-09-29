"""URL routes for internal (service-to-service) user endpoints.

Mounted at ``/internal/v1/users/`` rather than under ``/api/v1/users/`` on
purpose: Kong already has several overlapping routes on the ``/api/v1/users``
prefix (an admin-gated one among them), so giving internal endpoints their own
prefix keeps the gateway's longest-prefix matching unambiguous.
"""

from django.urls import path

from .views.home import InternalHomeView

urlpatterns = [
    path("home/<int:user_id>/", InternalHomeView.as_view()),
]
