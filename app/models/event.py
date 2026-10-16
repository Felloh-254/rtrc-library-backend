"""SQLAlchemy mappings for news, events, and event photos."""

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKeyConstraint,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class News(Base):
    __tablename__ = "news"
    __table_args__ = (
        CheckConstraint(
            "news_status IN ('Draft', 'Published')",
            name="news_news_status_check",
        ),
        {"schema": "content"},
    )

    id: Mapped[int] = mapped_column("news_id", primary_key=True)
    title: Mapped[str] = mapped_column("news_title", Text, nullable=False)
    category: Mapped[str | None] = mapped_column(
        "news_category",
        String(100),
        server_default=text("'Announcements'"),
    )
    content: Mapped[str] = mapped_column("news_content", Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column("news_excerpt", Text)
    author: Mapped[str | None] = mapped_column(
        "news_author",
        String(100),
        server_default=text("'Library Team'"),
    )
    status: Mapped[str | None] = mapped_column(
        "news_status",
        String(20),
        server_default=text("'Draft'"),
    )
    featured: Mapped[bool | None] = mapped_column(
        "news_featured",
        Boolean,
        server_default=text("FALSE"),
    )
    image_url: Mapped[str | None] = mapped_column("news_image_url", Text)
    created_at: Mapped[datetime | None] = mapped_column(
        "news_created_at",
        DateTime(timezone=False),
        server_default=text("CURRENT_TIMESTAMP"),
    )
    published_at: Mapped[date | None] = mapped_column("news_published_at", Date)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = {"schema": "content"}

    id: Mapped[int] = mapped_column("event_id", primary_key=True)
    title: Mapped[str] = mapped_column("event_title", String(100), nullable=False)
    description: Mapped[str] = mapped_column(
        "event_description",
        Text,
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column("event_start_date", Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column("event_end_date", Date)
    start_time: Mapped[time] = mapped_column(
        "event_start_time",
        Time(timezone=False),
        nullable=False,
    )
    end_time: Mapped[time | None] = mapped_column(
        "event_end_time",
        Time(timezone=False),
    )
    venue: Mapped[str | None] = mapped_column("event_venue", String(50))
    image: Mapped[str | None] = mapped_column("event_image", Text)
    status: Mapped[str] = mapped_column(
        "event_status",
        String(50),
        nullable=False,
        server_default=text("'Draft'"),
    )
    registration_required: Mapped[bool] = mapped_column(
        "event_registration_required",
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )
    category: Mapped[str | None] = mapped_column("event_category", String(255))

    photos: Mapped[list["EventPhoto"]] = relationship(back_populates="event")


class EventPhoto(Base):
    __tablename__ = "event_photos"
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id"],
            ["content.events.event_id"],
            name="event_photos_event_id_fkey",
            ondelete="CASCADE",
        ),
        {"schema": "content"},
    )

    id: Mapped[int] = mapped_column("photo_id", primary_key=True)
    event_id: Mapped[int] = mapped_column("event_id", nullable=False)
    photo_url: Mapped[str] = mapped_column("photo_url", Text, nullable=False)

    event: Mapped[Event] = relationship(back_populates="photos")
