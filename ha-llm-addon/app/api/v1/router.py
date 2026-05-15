"""API v1 router — aggregates all endpoint routers."""
from fastapi import APIRouter

from app.api.v1.endpoints.conversation import router as conversation_router
from app.api.v1.endpoints.health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(conversation_router, tags=["conversation"])
