import logging
from datetime import datetime, timezone
from .store import state_store

logger = logging.getLogger(__name__)


async def broadcast_telemetry_update(
    channel_id: str,
    is_active: bool,
    packets_in: int = 0,
    packets_out: int = 0,
    dropped_batches: int = 0,
    received_at: datetime = None,
    window_sec: float = 1.0,
):
    listeners = await state_store.get_listeners(channel_id)
    if not listeners:
        return

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    safe_window_sec = window_sec if window_sec > 0 else 1.0

    payload = {
        "type": "telemetry_update",
        "channel_id": channel_id,
        "is_active": is_active,
        "window_ms": int(safe_window_sec * 1000),
        "dropped_batches": dropped_batches,
        "metrics": {
            "direction_out": {
                "packets_per_sec": float(packets_out) / safe_window_sec,
                "packets": packets_out,
            },
            "direction_in": {
                "packets_per_sec": float(packets_in) / safe_window_sec,
                "packets": packets_in,
            },
        },
        "timestamp": (
            received_at.isoformat().replace("+00:00", "Z") if received_at else now_iso
        ),
        "received_at": (
            received_at.isoformat().replace("+00:00", "Z") if received_at else now_iso
        ),
    }

    dead_sessions = []
    # listeners is a Set[WSClientSession]
    for session in listeners:
        try:
            await session.websocket.send_json(payload)
        except Exception:
            dead_sessions.append(session)

    for session in dead_sessions:
        await state_store.remove_listener(channel_id, session)


async def broadcast_hosts_update(
    channel_id: str, target: str, hosts: list[dict], sessions: list
):
    """
    Sends a hosts_update payload to a specific list of WSClientSessions.
    Handles dead connections by removing them from the state store.
    """
    if not sessions:
        return

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "type": "hosts_update",
        "target": target,
        "channel_id": channel_id,
        "timestamp": now_iso,
        "hosts": hosts,
    }

    dead_sessions = []
    for session in sessions:
        try:
            await session.websocket.send_json(payload)
        except Exception:
            dead_sessions.append(session)

    for session in dead_sessions:
        # The websocket is dead, remove it from the channel's listeners entirely
        await state_store.remove_listener(channel_id, session)
