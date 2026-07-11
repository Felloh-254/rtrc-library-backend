from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    DATABASE_URL: str

    DB_POOL_SIZE: int
    DB_MAX_OVERFLOW: int
    DB_POOL_TIMEOUT: int
    DB_POOL_RECYCLE: int

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()