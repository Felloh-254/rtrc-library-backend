"""Convenient imports for application-wide FastAPI dependencies."""

from app.core.dependencies import (
    get_current_admin,
    get_current_superadmin,
    get_current_user,
    get_db,
    get_mongo_db,
    require_roles,
)

__all__ = [
    "get_current_admin",
    "get_current_superadmin",
    "get_current_user",
    "get_db",
    "get_mongo_db",
    "require_roles",
]
