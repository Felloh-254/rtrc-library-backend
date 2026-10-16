"""SQLAlchemy mapping for library ebooks."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Ebook(Base):
    __tablename__ = "ebooks"
    __table_args__ = (
        UniqueConstraint(
            "ebook_gutenberg_id",
            name="ebooks_ebook_gutenberg_id_key",
        ),
        {"schema": "library"},
    )

    id: Mapped[int] = mapped_column("ebook_id", Integer, primary_key=True)
    isbn: Mapped[str] = mapped_column("ebook_isbn", String(20), nullable=False)
    gutenberg_id: Mapped[int | None] = mapped_column("ebook_gutenberg_id", Integer)
    title: Mapped[str | None] = mapped_column("ebook_title", String(255))
    authors: Mapped[list[str] | None] = mapped_column("ebook_authors", ARRAY(Text))
    language: Mapped[str | None] = mapped_column("ebook_language", String(50))
    format: Mapped[str] = mapped_column("ebook_format", String(50), nullable=False)
    download_url: Mapped[str] = mapped_column("ebook_download_url", Text, nullable=False)
    download_count: Mapped[int | None] = mapped_column(
        "ebook_download_count",
        Integer,
        server_default=text("0"),
    )
    added_at: Mapped[datetime | None] = mapped_column(
        "ebook_added_at",
        DateTime(timezone=False),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    added_by: Mapped[str | None] = mapped_column("ebook_added_by", String(20))
    cover_url: Mapped[str | None] = mapped_column("ebook_cover_url", Text)
    subjects: Mapped[list[str] | None] = mapped_column("ebook_subjects", ARRAY(Text))
    copyright: Mapped[bool | None] = mapped_column("ebook_copyright", Boolean)
