"""SQLAlchemy mapping for application settings."""

from datetime import datetime

from sqlalchemy import DateTime, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"
    __table_args__ = {"schema": "public"}

    key: Mapped[str] = mapped_column("key", Text, primary_key=True)
    value: Mapped[str] = mapped_column("value", Text, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        "updated_at",
        DateTime(timezone=False),
        server_default=text("CURRENT_TIMESTAMP"),
    )
