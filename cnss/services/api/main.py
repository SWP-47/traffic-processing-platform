# ==============================================================================
# CnSS REST API Application Entry Point
# Initializes the FastAPI application, registers all route modules,
# configures global exception handlers for consistent error responses,
# and manages the lifecycle of shared infrastructure (Database pool, Redis client).
# ==============================================================================

# CRITICAL: Apply logging patch BEFORE any other imports
# to fix compatibility issues with passlib and uvicorn.
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

import core.logging_patch  # noqa: F401
from core.database import close_db_pool, init_db_pool
from core.exceptions import ClientResponseError, ServerInternalError
from core.logging import setup_logging
from core.redis.client import close_redis_client, init_redis_client
from services.api.routes import auth, channels, health, history

# --- Module Logger ---
logger = logging.getLogger(__name__)


# --- Application Lifespan Manager ---
# Handles initialization and teardown of shared infrastructure components.
# Ensures database pool and Redis client are properly initialized before
# the first request and gracefully closed during application shutdown.
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages the application lifecycle: startup initialization and shutdown cleanup.
    """
    # --- Startup Phase ---
    logger.info("Starting CnSS REST API service...")

    # Initialize logging configuration
    setup_logging()
    logger.info("Logging configured successfully.")

    # Initialize Redis client (required for token revocation checks and state caching)
    await init_redis_client()
    logger.info("Redis client initialized successfully.")

    # Initialize TimescaleDB connection pool (required for all database queries)
    await init_db_pool()
    logger.info("TimescaleDB connection pool initialized successfully.")

    logger.info("CnSS REST API service is fully operational.")

    # Yield control to the application (handles incoming requests)
    yield

    # --- Shutdown Phase ---
    logger.info("Shutting down CnSS REST API service...")

    # Close database pool gracefully
    await close_db_pool()
    logger.info("TimescaleDB connection pool closed.")

    # Close Redis client gracefully
    await close_redis_client()
    logger.info("Redis client closed.")

    logger.info("CnSS REST API service shutdown completed successfully.")


# --- FastAPI Application Instance ---
# Create the main application with lifespan manager and API metadata
app = FastAPI(
    title="CnSS REST API",
    description="Control and Status Server - HTTP gateway for authentication,"
    " channel discovery, and historical data retrieval",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc",  # ReDoc
    openapi_url="/api/openapi.json",
)

# --- Route Registration ---
# Include all route modules with their respective prefixes and tags
app.include_router(auth.router)
app.include_router(channels.router)
app.include_router(health.router)
app.include_router(history.router)

# --- Global Exception Handlers ---
# These handlers ensure all errors follow the consistent JSON response format
# defined in the API specification (api.md §6).


@app.exception_handler(ClientResponseError)
async def client_response_error_handler(request: Request, exc: ClientResponseError) -> JSONResponse:
    """
    Handles all client-facing errors (400, 401, 403, 404, 503).
    Returns a standardized JSON response with error code and message.
    """
    logger.warning(f"Client error: {exc.error_code} - {exc.message} " f"(Path: {request.url.path})")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(ServerInternalError)
async def server_internal_error_handler(request: Request, exc: ServerInternalError) -> JSONResponse:
    """
    Handles all server-side internal errors (500).
    Logs the full error details but returns a generic message to the client
    to prevent exposure of sensitive internal information.
    """
    logger.error(
        f"Internal server error: {exc.message} - {exc.details} " f"(Path: {request.url.path})",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected server error occurred.",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handles Pydantic validation errors (422 Unprocessable Entity).
    Formats the error details into our standard response schema.
    """
    logger.warning(f"Validation error: {exc.errors()} (Path: {request.url.path})")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed.",
            "details": exc.errors(),
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """
    Handles standard HTTP exceptions (e.g., 404 Not Found from FastAPI routing).
    Converts them to our standardized error response format.
    """
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail} " f"(Path: {request.url.path})")

    # Map common HTTP exceptions to our error codes
    error_code_map = {
        404: "not_found",
        405: "method_not_allowed",
        500: "internal_error",
    }

    error_code = error_code_map.get(exc.status_code, "http_error")

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code,
            "message": str(exc.detail),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any unhandled exceptions.
    Ensures the API never returns raw HTML error pages or stack traces.
    """
    logger.critical(
        f"Unhandled exception: {type(exc).__name__} - {str(exc)} " f"(Path: {request.url.path})",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected server error occurred.",
        },
    )


# --- Health Check Endpoint (Root) ---
# Simple endpoint to verify the API service is running (useful for Docker healthchecks)
@app.get("/", tags=["System"])
async def root() -> dict[str, str]:
    """
    Root endpoint for basic service availability check.
    """
    return {
        "service": "CnSS REST API",
        "status": "running",
        "version": "2.0.0",
    }


# --- Application Entry Point (for local development) ---
# Allows running the API directly with: python -m services.api.main
if __name__ == "__main__":
    import uvicorn

    from core.config import settings

    uvicorn.run(
        "services.api.main:app",
        host=settings.cnss_host,
        port=settings.cnss_http_port,
        reload=True,  # Enable hot-reload for development
        log_level=settings.log_level.lower(),
    )
