from fastapi import FastAPI

app = FastAPI(
    title="RTRC Library API",
    description="Backend API for RTRC Library Management System",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "RTRC Library API is running"
    }