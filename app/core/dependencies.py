"""FastAPI dependencies shared by routes and feature modules."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import ROLE_ADMIN, ROLE_SUPERADMIN
from app.core.database import get_db
from app.core.security import decode_access_token, oauth2_scheme
from app.models.user import User
from app.repositories.users import get_user_by_id


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = get_user_by_id(db, user_id)
    if user is None or user.role is None or user.patron is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    def role_dependency(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role is None or current_user.role.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return role_dependency


get_current_admin = require_roles(ROLE_ADMIN, ROLE_SUPERADMIN)
get_current_superadmin = require_roles(ROLE_SUPERADMIN)

__all__ = [
    "get_current_admin",
    "get_current_superadmin",
    "get_current_user",
    "get_db",
    "require_roles",
]
