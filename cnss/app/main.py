from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from .udp_server import start_udp_server
from .store import state_store
from .config import settings
from .models import LoginRequest
from .auth import authenticate_user, create_access_token, get_current_user, TokenPayload

import asyncio

from fastapi import WebSocket, WebSocketDisconnect, Query
from .auth import get_ws_user
from .tasks import background_timeout_and_gc_task

logging.basicConfig(
    level=settings.log_level.upper(),
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

    bg_task = asyncio.create_task(background_timeout_and_gc_task())

    yield
    if udp_transport:
        udp_transport.close()
        logger.info("UDP Telemetry Listener stopped.")

    bg_task.cancel()
    try:
        await bg_task
    except asyncio.CancelledError:
        pass

    if udp_transport:
        udp_transport.close()


app = FastAPI(
    title="CnSS MVP v1",
    description="Control and Status Server",
    version="1.0.0",
    lifespan=lifespan,
)


# GLOBAL ERROR HANDLER


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Intercepts HTTPException and formats the response according to the OpenAPI spec:
    {"error": "<code>", "message": "<text>"}
    """
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


# ENDPOINTS


@app.post("/api/v1/auth/login")
async def login(request: LoginRequest):
    # AC 3: Check for missing required fields
    if not request.username or not request.password:
        return JSONResponse(
            status_code=400,
            content={
                "error": "bad_request",
                "message": "Fields 'username' and 'password' are required.",
            },
        )

    # Validate credentials against the mock user store
    user = authenticate_user(request.username, request.password)
    if not user:
        return JSONResponse(
            status_code=401,
            content={
                "error": "invalid_credentials",
                "message": "Invalid username or password.",
            },
        )

    role = user["role"]

    # Calculate final scope (intersection of permitted and physically existing channels)
    existing_channels = await state_store.get_all_channels()
    existing_channel_ids = {ch.channel_id for ch in existing_channels}

    if role == "admin":
        # Admin gets access to all currently known channels
        final_scope = list(existing_channel_ids)
    else:
        # Viewer gets only the intersection of their configured scope and existing channels
        configured_scope = set(user.get("scope", []))
        final_scope = list(existing_channel_ids.intersection(configured_scope))

    # Generate JWT token with the computed scope
    token, expires_in, issued_at = create_access_token(
        username=request.username, role=role, scope=final_scope
    )

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "issued_at": issued_at,
        "role": role,
        "scope": final_scope,
    }


@app.get("/api/v1/channels")
async def list_channels(user: TokenPayload = Depends(get_current_user)):
    """
    Returns a list of channels accessible to the authenticated user.
    Requires a valid JWT token in the Authorization header.
    """
    all_channels = await state_store.get_all_channels()

    # Filter channels according to the Authorization Matrix
    if user.role == "admin":
        # Admin sees all existing channels
        accessible_channels = all_channels
    else:
        # Viewer sees only channels present in their JWT scope
        accessible_channels = [ch for ch in all_channels if ch.channel_id in user.scope]

    # Format the response according to OpenAPI ChannelsResponse schema
    response_channels = [
        {
            "channel_id": ch.channel_id,
            "is_active": ch.is_active,
            "last_activity_timestamp": ch.last_activity_timestamp.isoformat().replace(
                "+00:00", "Z"
            ),
        }
        for ch in accessible_channels
    ]

    return {"channels": response_channels, "total": len(response_channels)}


@app.get("/api/v1/channel/{channel_id}/status")
async def get_channel_status(
    channel_id: str, user: TokenPayload = Depends(get_current_user)
):
    """
    REST fallback for a specific channel's activity indicator.
    """
    # Check if channel exists
    channel = await state_store.get_channel(channel_id)
    if not channel:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": "Channel not found."},
        )

    # Check Authorization Matrix (Viewer scope enforcement)
    if user.role != "admin" and channel_id not in user.scope:
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "message": "You do not have access to this channel.",
            },
        )

    return {
        "channel_id": channel.channel_id,
        "is_active": channel.is_active,
        "last_activity_timestamp": channel.last_activity_timestamp.isoformat().replace(
            "+00:00", "Z"
        ),
    }


@app.get("/api/v1/health")
async def health_check(user: TokenPayload = Depends(get_current_user)):
    """
    Verify operational status of the CnSS and aggregate channel statistics.
    """
    channels = await state_store.get_all_channels()
    active_count = sum(1 for c in channels if c.is_active)
    return {
        "status": "healthy",
        "components": {"cnss": "active"},
        "channels_active": active_count,
        "channels_total": len(channels),
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


@app.websocket("/api/v1/ws/telemetry")
async def websocket_telemetry(
    websocket: WebSocket, token: str = Query(None), channel_id: str = Query(None)
):
    # 1. Validate Query Parameters
    if not token:
        await websocket.close(code=4001, reason="invalid_token")
        return
    if not channel_id:
        await websocket.close(code=4002, reason="missing_channel")
        return

    # 2. Validate Token
    try:
        user = await get_ws_user(token)
    except HTTPException:
        await websocket.close(code=4001, reason="invalid_token")
        return

    # 3. Validate Scope
    if user.role != "admin" and channel_id not in user.scope:
        await websocket.close(code=4003, reason="channel_forbidden")
        return

    # 4. Validate Channel Existence
    channel = await state_store.get_channel(channel_id)
    if not channel:
        await websocket.close(code=4004, reason="channel_not_found")
        return

    # 5. Accept & Register Listener
    await websocket.accept()
    await state_store.add_listener(channel_id, websocket)

    try:
        while True:
            # Keep connection alive, handle basic ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        # Ensure listener is removed on disconnect (Memory Leak Prevention)
        await state_store.remove_listener(channel_id, websocket)
