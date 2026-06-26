import asyncio
import logging
from datetime import datetime, timezone, timedelta
from .store import state_store
from .config import settings
from .broadcast import broadcast_telemetry_update, broadcast_hosts_update
from .db import get_reporting_data, get_top_hosts

logger = logging.getLogger(__name__)

async def reporting_worker_task():
    """Runs every 1s to aggregate DB metrics, check timeouts, and push to WebSockets."""
    logger.info("Reporting worker started.")
    while True:
        try:
            await asyncio.sleep(settings.reporting_interval_sec)
            now = datetime.now(timezone.utc)
            
            metrics, last_seen_map = await get_reporting_data()
            channels = await state_store.get_all_channels()
            
            for ch in channels:
                last_seen = last_seen_map.get(ch.channel_id)
                if last_seen:
                    time_since_activity = now - last_seen
                    is_active = (
                        time_since_activity.total_seconds() * 1000
                        <= settings.activity_timeout_ms
                    )
                else:
                    is_active = False

                # Update in-memory state for REST API consistency
                await state_store.set_channel_active(ch.channel_id, is_active)
                
                ch_metrics = metrics.get(ch.channel_id, {0: 0, 1: 0})
                packets_in = ch_metrics.get(0, 0)
                packets_out = ch_metrics.get(1, 0)
                dropped = await state_store.get_and_reset_dropped_batches(ch.channel_id)
                
                await broadcast_telemetry_update(
                    channel_id=ch.channel_id,
                    is_active=is_active,
                    packets_in=packets_in,
                    packets_out=packets_out,
                    dropped_batches=dropped,
                    received_at=now,
                    window_sec=settings.reporting_window_sec,
                )
                
                for target in ["lan_hosts", "wan_hosts"]:
                    # Skip DB query if zero subscribers
                    subscribers = await state_store.get_subscribers_by_target(ch.channel_id, target)
                    if not subscribers:
                        continue
                        
                    # Group subscribers by their sort/limit params to minimize DB queries
                    query_groups = {}
                    for sub in subscribers:
                        params = sub.subscriptions.get(target, {})
                        key = (params.get("sort_by", "sent"), params.get("limit", 5))
                        if key not in query_groups:
                            query_groups[key] = []
                        query_groups[key].append(sub)
                        
                    for (sort_by, limit), subs in query_groups.items():
                        # Query TimescaleDB
                        hosts = await get_top_hosts(
                            channel_id=ch.channel_id, target=target,
                            sort_by=sort_by, limit=limit,
                            window_sec=settings.reporting_window_sec
                        )
                        
                        # Use the centralized broadcast method
                        await broadcast_hosts_update(
                            channel_id=ch.channel_id,
                            target=target,
                            hosts=hosts,
                            sessions=subs
                        )

        except asyncio.CancelledError:
            logger.info("Reporting worker cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in reporting worker: {e}")
            await asyncio.sleep(5.0)

async def background_timeout_and_gc_task():
    """Runs periodically to garbage collect inactive channels with no listeners."""
    logger.info("Background GC task started.")
    while True:
        try:
            await asyncio.sleep(1.0)
            now = datetime.now(timezone.utc)
            retention_td = timedelta(milliseconds=settings.channel_retention_ms)
            channels = await state_store.get_all_channels()
            for ch in channels:
                if not ch.is_active:
                    time_since_activity = now - ch.last_activity_timestamp
                    if time_since_activity > retention_td:
                        listeners = await state_store.get_listeners(ch.channel_id)
                        if not listeners:
                            logger.info(
                                f"Channel {ch.channel_id} eligible for GC. Removing."
                            )
                            await state_store.remove_channel(ch.channel_id)
        except asyncio.CancelledError:
            logger.info("Background GC task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in background GC task: {e}")
            await asyncio.sleep(5.0)