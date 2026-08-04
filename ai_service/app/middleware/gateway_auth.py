import os

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class GatewayAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        expected_secret = os.getenv("GATEWAY_INTERNAL_SECRET")


        gateway_secret = request.headers.get("X-Gateway-Secret")
        
        print(expected_secret)

        if gateway_secret != expected_secret:
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden"},
            )

        return await call_next(request)