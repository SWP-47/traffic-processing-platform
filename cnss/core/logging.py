# ==============================================================================
# CnSS Logging Configuration Module
# Centralized logging setup using dictConfig and custom security filters.
# ==============================================================================

import logging
import logging.config
import re
import sys

from core.config import settings


# --- Token Masking Filter ---
# Custom filter to sanitize sensitive data (JWT tokens) from log outputs.
class TokenMaskingFilter(logging.Filter):
    """
    Masks tokens in query parameters to prevent leakage in logs.
    Replaces '?token=...' or '&token=...' with '?token=[REDACTED]'.
    """

    # Regex to match token parameters in URLs or log messages
    TOKEN_PATTERN = re.compile(r"([?&]token=)[^ &\s]+")

    def _mask_string(self, s: str) -> str:
        """Applies regex substitution if the input is a string."""
        if isinstance(s, str):
            return self.TOKEN_PATTERN.sub(r"\1[REDACTED]", s)
        return s

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Intercepts log records and masks tokens in the message and its arguments.
        """
        # Mask the main log message
        if isinstance(record.msg, str):
            record.msg = self._mask_string(record.msg)

        # Mask formatting arguments if they exist
        if isinstance(record.args, tuple):
            record.args = tuple(self._mask_string(str(arg)) for arg in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: self._mask_string(str(v)) for k, v in record.args.items()}

        return True


# --- Logging Configuration Dictionary ---
# Standard Python dictConfig structure for centralized logging management.
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "token_masking": {
            "()": TokenMaskingFilter,
        }
    },
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "filters": ["token_masking"],
            "stream": sys.stdout,
        },
    },
    "loggers": {
        # Uvicorn access logs (HTTP/WS requests)
        "uvicorn.access": {
            "handlers": ["console"],
            "level": settings.log_level.upper(),
            "propagate": False,
        },
        # Uvicorn error logs
        "uvicorn.error": {
            "handlers": ["console"],
            "level": settings.log_level.upper(),
            "propagate": False,
        },
        # Application-specific logs (using 'cnss' as the base namespace)
        "cnss": {
            "handlers": ["console"],
            "level": settings.log_level.upper(),
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": settings.log_level.upper(),
    },
}


# --- Setup Function ---
def setup_logging() -> None:
    """
    Initializes the logging configuration for the application.
    Applies dictConfig and ensures the token masking filter is active.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
