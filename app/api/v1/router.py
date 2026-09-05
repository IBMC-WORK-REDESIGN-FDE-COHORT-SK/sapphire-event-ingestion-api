"""
API v1 router
"""

from fastapi import APIRouter
from app.api.v1.endpoints import metrics, health

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(metrics.router, tags=["metrics"])
api_router.include_router(health.router, tags=["health"])

# Made with Bob
