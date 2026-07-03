# ==============================================================================
# CnSS Base Subscription Handler
# Abstract base class defining the contract for all subscription target handlers.
# Every concrete handler must implement the `execute` method to provide safe,
# parameterized SQL queries against TimescaleDB.
#
# The handler pattern isolates target-specific SQL logic from the Poller,
# enabling clean separation of concerns and easy addition of new targets.
# ==============================================================================

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import asyncpg

from core.contracts.subscriptions import SubscribeRequest

# --- Module Logger ---
logger = logging.getLogger(__name__)


# --- Abstract Handler Contract ---
class BaseSubscriptionHandler(ABC):
    """
    Abstract base class for subscription-specific SQL handlers.

    Defines the interface that all concrete handlers must implement.
    The Poller invokes `execute()` for each active subscription, passing
    the database pool and the validated subscription request.
    """

    @property
    @abstractmethod
    def target_name(self) -> str:
        """
        Returns the target identifier this handler is responsible for.
        Used for logging and registry validation.
        """
        pass

    @abstractmethod
    async def execute(self, db_pool: asyncpg.Pool, request: SubscribeRequest) -> Optional[Dict[str, Any]]:
        """
        Executes the target-specific SQL query and returns the formatted result.

        Implementations MUST:
        - Use parameterized queries ($1, $2, ...) for all user-controlled VALUES.
        - Apply strict whitelisting for SQL identifiers (ORDER BY columns).
        - Never interpolate raw user input into SQL strings.

        :param db_pool: The asyncpg connection pool for TimescaleDB.
        :param request: The validated subscription request containing target and params.
        :return: A dictionary containing the aggregated data, or None if no data.
        :raises DatabaseError: On query execution failures.
        """
        pass

    def _validate_request(self, request: SubscribeRequest) -> None:
        """
        Performs common validation shared across all handlers.
        Concrete handlers may override this to add target-specific checks.

        :param request: The subscription request to validate.
        :raises ValueError: If required fields are missing or invalid.
        """
        # Ensure the request targets this handler's domain
        if request.target != self.target_name:
            logger.warning(
                f"Handler '{self.target_name}' received request for " f"mismatched target '{request.target}'."
            )
            raise ValueError(f"Target mismatch: expected '{self.target_name}', " f"got '{request.target}'.")

        # Ensure channel_id is present (required for all subscriptions)
        if not request.channel_id:
            logger.warning(f"Empty channel_id in request for target '{self.target_name}'.")
            raise ValueError("channel_id is required for subscription.")

        logger.debug(f"Request validation passed for target '{self.target_name}' " f"(channel: {request.channel_id}).")
