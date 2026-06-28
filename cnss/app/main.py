from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import re
import logging
import json
from .db import get_channel_history, get_top_hosts, get_all_channel_ids_from_db
from .models import WSClientSession, WSControlMessage
from .broadcast import broadcast_hosts_update


from .udp_server import start_udp_server
from .store import state_store
from .config import settings
from .models import LoginRequest
from .auth import authenticate_user, create_access_token, get_current_user, TokenPayload

import asyncio

from fastapi import WebSocket, WebSocketDisconnect, Query
from .auth import get_ws_user
from .tasks import reporting_worker_task

from .db import (
    init_db_pool,
    close_db_pool,
    get_all_channels_from_db,
    get_channel_status_from_db,
    get_health_metrics_from_db,
    is_db_healthy,
)

from datetime import timedelta


class TokenMaskingFilter(logging.Filter):
    """Masks tokens in query parameters to prevent leakage in logs."""

    TOKEN_PATTERN = re.compile(r"([?&]token=)[^ &\s]+")

    def _mask_string(self, s: str) -> str:
        if isinstance(s, str):
            return self.TOKEN_PATTERN.sub(r"\1[REDACTED]", s)
        return s

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(self._mask_string(arg) for arg in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: self._mask_string(v) for k, v in record.args.items()}

        if isinstance(record.msg, str):
            record.msg = self._mask_string(record.msg)

        return True


# Apply filter to Uvicorn and App loggers
logging.getLogger("uvicorn.access").addFilter(TokenMaskingFilter())
logging.getLogger("uvicorn.error").addFilter(TokenMaskingFilter())
logging.getLogger("app").addFilter(TokenMaskingFilter())

# Basic logging config
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

    await init_db_pool()

    logger.info(f"Opening UDP Telemetry Listener on port {settings.cnss_udp_port}")
    udp_transport = await start_udp_server(
        host=settings.cnss_host, port=settings.cnss_udp_port
    )
    channels = await get_all_channel_ids_from_db()
    for channel_id in channels:
        await state_store.get_or_create_channel(channel_id)
    logger.info(f"Channels are loaded to state store")

    reporting_task = asyncio.create_task(reporting_worker_task())
    yield

    # Shutdown
    if udp_transport:
        udp_transport.close()
        logger.info("UDP Telemetry Listener stopped.")
    reporting_task.cancel()
    try:
        await reporting_task
    except asyncio.CancelledError:
        pass
    await close_db_pool()


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
    existing_channel_ids = set(await get_all_channel_ids_from_db())

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
    Queries TimescaleDB directly for channel existence and activity.
    """

    channels_data = await get_all_channels_from_db()

    # Filter channels according to the Authorization Matrix
    if user.role == "admin":
        accessible_channels = channels_data
    else:
        accessible_channels = [
            ch for ch in channels_data if ch["channel_id"] in user.scope
        ]

    now = datetime.now(timezone.utc)
    timeout_td = timedelta(milliseconds=settings.activity_timeout_ms)

    response_channels = []
    for ch in accessible_channels:
        last_activity = ch["last_activity_timestamp"]
        is_active = False
        if last_activity:
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            is_active = (now - last_activity) <= timeout_td

        response_channels.append(
            {
                "channel_id": ch["channel_id"],
                "is_active": is_active,
                "last_activity_timestamp": (
                    last_activity.isoformat().replace("+00:00", "Z")
                    if last_activity
                    else None
                ),
            }
        )

    return {"channels": response_channels, "total": len(response_channels)}


@app.get("/api/v1/channel/{channel_id}/status")
async def get_channel_status(
    channel_id: str, user: TokenPayload = Depends(get_current_user)
):
    """
    REST fallback for a specific channel's activity indicator.
    Queries TimescaleDB directly.
    """

    # Check Authorization Matrix (Viewer scope enforcement) BEFORE DB lookup
    if user.role != "admin" and channel_id not in user.scope:
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "message": "You do not have access to this channel.",
            },
        )

    channel_data = await get_channel_status_from_db(channel_id)
    if not channel_data:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": "Channel not found."},
        )

    now = datetime.now(timezone.utc)
    timeout_td = timedelta(milliseconds=settings.activity_timeout_ms)
    last_activity = channel_data["last_activity_timestamp"]

    is_active = False
    if last_activity:
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)
        is_active = (now - last_activity) <= timeout_td

    return {
        "channel_id": channel_id,
        "is_active": is_active,
        "last_activity_timestamp": (
            last_activity.isoformat().replace("+00:00", "Z") if last_activity else None
        ),
    }


@app.get("/api/v1/health")
async def health_check(user: TokenPayload = Depends(get_current_user)):
    """
    Verify operational status of the CnSS and aggregate channel statistics from DB.
    Returns 503 if the database is unreachable.
    """

    db_healthy = await is_db_healthy()
    metrics = await get_health_metrics_from_db()

    status = "healthy" if db_healthy else "unhealthy"
    cnss_status = "active" if db_healthy else "error"
    status_code = 200 if db_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "components": {"cnss": cnss_status},
            "channels_active": metrics["channels_active"],
            "channels_total": metrics["channels_total"],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        },
    )


@app.websocket("/api/v1/ws/telemetry")
async def websocket_telemetry(
    websocket: WebSocket, token: str = Query(None), channel_id: str = Query(None)
):
    # 1. Validate Query Parameters
    if not token:
        await websocket.accept()  # Accept first to allow WS close frame
        await websocket.close(code=4001, reason="invalid_token")
        return
    if not channel_id:
        await websocket.accept()
        await websocket.close(code=4002, reason="missing_channel")
        return

    # 2. Validate Token
    try:
        user = await get_ws_user(token)
    except HTTPException:
        await websocket.accept()
        await websocket.close(code=4001, reason="invalid_token")
        return

    # 3. Validate Scope
    if user.role != "admin" and channel_id not in user.scope:
        await websocket.accept()
        await websocket.close(code=4003, reason="channel_forbidden")
        return

    # 4. Validate Channel Existence
    channels = await get_all_channel_ids_from_db()
    if channel_id not in channels:
        await websocket.accept()
        await websocket.close(code=4004, reason="channel_not_found")
        return

    # 5. Accept & Register Listener
    await websocket.accept()

    # AC 1: Create WSClientSession
    session = WSClientSession(websocket=websocket, user=user, channel_id=channel_id)
    await state_store.add_listener(channel_id, session)

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue

            # Handle Control Messages
            try:
                msg_dict = json.loads(data)
                msg = WSControlMessage(**msg_dict)

                if msg.action == "subscribe" and msg.target in [
                    "lan_hosts",
                    "wan_hosts",
                ]:
                    # Update session subscriptions
                    session.subscriptions[msg.target] = {
                        "sort_by": msg.sort_by or "sent",
                        "limit": msg.limit or 5,
                    }

                    # Initial Snapshot (Query DB and send ONLY to this client)
                    sub_params = session.subscriptions[msg.target]
                    hosts = await get_top_hosts(
                        channel_id=channel_id,
                        target=msg.target,
                        sort_by=sub_params["sort_by"],
                        limit=sub_params["limit"],
                        window_sec=settings.reporting_window_sec,
                    )

                    await broadcast_hosts_update(
                        channel_id=channel_id,
                        target=msg.target,
                        hosts=hosts,
                        sessions=[session],
                    )

                elif msg.action == "unsubscribe" and msg.target in [
                    "lan_hosts",
                    "wan_hosts",
                ]:
                    # Remove subscription
                    session.subscriptions.pop(msg.target, None)

            except Exception as e:
                logger.warning(f"Invalid WS control message: {e}")

    except WebSocketDisconnect:
        pass
    finally:
        # Garbage Collection
        await state_store.remove_listener(channel_id, session)


@app.get("/api/v1/channel/{channel_id}/history")
async def get_channel_history_endpoint(
    channel_id: str, period: str, user: TokenPayload = Depends(get_current_user)
):
    # Auth & Scope check
    if user.role != "admin" and channel_id not in user.scope:
        return JSONResponse(
            status_code=403,
            content={
                "error": "forbidden",
                "message": "You do not have access to this channel.",
            },
        )

    channel_data = await get_channel_status_from_db(channel_id)
    if not channel_data:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": "Channel not found."},
        )

    if period not in ["1h", "24h", "7d", "30d"]:
        return JSONResponse(
            status_code=400,
            content={"error": "bad_request", "message": "Invalid period."},
        )

    interval_sec, points = await get_channel_history(channel_id, period)

    return {
        "channel_id": channel_id,
        "period": period,
        "interval_sec": interval_sec,
        "points": points,
    }
