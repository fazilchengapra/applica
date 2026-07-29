from http.cookies import SimpleCookie

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication


class JWTAuthMiddleware(BaseMiddleware):

    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])

        cookie = SimpleCookie()
        cookie.load(headers.get(b"cookie", b"").decode())

        token = cookie.get("access_token")

        if token:
            scope["user"] = await self.get_user_from_token(token.value)
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, raw_token):
        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(raw_token)
            return jwt_auth.get_user(validated_token)
        except Exception:
            return AnonymousUser()