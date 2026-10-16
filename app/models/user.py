"""SQLAlchemy mappings for roles and member accounts."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.circulation import Borrowing, Request
    from app.models.reservation import Hold, Reservation


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("role_name", name="roles_role_name_key"),
        {"schema": "public"},
    )

    id: Mapped[int] = mapped_column("role_id", Integer, primary_key=True)
    name: Mapped[str] = mapped_column("role_name", String(50), nullable=False)

    users: Mapped[list["User"]] = relationship(
        primaryjoin="Role.id == User.role_id",
        foreign_keys="User.role_id",
        back_populates="role",
    )


class PatronCategory(Base):
    __tablename__ = "patron_categories"
    __table_args__ = (
        CheckConstraint(
            "category_name IN ('Primary Student', 'Secondary Student', "
            "'TVET Student', 'Teacher', 'Community Member')",
            name="patron_categories_category_name_check",
        ),
        UniqueConstraint(
            "category_name",
            name="patron_categories_category_name_key",
        ),
        {"schema": "library"},
    )

    id: Mapped[int] = mapped_column("category_id", Integer, primary_key=True)
    name: Mapped[str] = mapped_column("category_name", String(50), nullable=False)

    patrons: Mapped[list["Patron"]] = relationship(back_populates="category")


class Patron(Base):
    __tablename__ = "patrons"
    __table_args__ = (
        CheckConstraint(
            "patron_gender IN ('Male', 'Female', 'Other')",
            name="patrons_gender_check",
        ),
        CheckConstraint(
            "patron_education_level IN ('Primary', 'Secondary', 'Tertiary', 'Other')",
            name="patrons_education_level_check",
        ),
        ForeignKeyConstraint(
            ["patron_category_id"],
            ["library.patron_categories.category_id"],
            name="patrons_patron_category_id_fkey",
        ),
        {"schema": "members"},
    )

    id: Mapped[int] = mapped_column("patron_id", Integer, primary_key=True)
    membership_number: Mapped[str] = mapped_column(
        "patron_membership_number",
        String(20),
        nullable=False,
    )
    name: Mapped[str] = mapped_column("patron_name", String(50), nullable=False)
    gender: Mapped[str | None] = mapped_column("patron_gender", String(10))
    date_of_birth: Mapped[date | None] = mapped_column("patron_date_of_birth", Date)
    education_level: Mapped[str | None] = mapped_column(
        "patron_education_level",
        String(50),
    )
    locality: Mapped[str | None] = mapped_column("patron_locality", Text)
    password_hash: Mapped[str | None] = mapped_column("patron_password", Text)
    category_id: Mapped[int | None] = mapped_column("patron_category_id", Integer)

    category: Mapped[PatronCategory | None] = relationship(back_populates="patrons")
    contacts: Mapped[list["PatronContact"]] = relationship(back_populates="patron")
    user: Mapped["User | None"] = relationship(back_populates="patron", uselist=False)
    borrowings: Mapped[list["Borrowing"]] = relationship(back_populates="patron")
    requests: Mapped[list["Request"]] = relationship(back_populates="patron")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="patron")
    holds: Mapped[list["Hold"]] = relationship(back_populates="patron")


class PatronContact(Base):
    __tablename__ = "patron_contacts"
    __table_args__ = (
        CheckConstraint(
            "contact_type IN ('Phone', 'Email', 'WhatsApp')",
            name="patron_contacts_contact_type_check",
        ),
        ForeignKeyConstraint(
            ["patron_id"],
            ["members.patrons.patron_id"],
            name="patron_contacts_patron_id_fkey",
            ondelete="CASCADE",
        ),
        {"schema": "members"},
    )

    id: Mapped[int] = mapped_column("contact_id", Integer, primary_key=True)
    patron_id: Mapped[int] = mapped_column("patron_id", Integer, nullable=False)
    contact_type: Mapped[str | None] = mapped_column("contact_type", String(20))
    contact_value: Mapped[str] = mapped_column("contact_value", Text, nullable=False)

    patron: Mapped[Patron] = relationship(back_populates="contacts")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "NOT (user_deleted = TRUE AND user_status = TRUE)",
            name="users_not_deleted_active_check",
        ),
        ForeignKeyConstraint(
            ["user_patron_id"],
            ["members.patrons.patron_id"],
            name="users_user_patron_id_fkey",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_role_id"],
            ["public.roles.role_id"],
            name="fk_user_role",
            onupdate="CASCADE",
        ),
        ForeignKeyConstraint(
            ["user_role_id"],
            ["public.roles.role_id"],
            name="users_user_role_id_fkey",
        ),
        UniqueConstraint("user_patron_id", name="users_user_patron_id_key"),
        {"schema": "members"},
    )

    id: Mapped[int] = mapped_column("user_id", Integer, primary_key=True)
    patron_id: Mapped[int | None] = mapped_column("user_patron_id", Integer)
    role_id: Mapped[int] = mapped_column(
        "user_role_id",
        Integer,
        nullable=False,
        server_default=text("2"),
    )
    date_joined: Mapped[date] = mapped_column(
        "user_date_joined",
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    is_active: Mapped[bool] = mapped_column(
        "user_status",
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    last_login: Mapped[datetime | None] = mapped_column(
        "user_last_login",
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime | None] = mapped_column(
        "user_created_at",
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        "user_updated_at",
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    is_deleted: Mapped[bool] = mapped_column(
        "user_deleted",
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )

    patron: Mapped[Patron | None] = relationship(back_populates="user")
    role: Mapped[Role] = relationship(
        primaryjoin="User.role_id == Role.id",
        foreign_keys="User.role_id",
        back_populates="users",
    )
