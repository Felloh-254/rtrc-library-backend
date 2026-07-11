from fastapi import FastAPI
from sqlalchemy import text

from app.core.database import engine

app = FastAPI()


@app.get("/")
def home():
    return {"message": "RTRC Library API"}


@app.get("/health/database")
def health_database():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "healthy"
    }