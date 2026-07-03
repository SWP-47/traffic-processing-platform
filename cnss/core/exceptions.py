# ==============================================================================
# CnSS Exception Hierarchy
# Centralized custom exceptions divided into two primary branches:
# ClientResponseError: Maps directly to HTTP status codes and WebSocket close frames.
# ServerInternalError: Represents infrastructure failures or unexpected backend states.
# ==============================================================================

from typing import Optional


# --- Root Exception ---
class CnSSBaseError(Exception):
    """Root exception for all application-specific errors."""

    pass


# --- Client-Facing Response Errors ---
# Used for errors that must be translated into HTTP responses
# or WebSocket close frames for the MUI client.
class ClientResponseError(CnSSBaseError):
    """
    Base class for errors that map to client-facing status codes.
    Carries HTTP status, machine-readable error code, human message,
    and optional WebSocket close code for unified routing.
    """

    def __init__(self, status_code: int, error_code: str, message: str, ws_close_code: Optional[int] = None):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.ws_close_code = ws_close_code
        super().__init__(message)


# --- Authentication Errors (HTTP 401 / WS 4001) ---
class AuthError(ClientResponseError):
    """Base class for authentication and identity failures."""

    def __init__(self, message: str = "Invalid username or password."):
        super().__init__(status_code=401, error_code="unauthorized", message=message, ws_close_code=4001)


class InvalidCredentialsError(AuthError):
    """Raised when username or password is incorrect during login."""

    pass


class TokenExpiredError(AuthError):
    """Raised when a JWT has exceeded its 'exp' claim."""

    def __init__(self, message: str = "Token has expired."):
        super().__init__(message=message)


class TokenRevokedError(AuthError):
    """Raised when a structurally valid JWT is found in the 'jwt:revoked' Redis set."""

    def __init__(self, message: str = "Token has been revoked."):
        super().__init__(message=message)


# --- Authorization Errors (HTTP 403 / WS 4003) ---
class AuthorizationError(ClientResponseError):
    """Raised when an authenticated user lacks the required scope for a channel."""

    def __init__(self, message: str = "You do not have access to this channel."):
        super().__init__(status_code=403, error_code="forbidden", message=message, ws_close_code=4003)


# --- Validation Errors (HTTP 400) ---
class ValidationError(ClientResponseError):
    """Base class for invalid input data or business logic violations."""

    def __init__(self, error_code: str = "bad_request", message: str = "Invalid request parameters."):
        super().__init__(status_code=400, error_code=error_code, message=message)


# --- Resource Errors (HTTP 404 / WS 4004) ---
class ResourceNotFoundError(ClientResponseError):
    """Raised when a requested entity does not exist in the database."""

    def __init__(self, message: str = "Resource not found."):
        super().__init__(status_code=404, error_code="not_found", message=message, ws_close_code=4004)


# --- Server-Side Internal Errors ---
# Used for infrastructure failures, DB/Redis issues, or unexpected states.
# These typically map to HTTP 5xx and do not expose internal details to the client.
class ServerInternalError(CnSSBaseError):
    """Base exception for infrastructure or unexpected backend failures."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class DatabaseError(ServerInternalError):
    """Raised on TimescaleDB query, connection, or transaction failures."""

    def __init__(self, message: str = "Database operation failed."):
        super().__init__(message=message)


class RedisError(ServerInternalError):
    """Raised on Redis connection, buffer, or Lua script execution failures."""

    def __init__(self, message: str = "Cache or state synchronization failed."):
        super().__init__(message=message)


class ConfigurationError(ServerInternalError):
    """Raised when required environment variables or settings are invalid."""

    def __init__(self, message: str = "Invalid application configuration."):
        super().__init__(message=message)

class InvalidCredentialsError(AuthError):
    """Raised when username or password is incorrect during login."""
    def __init__(self, message: str = "Invalid username or password."):
        super().__init__(message=message)
        # Override the default 'unauthorized' error code from AuthError
        # to match the specific API specification (api.md §6).
        self.error_code = "invalid_credentials"

# --- Health Check Errors (HTTP 503) ---
class UnhealthyError(ClientResponseError):
    """Raised when the /health endpoint detects a degraded or failed component."""
    def __init__(self, message: str = "Service is currently unhealthy."):
        super().__init__(status_code=503, error_code="unhealthy", message=message)