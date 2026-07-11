# ==============================================================================
# CnSS WebSocket Initial Snapshot Fetcher
# Executes read-only queries against TimescaleDB to provide the initial state
# for a newly subscribed client. This prevents the "cold start" gap where
# the client would otherwise wait for the next Pub/Sub update from the Reporting Worker.
# ==============================================================================

import logging
from typing import Any, Dict

from core.contracts.subscriptions import SubscribeRequest, SubscriptionParams
from core.database import get_db_pool
from core.exceptions import ResourceNotFoundError
from services.reporting.handlers import HANDLER_REGISTRY

# --- Module Logger ---
logger = logging.getLogger(__name__)


# --- Snapshot Fetcher Class ---
class SnapshotFetcher:
    """
    Executes target-specific SQL queries to generate the initial state snapshot.
    Uses the same concrete handlers as the Reporting Worker to ensure DRY query code.
    """

    async def fetch_snapshot(self, channel_id: str, target: str, params: SubscriptionParams) -> Dict[str, Any]:
        """
        Routes the snapshot request to the appropriate target-specific handler.

        :param channel_id: The channel identifier to query.
        :param target: The data stream type (e.g., 'telemetry', 'hosts_table').
        :param params: The subscription parameters (filters, limits, windows).
        :return: A dictionary containing the initial snapshot data.
        :raises ResourceNotFoundError: If the target type is not supported.
        """
        handler = HANDLER_REGISTRY.get(target)
        if not handler:
            logger.warning(f"Unsupported snapshot target: '{target}'")
            raise ResourceNotFoundError(message=f"Target '{target}' is not supported for snapshots.")

        request = SubscribeRequest(
            id="snapshot-placeholder",
            action="subscribe",
            channel_id=channel_id,
            target=target,
            params=params,
        )

        db_pool = get_db_pool()
        snapshot = await handler.execute(db_pool, request)
        if snapshot is None:
            return {}
        return snapshot
