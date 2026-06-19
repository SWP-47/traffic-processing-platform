from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from .udp_server import start_udp_server
from .store import state_store
from .config import settings
from .models import LoginRequest
from .auth import authenticate_user, create_access_token

logging.basicConfig(
    level=settings.log_level.upper(),  # .upper() ensures "debug" becomes "DEBUG"
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

udp_transport = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global udp_transport
    logger.info(f"Starting CnSS on {settings.cnss_host}:{settings.cnss_http_port}")
    logger.info(f"Opening UDP Telemetry Listener on port {settings.cnss_udp_port}")

    udp_transport = await start_udp_server(
        host=settings.cnss_host, port=settings.cnss_udp_port
    )
    yield

    if udp_transport:
        udp_transport.close()
        logger.info("UDP Telemetry Listener stopped.")


app = FastAPI(
    title="CnSS MVP v1",
    description="Control and Status Server",
    version="1.0.0",
    lifespan=lifespan,
)

@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    # Check for missing fields manually to return exact 400 format
    if not request.username or not request.password:
        return JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": "Fields 'username' and 'password' are required."
            }
        )
    
    # Validate credentials
    user = authenticate_user(request.username, request.password)
    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "error": "invalid_credentials",
                "message": "Invalid username or password."
            }
        )
    
    role = user["role"]
    scope = user["scope"]
    
    # System Documentation requirement: Admin scope contains all known channels
    if role == "admin":
        channels = await state_store.get_all_channels()
        scope = [c.channel_id for c in channels]
        
    # Generate JWT and return response
    token, expires_in, issued_at = create_access_token(
        username=request.username,
        role=role,
        scope=scope
    )
    
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "issued_at": issued_at,
        "role": role,
        "scope": scope
    }

@app.get("/health")
async def health_check():
    channels = await state_store.get_all_channels()
    active_count = sum(1 for c in channels if c.is_active)
    return {
        "status": "healthy",
        "components": {"cnss": "active"},
        "channels_active": active_count,
        "channels_total": len(channels),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
