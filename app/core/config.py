import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _fix_db_url(url: str) -> tuple[str, str]:
    """Railway provides DATABASE_URL as postgresql://... — convert for asyncpg and Alembic."""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    async_url = url.replace("postgresql://", "postgresql+asyncpg://", 1) if "asyncpg" not in url else url
    sync_url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return async_url, sync_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_secret_key: str = "change_me"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://clinicuser:clinicpass@localhost:5432/clinic_db"
    database_url_sync: str = "postgresql://clinicuser:clinicpass@localhost:5432/clinic_db"

    def model_post_init(self, __context) -> None:
        # If Railway injects DATABASE_URL, use it and derive both variants
        raw = os.environ.get("DATABASE_URL", "")
        if raw and "asyncpg" not in raw:
            async_url, sync_url = _fix_db_url(raw)
            object.__setattr__(self, "database_url", async_url)
            object.__setattr__(self, "database_url_sync", sync_url)

    openai_api_key: str = ""

    meta_access_token: str = ""
    meta_phone_number_id: str = ""
    meta_verify_token: str = "my_verify_token"
    meta_webhook_base_url: str = "http://localhost:8000"
    meta_api_version: str = "v21.0"

    clinics_dir: str = "./clinics"

    @property
    def clinics_path(self) -> Path:
        return Path(self.clinics_dir)


settings = Settings()
