from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/postgres"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    app_env: str = "development"
    cors_origins: str = ""
    cors_origin_regex: str = r"^https://[a-z0-9-]+\.vercel\.app$"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def allowed_cors_origins(self) -> list[str]:
        origins = list(self.cors_origins_list)
        if self.app_env.lower() in {"development", "dev", "local"}:
            origins.extend(
                [
                    "http://localhost:3000",
                    "http://localhost:5173",
                    "http://localhost:5500",
                    "http://localhost:5501",
                    "http://127.0.0.1:3000",
                    "http://127.0.0.1:5173",
                    "http://127.0.0.1:5500",
                    "http://127.0.0.1:5501",
                ]
            )
        return list(dict.fromkeys(origins))


@lru_cache
def get_settings() -> Settings:
    return Settings()
