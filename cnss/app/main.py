from fastapi import FastAPI
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging

from .udp_server import start_udp_server
from .store import state_store
from .config import settings

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
