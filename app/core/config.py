from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # Application
    SECRET_KEY: str
    UPLOAD_FOLDER: str = "uploads"
    SESSION_LIFETIME_MINUTES: int = 30

    # Google Books API
    GOOGLE_BOOKS_API_KEY: str | None = None
    GOOGLE_BOOKS_API_URL: str = ("https://www.googleapis.com/books/v1/volumes")

    # Gutenberg API
    GUTENBERG_API_URL: str = "https://gutendex.com/books"
    GUTENBERG_EBOOK_COVER_URL_TEMPLATE: str = ("https://www.gutenberg.org/cache/epub/{id}/pg{id}.cover.medium.jpg")
    GUTENBERG_EBOOK_DOWNLOAD_URL_TEMPLATE: str | None = None

    # Mail
    MAIL_SERVER: str | None = None
    MAIL_PORT: int = 587
    MAIL_USE_TLS: bool = True
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None

    # MongoDB
    MONGO_URI: str | None = None
    MONGO_USER: str | None = None
    MONGO_PASS: str | None = None
    MONGO_CLUSTER: str | None = None
    MONGO_DB: str | None = None
    MONGO_SERVER_SELECTION_TIMEOUT_MS: int = 5000

    # PostgreSQL
    POSTGRES_DB: str | None = None
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None

    DATABASE_URL: str | None = None

    # Connection pool
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES: int = 3600

    @field_validator(
        "MONGO_URI",
        "MONGO_USER",
        "MONGO_PASS",
        "MONGO_CLUSTER",
        "MONGO_DB",
    )
    @classmethod
    def normalize_mongo_settings(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return value.strip()

    @model_validator(mode="after")
    def validate_database_configuration(self) -> "Settings":
        postgres_fields = (
            self.POSTGRES_DB,
            self.POSTGRES_HOST,
            self.POSTGRES_USER,
            self.POSTGRES_PASSWORD,
        )
        if not self.DATABASE_URL and any(value is None for value in postgres_fields):
            raise ValueError(
                "Configure DATABASE_URL or all of POSTGRES_DB, POSTGRES_HOST, "
                "POSTGRES_USER, and POSTGRES_PASSWORD."
            )

        mongo_fields = (
            self.MONGO_URI,
            self.MONGO_USER,
            self.MONGO_PASS,
            self.MONGO_CLUSTER,
            self.MONGO_DB,
        )
        if any(value is not None for value in mongo_fields):
            if self.MONGO_DB is None:
                raise ValueError("MONGO_DB is required when MongoDB is configured.")
            if self.MONGO_URI and self.MONGO_CLUSTER:
                raise ValueError(
                    "Configure either MONGO_URI or MONGO_CLUSTER, not both."
                )
            if self.MONGO_URI and (
                self.MONGO_USER is not None or self.MONGO_PASS is not None
            ):
                raise ValueError(
                    "Put MongoDB credentials in MONGO_URI or use MONGO_CLUSTER "
                    "with MONGO_USER and MONGO_PASS."
                )
            if not self.MONGO_URI and not self.MONGO_CLUSTER:
                raise ValueError("Configure MONGO_URI or MONGO_CLUSTER for MongoDB.")
            if (self.MONGO_USER is None) != (self.MONGO_PASS is None):
                raise ValueError("Configure both MONGO_USER and MONGO_PASS, or neither.")

        if self.MONGO_SERVER_SELECTION_TIMEOUT_MS < 1:
            raise ValueError(
                "MONGO_SERVER_SELECTION_TIMEOUT_MS must be greater than zero."
            )
        return self

    @property
    def mongodb_configured(self) -> bool:
        return self.MONGO_URI is not None or self.MONGO_CLUSTER is not None

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL

        if (
            self.POSTGRES_DB is None
            or self.POSTGRES_HOST is None
            or self.POSTGRES_USER is None
            or self.POSTGRES_PASSWORD is None
        ):
            raise ValueError("Database connection settings are incomplete.")

        return URL.create(
            "postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()