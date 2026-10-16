"""Business logic for account creation and password authentication."""

from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import ROLE_SUPERADMIN
from app.core.security import hash_password, verify_password
from app.models.user import Patron, User
from app.repositories.users import (
    account_exists_by_membership_number,
    get_role_by_name,
    get_patron_by_membership_number,
    get_user_by_membership_number,
    has_superadmin,
)
from app.schemas.auth import UserCreate


class DuplicateMembershipNumberError(Exception):
    """Raised when an account is created with an existing membership number."""


class InvalidCredentialsError(Exception):
    """Raised when credentials do not identify an active account."""


class SuperadminAlreadyExistsError(Exception):
    """Raised when the one-time superadmin bootstrap has already been used."""


def authenticate_user(
    db: Session,
    membership_number: str,
    password: str,
) -> User:
    user = get_user_by_membership_number(db, membership_number)
    if (
        user is None
        or user.patron is None
        or not verify_password(password, user.patron.password_hash)
    ):
        raise InvalidCredentialsError

    user.last_login = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def create_account(
    db: Session,
    account: UserCreate,
    role_name: str,
) -> User:
    patron = get_patron_by_membership_number(db, account.membership_number)
    if patron is not None and patron.user is not None:
        raise DuplicateMembershipNumberError

    role = get_role_by_name(db, role_name)
    if role is None:
        raise RuntimeError(
            f"Database role {role_name!r} is missing; apply the database migrations."
        )

    password_hash = hash_password(account.password)
    if patron is None:
        patron = Patron(
            membership_number=account.membership_number,
            name=account.name,
            password_hash=password_hash,
            category_id=account.category_id,
        )
    else:
        patron.password_hash = password_hash

    user = User(patron=patron, role=role)
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        if account_exists_by_membership_number(db, account.membership_number):
            raise DuplicateMembershipNumberError from error
        raise

    db.refresh(user)
    return user


def bootstrap_superadmin(db: Session, account: UserCreate) -> User:
    if has_superadmin(db):
        raise SuperadminAlreadyExistsError
    return create_account(db, account, ROLE_SUPERADMIN)