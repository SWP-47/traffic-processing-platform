from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # HTTP API Server
    cnss_host: str = "0.0.0.0"
    cnss_http_port: int = 8000

    # UDP Ingestion (CN → CnSS)
    cnss_udp_port: int = 5140

    # TimescaleDB
    database_url: str = "postgresql://traffic:traffic@localhost:5432/traffic_db"
    database_pool_min_size: int = 2
    database_pool_max_size: int = 10

    # Security & JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 86400

    # Logging
    log_level: str = "INFO"

    # Telemetry Timeouts & Garbage Collection
    activity_timeout_ms: int = 5000
    channel_retention_ms: int = 86400000

    # Reporting Worker
    reporting_interval_sec: float = 1.0
    reporting_window_sec: float = 3.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
