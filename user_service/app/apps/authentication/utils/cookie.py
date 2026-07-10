from django.conf import settings

def set_access_cookie(response, *, access_token: str):
    response.set_cookie(
        key=settings.ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=15 * 60,
        path="/",
    )


def set_refresh_cookie(response, *, refresh_token: str):
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        max_age=7 * 24 * 60 * 60,
        path="/api/v1/auth/",
    )


def set_auth_cookies(response, *, access_token: str, refresh_token: str):
    """Used only at login, where both tokens are freshly issued."""
    set_access_cookie(response, access_token=access_token)
    set_refresh_cookie(response, refresh_token=refresh_token)


def clear_auth_cookies(response):
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE, path="/api/v1/auth/")