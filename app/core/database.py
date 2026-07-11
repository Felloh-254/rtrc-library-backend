from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,

    pool_size=settings.DB_POOL_SIZE,

    max_overflow=settings.DB_MAX_OVERFLOW,

    pool_timeout=settings.DB_POOL_TIMEOUT,

    pool_recycle=settings.DB_POOL_RECYCLE,

    pool_pre_ping=True,

    future=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()