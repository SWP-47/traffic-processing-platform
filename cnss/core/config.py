# ==============================================================================
# CnSS Configuration Module
# Centralized, typed configuration management using Pydantic Settings.
# Loads environment variables from .env file or system environment.
# ==============================================================================

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    Validates types and provides default values for local development.
    """

    # --- Network & Ingestion ---
    # Port for the UDP Listener to receive TelemetryBatch payloads
    cnss_udp_port: int = Field(default=5140, alias="CnSS_UDP_PORT")
    # Maximum Transmission Unit constraint for UDP payloads (must be < 1400 bytes)
    cnss_udp_mtu: int = Field(default=1400, alias="CnSS_UDP_MTU")
    # Threshold for detecting abnormal backward jumps in sequence numbers (CN reboot/reset)
    sequence_reset_threshold: int = Field(default=1_000_000, alias="SEQUENCE_RESET_THRESHOLD")

    # --- Redis Configuration ---
    # Connection URL for the ephemeral Redis instance (no persistence)
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    # Maximum length of the Redis capped list for UDP buffering (prevents OOM if DB flusher lags)
    redis_udp_buffer_max_len: int = Field(default=100_000, alias="REDIS_UDP_BUFFER_MAX_LEN")

    # --- Database Configuration (TimescaleDB) ---
    # Async connection URL for PostgreSQL/TimescaleDB
    database_url: str = Field(default="postgresql+asyncpg://cnss:cnss@timescaledb:5432/cnss", alias="DATABASE_URL")

    # --- Security & JWT ---
    # Secret key for signing JWT tokens (HS256). MUST be changed in production!
    jwt_secret_key: str = Field(default="change-this-to-a-secure-random-string-in-production", alias="JWT_SECRET_KEY")
    # JWT signing algorithm
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    # Token expiration time in hours (default 24h)
    jwt_expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS")

    # --- Logging ---
    # Global log level for all microservices (DEBUG, INFO, WARNING, ERROR)
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")

    # --- Service Hosts & Ports (Local Development) ---
    # Host for local microservices binding
    cnss_host: str = Field(default="0.0.0.0", alias="CnSS_HOST")

    # Port for the REST API and WebSocket services.
    # FastAPI natively handles both HTTP and WS on the same port (matching legacy design).
    # External routing (wss:// and https://) is handled by the Nginx reverse proxy.
    cnss_http_port: int = Field(default=8000, alias="CnSS_HTTP_PORT")

    # --- Timeouts & Intervals ---
    # Channel inactivity timeout in milliseconds (used for REST/WS fallback status)
    activity_timeout_ms: int = Field(default=5000, alias="ACTIVITY_TIMEOUT_MS")
    # Default window for real-time telemetry aggregation in seconds
    reporting_window_sec: float = Field(default=5.0, alias="REPORTING_WINDOW_SEC")
    # Interval in seconds for the Background Flusher to push Redis buffers to TimescaleDB
    flush_interval_sec: float = Field(default=1.0, alias="FLUSH_INTERVAL_SEC")
    # Interval in seconds for the Ghost Cleaner to scan and remove stale subscription listeners
    ghost_cleanup_interval_sec: float = Field(default=5.0, alias="GHOST_CLEANUP_INTERVAL_SEC")
    # Interval in seconds for the Reporting Worker's Drop Flusher to sync drops and state to TimescaleDB
    reporting_flush_interval_sec: float = Field(default=1.0, alias="REPORTING_FLUSH_INTERVAL_SEC")
    # Interval in seconds for the Reporting Worker's Timeout Enforcer to mark inactive channels
    reporting_enforcement_interval_sec: float = Field(default=1.0, alias="REPORTING_ENFORCEMENT_INTERVAL_SEC")

    # Pydantic V2 configuration for environment variables
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # --- Data Retention ---
    # Number of days to retain raw packet_flows data in TimescaleDB.
    # Older data is automatically dropped by the retention policy.
    retention_days: int = Field(default=7, alias="RETENTION_DAYS")


# Global singleton instance of settings to be imported across the application
settings = Settings()
