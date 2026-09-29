"""Shared DRF permission for service-to-service (internal) endpoints.

Internal calls arrive through Kong, which verifies ``X-Internal-Secret`` with
the ``internal-secret-auth`` plugin before proxying. That plugin forwards the
original request headers, so the secret is still present at the backend and we
re-verify it here as defense in depth: a request that reached the container
without passing through Kong is rejected even if the network boundary is
somehow open.

All services share one secret, ``GATEWAY_INTERNAL_SECRET`` (templated into Kong
from ``kong/.env`` and mirrored into each service's env), so the BFF in
ai_service and this service agree on a single value.
"""

from hmac import compare_digest

from django.conf import settings
from rest_framework import permissions
INTERNAL_SECRET_HEADER = "HTTP_X_INTERNAL_SECRET"


class InternalSecretPermission(permissions.BasePermission):
    """Allow only callers presenting the shared internal secret.

    Uses a constant-time comparison so the check does not leak the secret's
    length or prefix through response timing. The expected value is read from
    Django settings (populated from ``GATEWAY_INTERNAL_SECRET``) rather than the
    environment directly, so tests can override it.
    """

    message = "Invalid internal secret"

    def has_permission(self, request, view) -> bool:
        expected = getattr(settings, "GATEWAY_INTERNAL_SECRET", None)
        provided = request.META.get(INTERNAL_SECRET_HEADER)

        if not expected or not provided:
            return False

        return compare_digest(provided, expected)
