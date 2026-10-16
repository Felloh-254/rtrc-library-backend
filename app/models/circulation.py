"""SQLAlchemy mappings for borrowing, fine, and book request records."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import Patron


class Borrowing(Base):
    __tablename__ = "borrowings"
    __table_args__ = (
        CheckConstraint(
            "borrowing_status IN ('Borrowed', 'Returned', 'Overdue')",
            name="borrowings_borrowing_status_check",
        ),
        ForeignKeyConstraint(
            ["borrowing_patron_id"],
            ["members.patrons.patron_id"],
            name="borrowings_borrowing_patron_id_fkey",
        ),
        ForeignKeyConstraint(
            ["borrowing_book_id"],
            ["library.books.book_id"],
            name="borrowings_borrowing_book_id_fkey",
        ),
        {"schema": "circulation"},
    )

    id: Mapped[int] = mapped_column("borrowing_id", Integer, primary_key=True)
    patron_id: Mapped[int] = mapped_column(
        "borrowing_patron_id",
        Integer,
        nullable=False,
    )
    book_id: Mapped[int] = mapped_column(
        "borrowing_book_id",
        Integer,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(
        "borrowing_date",
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    due_date: Mapped[date] = mapped_column("borrowing_due_date", Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(
        "borrowing_return_date",
        Date,
        nullable=True,
    )
    status: Mapped[str | None] = mapped_column(
        "borrowing_status",
        String(20),
        server_default=text("'Borrowed'"),
    )
    renewal_count: Mapped[int] = mapped_column(
        "borrowing_renewal_count",
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    patron: Mapped["Patron"] = relationship(back_populates="borrowings")
    book: Mapped["Book"] = relationship(back_populates="borrowings")
    renewals: Mapped[list["BorrowingRenewal"]] = relationship(
        back_populates="borrowing"
    )
    fines: Mapped[list["Fine"]] = relationship(back_populates="borrowing")


class BorrowingRenewal(Base):
    __tablename__ = "borrowing_renewals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["borrowing_id"],
            ["circulation.borrowings.borrowing_id"],
            name="borrowing_renewals_borrowing_id_fkey",
        ),
        {"schema": "circulation"},
    )

    id: Mapped[int] = mapped_column("renewal_id", Integer, primary_key=True)
    borrowing_id: Mapped[int | None] = mapped_column("borrowing_id", Integer)
    renewed_at: Mapped[datetime | None] = mapped_column(
        "renewed_at",
        DateTime(timezone=False),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    old_due_date: Mapped[date | None] = mapped_column("old_due_date", Date)
    new_due_date: Mapped[date | None] = mapped_column("new_due_date", Date)

    borrowing: Mapped[Borrowing | None] = relationship(back_populates="renewals")


class Fine(Base):
    __tablename__ = "fines"
    __table_args__ = (
        ForeignKeyConstraint(
            ["fine_borrowing_id"],
            ["circulation.borrowings.borrowing_id"],
            name="fines_fine_borrowing_id_fkey",
        ),
        {"schema": "circulation"},
    )

    id: Mapped[int] = mapped_column("fine_id", Integer, primary_key=True)
    borrowing_id: Mapped[int] = mapped_column(
        "fine_borrowing_id",
        Integer,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        "fine_amount",
        Numeric(10, 2),
        nullable=False,
    )
    paid: Mapped[bool | None] = mapped_column(
        "fine_paid",
        Boolean,
        server_default=text("FALSE"),
    )

    borrowing: Mapped[Borrowing] = relationship(back_populates="fines")


class Request(Base):
    __tablename__ = "requests"
    __table_args__ = (
        CheckConstraint(
            "request_status IN ('Active', 'Approved', 'Fulfilled', 'Cancelled')",
            name="chk_request_status",
        ),
        CheckConstraint(
            "request_status IN ('Active', 'Fulfilled', 'Cancelled')",
            name="requests_request_status_check",
        ),
        ForeignKeyConstraint(
            ["request_patron_id"],
            ["members.patrons.patron_id"],
            name="requests_request_patron_id_fkey",
        ),
        ForeignKeyConstraint(
            ["request_book_id"],
            ["library.books.book_id"],
            name="requests_request_book_id_fkey",
        ),
        {"schema": "circulation"},
    )

    id: Mapped[int] = mapped_column("request_id", Integer, primary_key=True)
    patron_id: Mapped[int] = mapped_column(
        "request_patron_id",
        Integer,
        nullable=False,
    )
    book_id: Mapped[int] = mapped_column("request_book_id", Integer, nullable=False)
    date: Mapped[date] = mapped_column(
        "request_date",
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    status: Mapped[str | None] = mapped_column(
        "request_status",
        String(20),
        server_default=text("'Active'"),
    )

    patron: Mapped["Patron"] = relationship(back_populates="requests")
    book: Mapped["Book"] = relationship(back_populates="requests")
