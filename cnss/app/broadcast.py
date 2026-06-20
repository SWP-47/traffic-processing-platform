# app/broadcast.py
import logging
from datetime import datetime, timezone
from .store import state_store
from .models import TelemetryBatch

logger = logging.getLogger(__name__)

async def broadcast_telemetry_update(
    channel_id: str, 
    is_active: bool, 
    batch: TelemetryBatch = None, 
    dropped_batches: int = 0, 
    received_at: datetime = None
):
    listeners = await state_store.get_listeners(channel_id)
    if not listeners:
        return

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    if batch:
        window_sec = batch.window_ms / 1000.0 if batch.window_ms > 0 else 1.0
        payload = {
            "type": "telemetry_update",
            "channel_id": channel_id,
            "is_active": is_active,
            "window_ms": batch.window_ms,
            "dropped_batches": dropped_batches,
            "metrics": {
                "direction_out": {
                    "packets_per_sec": batch.direction_out.packets / window_sec,
                    "packets": batch.direction_out.packets
                },
                "direction_in": {
                    "packets_per_sec": batch.direction_in.packets / window_sec,
                    "packets": batch.direction_in.packets
                }
            },
            "timestamp": batch.timestamp.isoformat().replace("+00:00", "Z"),
            "received_at": received_at.isoformat().replace("+00:00", "Z") if received_at else now_iso
        }
    else:
        payload = {
            "type": "telemetry_update",
            "channel_id": channel_id,
            "is_active": False,
            "window_ms": 0,
            "dropped_batches": 0,
            "metrics": {
                "direction_out": {"packets_per_sec": 0.0, "packets": 0},
                "direction_in": {"packets_per_sec": 0.0, "packets": 0}
            },
            "timestamp": now_iso,
            "received_at": now_iso
        }

    dead_listeners = []
    for ws in listeners:
        try:
            await ws.send_json(payload)
        except Exception:
            dead_listeners.append(ws)
            
    for ws in dead_listeners:
        await state_store.remove_listener(channel_id, ws)