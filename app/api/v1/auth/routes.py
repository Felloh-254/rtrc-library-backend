"""Login, account provisioning, and current-user routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_admin, get_current_user, get_db
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import Token, UserCreate, UserRead
from app.services.auth import (
    DuplicateMembershipNumberError,
    InvalidCredentialsError,
    authenticate_user,
    create_account,
)


router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_response(user: User) -> UserRead:
    if user.patron is None or user.role is None:
        raise RuntimeError("Authentication account is missing its patron or role.")
    return UserRead(
        id=user.id,
        membership_number=user.patron.membership_number,
        name=user.patron.name,
        role=user.role.name,
    )


@router.post("/login", response_model=Token)
def login(
    credentials: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    try:
        user = authenticate_user(db, credentials.username, credentials.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect membership number or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return _user_response(current_user)


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    account: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
) -> UserRead:
    if (
        account.role == "admin"
        and (current_user.role is None or current_user.role.name != "superadmin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a superadmin can create admin accounts.",
        )

    try:
        user = create_account(db, account, account.role)
    except DuplicateMembershipNumberError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That membership number is already in use.",
        ) from None
    return _user_response(user)