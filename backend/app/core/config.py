from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "MINOVA"
    debug: bool = False
    api_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "postgresql+asyncpg://minova_app:minova_dev@localhost:5432/minova"
    database_sync_url: str = "postgresql://minova_app:minova_dev@localhost:5432/minova"
    db_echo: bool = False
    db_pool_size: int = 10
    db_max_overflow: int = 20

    keycloak_url: str = "http://localhost:8081"
    keycloak_realm: str = "minova"
    keycloak_client_id: str = "minova-api"
    keycloak_jwks_url: str = ""

    @property
    def effective_jwks_url(self) -> str:
        if self.keycloak_jwks_url:
            return self.keycloak_jwks_url
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    minio_bucket_documents: str = "documents"
    minio_bucket_attachments: str = "attachments"
    minio_bucket_exports: str = "exports"
    minio_bucket_reports: str = "reports"

    ollama_url: str = "http://localhost:11434"
    llm_model: str = "qwen3:8b"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "minova-main"

    open_meteo_base_url: str = "https://api.open-meteo.com/v1"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    log_level: str = "INFO"
    log_json: bool = False

    conflict_tolerance_pct: float = 0.5
    sla_default_hours: int = 24

    mine_timezone: str = "Asia/Kolkata"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
