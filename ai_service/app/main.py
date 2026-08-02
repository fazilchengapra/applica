from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.v1.router import router as v1_router

# middleware
from app.middleware.gateway_auth import GatewayAuthMiddleware

load_dotenv()

app = FastAPI(title="ai_service", version="0.1.0")

app.add_middleware(GatewayAuthMiddleware)

app.include_router(v1_router, prefix="/api/ai/v1")
