import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from pymongo.errors import PyMongoError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import router as api_router
from app.core.config import settings
from app.core.database import engine
from app.core.mongo import connect_mongodb

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    upload_path = Path(settings.UPLOAD_FOLDER)
    upload_path.mkdir(parents=True, exist_ok=True)

    logger.info("RTRC Library API starting up")

    mongo_client = None
    try:
        mongo_client, mongo_database = connect_mongodb()
        app.state.mongo_client = mongo_client
        app.state.mongo_database = mongo_database
        yield
    finally:
        if mongo_client is not None:
            mongo_client.close()
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
    def health_database(request: Request):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            logger.exception("Database health check failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PostgreSQL service is currently unavailable.",
            ) from None

        mongo_database = getattr(request.app.state, "mongo_database", None)
        if mongo_database is None:
            return {
                "status": "healthy",
                "postgresql": "healthy",
                "mongodb": "not_configured",
            }

        try:
            mongo_database.command("ping")
        except PyMongoError:
            logger.exception("MongoDB health check failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MongoDB service is currently unavailable.",
            ) from None

        return {
            "status": "healthy",
            "postgresql": "healthy",
            "mongodb": "healthy",
        }

    app.include_router(api_router)

    return app


app = create_app()