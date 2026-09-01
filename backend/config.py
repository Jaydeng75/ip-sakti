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
    public_api_url: str = "http://localhost:8000"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    ocr_enabled: bool = True
    malware_scan_enabled: bool = False
    clamav_host: str = "clamav"
    clamav_port: int = 3310
    clamav_timeout_seconds: float = 15.0
    demo_mode: bool = False
    registration_enabled: bool = True
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    corpus_version: str = "2026-09-01.official-registry.8"
    embedding_provider: str = "deterministic"
    embedding_url: str = "http://localhost:8081/v1"
    embedding_api_key: str | None = None
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_revision: str = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    embedding_dimensions: int = 384
    embedding_timeout_seconds: float = 60.0
    embedding_allow_fallback: bool = True
    retrieval_prefetch_limit: int = 40
    retrieval_lexical_weight: float = 0.45
    retrieval_semantic_weight: float = 0.55
    retrieval_minimum_lexical_score: float = 0.05
    retrieval_minimum_rerank_score: float = 0.05
    reranker_provider: str = "heuristic"
    reranker_url: str | None = None
    reranker_api_key: str | None = None
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_revision: str = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    reranker_timeout_seconds: float = 60.0
    reranker_allow_fallback: bool = True
    source_monitor_timeout_seconds: float = 15.0
    source_monitor_max_bytes: int = 5 * 1024 * 1024
    external_research_enabled: bool = False
    external_research_timeout_seconds: float = 20.0
    external_research_max_results: int = 5
    ncbi_api_key: str | None = None
    ncbi_contact_email: str | None = None
    patent_search_provider: str = "auto"
    google_cloud_project: str | None = None
    bigquery_location: str = "US"
    bigquery_maximum_bytes_billed: int = 100_000_000_000
    epo_ops_consumer_key: str | None = None
    epo_ops_consumer_secret: str | None = None
    otel_enabled: bool = False
    otel_service_name: str = "ip-sakti-api"
    otel_exporter_endpoint: str | None = None
    translation_enabled: bool = False
    translation_url: str = "http://localhost:8100"
    translation_service_token: str | None = None
    translation_timeout_seconds: float = 120.0
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    trusted_hosts: str = "localhost,127.0.0.1,testserver"

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

    @property
    def hosts(self) -> list[str]:
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
