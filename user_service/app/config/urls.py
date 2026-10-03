from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # api version 1
    path("api/v1/auth/", include("app.apps.authentication.api.v1.urls")),
    path("api/v1/users/", include("app.apps.users.api.v1.urls")),
    # service-to-service only, guarded by the shared internal secret
    path("internal/v1/users/", include("app.apps.users.api.v1.internal_urls")),
    path("api/v1/profiles/", include("app.apps.profiles.api.v1.urls")),
    # In-app notifications (read + write) are served by notification_service
    # under /api/v1/notify, which owns the table. See apps/notifications/README.
    # drf api docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/admin/", admin.site.urls),
]
