from fastapi import APIRouter

from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.simulations import router as simulations_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(simulations_router)
