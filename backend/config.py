from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    app_name: str = "IP-SAKTI Intelligence API"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    secret_key: str = Field(default="change-me-in-production-at-least-32-characters")
    access_token_minutes: int = 60
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'ip_sakti.db'}"
    allowed_origins: str = "http://localhost:3000"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    demo_mode: bool = False
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    corpus_version: str = "2026-08-31.curated-mvp.1"
    translation_enabled: bool = False
    translation_url: str = "http://localhost:8100"
    translation_timeout_seconds: float = 120.0

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_prefix="IPSAKTI_",
        extra="ignore",
    )

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def production(self) -> bool:
        return self.environment.lower() == "production"


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
