"""SQLAlchemy mappings for library books and DDC classifications."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.circulation import Borrowing, Request
    from app.models.reservation import Hold, Reservation


class DDCClassification(Base):
    __tablename__ = "ddc_classifications"
    __table_args__ = {"schema": "library"}

    code: Mapped[str] = mapped_column("ddc_code", String(20), primary_key=True)
    description: Mapped[str] = mapped_column("ddc_description", Text, nullable=False)

    books: Mapped[list["Book"]] = relationship(back_populates="classification")


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint(
            "book_acquisition_method IN ('Purchase', 'Donation', 'Exchange')",
            name="books_acquisition_method_check",
        ),
        CheckConstraint(
            "book_status IN ('Available', 'Issued', 'Reserved', 'Lost')",
            name="books_status_check",
        ),
        ForeignKeyConstraint(
            ["book_ddc_code"],
            ["library.ddc_classifications.ddc_code"],
            name="fk_books_ddc",
        ),
        {"schema": "library"},
    )

    id: Mapped[int] = mapped_column("book_id", Integer, primary_key=True)
    account_number: Mapped[str] = mapped_column(
        "book_account_number",
        String(20),
        nullable=False,
    )
    isbn: Mapped[str] = mapped_column("book_isbn", String(20), nullable=False)
    title: Mapped[str] = mapped_column("book_title", String(255), nullable=False)
    authors: Mapped[list[str]] = mapped_column(
        "book_author",
        ARRAY(Text),
        nullable=False,
    )
    genre: Mapped[str | None] = mapped_column("book_genre", String(255))
    language: Mapped[str | None] = mapped_column("book_language", String(50))
    publisher: Mapped[str | None] = mapped_column("book_publisher", String(255))
    publication_year: Mapped[str | None] = mapped_column(
        "book_publication_year",
        String(20),
    )
    acquisition_method: Mapped[str | None] = mapped_column(
        "book_acquisition_method",
        String(50),
    )
    shelf_location: Mapped[str | None] = mapped_column(
        "book_shelf_location",
        String(100),
    )
    condition: Mapped[str | None] = mapped_column("book_condition", String(50))
    status: Mapped[str | None] = mapped_column(
        "book_status",
        String(50),
        server_default=text("'Available'"),
    )
    acquisition_date: Mapped[datetime | None] = mapped_column(
        "book_acquisition_date",
        DateTime(timezone=False),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updation_date: Mapped[datetime | None] = mapped_column(
        "book_updation_date",
        DateTime(timezone=False),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    ddc_code: Mapped[str | None] = mapped_column("book_ddc_code", String(20))

    classification: Mapped[DDCClassification | None] = relationship(
        back_populates="books"
    )
    borrowings: Mapped[list["Borrowing"]] = relationship(back_populates="book")
    requests: Mapped[list["Request"]] = relationship(back_populates="book")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="book")
    holds: Mapped[list["Hold"]] = relationship(back_populates="book")
