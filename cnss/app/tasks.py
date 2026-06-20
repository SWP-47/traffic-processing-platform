import asyncio
import logging
from datetime import datetime, timezone, timedelta
from .store import state_store
from .config import settings
from .broadcast import broadcast_telemetry_update

logger = logging.getLogger(__name__)


async def background_timeout_and_gc_task():
    logger.info("Background timeout and GC task started.")
    while True:
        try:
            await asyncio.sleep(1.0)  # Check every 1 second
            now = datetime.now(timezone.utc)

            timeout_td = timedelta(milliseconds=settings.activity_timeout_ms)
            retention_td = timedelta(milliseconds=settings.channel_retention_ms)

            channels = await state_store.get_all_channels()

            for ch in channels:
                time_since_activity = now - ch.last_activity_timestamp

                # Timeout detection (Per-channel, isolated)
                if ch.is_active and time_since_activity > timeout_td:
                    logger.info(f"Channel {ch.channel_id} timed out. Marking inactive.")
                    await state_store.set_channel_inactive(ch.channel_id)

                    # Push update to listeners
                    await broadcast_telemetry_update(ch.channel_id, is_active=False)

                # Garbage collection
                elif not ch.is_active and time_since_activity > retention_td:
                    listeners = await state_store.get_listeners(ch.channel_id)
                    if not listeners:
                        logger.info(
                            f"Channel {ch.channel_id} eligible for GC. Removing."
                        )
                        await state_store.remove_channel(ch.channel_id)

        except asyncio.CancelledError:
            logger.info("Background task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in background task: {e}")
            await asyncio.sleep(5.0)  # Backoff on unexpected errors
