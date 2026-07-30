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
    path("api/v1/profiles/", include("app.apps.profiles.api.v1.urls")),
    # drf api docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("admin/", admin.site.urls),
]
