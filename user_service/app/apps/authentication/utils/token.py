import hashlib
import secrets
from ..models.verification_token import VerificationToken
from django.utils import timezone

def generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()

def _get_valid_token(user, token_type):
    vt = (
        VerificationToken.objects.select_related("auth_method")
        .filter(user=user, type=token_type, used_at__isnull=True, revoked_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if vt is None or vt.expires_at < timezone.now():
        return None
    return vt