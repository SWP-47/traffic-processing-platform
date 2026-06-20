from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # HTTP API Server
    cnss_host: str = "0.0.0.0"
    cnss_http_port: int = 8000

    # UDP Ingestion (CN to CnSS)
    cnss_udp_port: int = 5140

    # WebSocket Server (CnSS to MUI)
    cnss_ws_port: int = 8443

    # Security & JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_seconds: int = 86400

    # Logging Configuration
    log_level: str = "INFO"  # Default to INFO for safety

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
