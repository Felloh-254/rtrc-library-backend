"""SQLAlchemy mappings for reservations and holds."""

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKeyConstraint, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import Patron


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "reservation_status IN ('Active', 'Fulfilled', 'Cancelled')",
            name="reservations_reservation_status_check",
        ),
        ForeignKeyConstraint(
            ["reservation_patron_id"],
            ["members.patrons.patron_id"],
            name="reservations_reservation_patron_id_fkey",
        ),
        ForeignKeyConstraint(
            ["reservation_book_id"],
            ["library.books.book_id"],
            name="reservations_reservation_book_id_fkey",
        ),
        {"schema": "circulation"},
    )

    id: Mapped[int] = mapped_column("reservation_id", Integer, primary_key=True)
    patron_id: Mapped[int] = mapped_column(
        "reservation_patron_id",
        Integer,
        nullable=False,
    )
    book_id: Mapped[int] = mapped_column(
        "reservation_book_id",
        Integer,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(
        "reservation_date",
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    status: Mapped[str | None] = mapped_column(
        "reservation_status",
        String(20),
        server_default=text("'Active'"),
    )

    patron: Mapped["Patron"] = relationship(back_populates="reservations")
    book: Mapped["Book"] = relationship(back_populates="reservations")


class Hold(Base):
    __tablename__ = "hold"
    __table_args__ = (
        CheckConstraint(
            "hold_status IN ('Active', 'Fulfilled', 'Cancelled')",
            name="hold_hold_status_check",
        ),
        ForeignKeyConstraint(
            ["hold_patron_id"],
            ["members.patrons.patron_id"],
            name="hold_hold_patron_id_fkey",
        ),
        ForeignKeyConstraint(
            ["hold_book_id"],
            ["library.books.book_id"],
            name="hold_hold_book_id_fkey",
        ),
        {"schema": "circulation"},
    )

    id: Mapped[int] = mapped_column("hold_id", Integer, primary_key=True)
    patron_id: Mapped[int] = mapped_column("hold_patron_id", Integer, nullable=False)
    book_id: Mapped[int] = mapped_column("hold_book_id", Integer, nullable=False)
    date: Mapped[date] = mapped_column(
        "hold_date",
        Date,
        nullable=False,
        server_default=text("CURRENT_DATE"),
    )
    status: Mapped[str | None] = mapped_column(
        "hold_status",
        String(20),
        server_default=text("'Active'"),
    )

    patron: Mapped["Patron"] = relationship(back_populates="holds")
    book: Mapped["Book"] = relationship(back_populates="holds")
