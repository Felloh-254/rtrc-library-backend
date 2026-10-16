"""Version 1 API routes."""

from fastapi import APIRouter

from app.api.v1.auth.routes import router as auth_router


router = APIRouter()
router.include_router(auth_router)

__all__ = ["router"]