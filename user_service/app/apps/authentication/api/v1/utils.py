import hashlib
import secrets
from django.conf import settings


def generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()

def set_auth_cookies(response, *, access_token: str, refresh_token: str):
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=15 * 60,  # match ACCESS_TOKEN_LIFETIME
        path="/",
    )
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=7 * 24 * 60 * 60,  # match REFRESH_TOKEN_LIFETIME
        path="/api/v1/auth/",  # scope refresh cookie to the auth endpoints only
    )


def clear_auth_cookies(response):
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE, path="/api/v1/auth/")