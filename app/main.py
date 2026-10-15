import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import engine

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    upload_path = Path(settings.UPLOAD_FOLDER)
    upload_path.mkdir(parents=True, exist_ok=True)

    logger.info("RTRC Library API starting up")

    yield

    # Shutdown
    engine.dispose()
    logger.info("RTRC Library API shut down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="RTRC Library API",
        description="API for the RTRC Library Management System.",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/", tags=["General"])
    def home():
        return {"message": "RTRC Library API"}

    @app.get("/health/database", tags=["Health"])
    def health_database():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            return {"status": "healthy"}

        except SQLAlchemyError:
            logger.exception("Database health check failed")

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database service is currently unavailable.",
            )

    # Register feature routers here as they become available.

    return app


app = create_app()