"""Database queries for authentication users."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import Patron, Role, User


def get_user_by_membership_number(
    db: Session,
    membership_number: str,
) -> User | None:
    statement = (
        select(User)
        .join(User.patron)
        .options(joinedload(User.patron), joinedload(User.role))
        .where(
            Patron.membership_number == membership_number,
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        )
    )
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    statement = (
        select(User)
        .options(joinedload(User.patron), joinedload(User.role))
        .where(
            User.id == user_id,
            User.is_active.is_(True),
            User.is_deleted.is_(False),
        )
    )
    return db.scalar(statement)


def get_role_by_name(db: Session, role_name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == role_name))


def get_patron_by_membership_number(
    db: Session,
    membership_number: str,
) -> Patron | None:
    return db.scalar(
        select(Patron)
        .options(joinedload(Patron.user))
        .where(Patron.membership_number == membership_number)
    )


def account_exists_by_membership_number(
    db: Session,
    membership_number: str,
) -> bool:
    return db.scalar(
        select(User.id)
        .join(User.patron)
        .where(Patron.membership_number == membership_number)
        .limit(1)
    ) is not None


def has_superadmin(db: Session) -> bool:
    return db.scalar(
        select(User.id)
        .join(User.role)
        .where(Role.name == "superadmin", User.is_deleted.is_(False))
        .limit(1)
    ) is not None