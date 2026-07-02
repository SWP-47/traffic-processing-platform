# ==============================================================================
# CnSS Subscription Handlers Package
# Central registry for all subscription target handlers.
# Each handler is responsible for generating safe, parameterized SQL queries
# for a specific subscription target (e.g., 'telemetry', 'lan_hosts').
#
# To add a new subscription target:
#   1. Create a new module (e.g., 'new_target_handler.py') in this package.
#   2. Implement a class inheriting from BaseSubscriptionHandler.
#   3. Register it in the HANDLER_REGISTRY dictionary below.
# The Poller will automatically pick it up via the registry.
# ==============================================================================

from services.reporting.handlers.base import BaseSubscriptionHandler
from services.reporting.handlers.telemetry_handler import TelemetryHandler

# --- Handler Registry ---
# Maps target names (from SubscribeRequest.target) to their handler instances.
# This dictionary is the single source of truth for target routing in the Poller.
# Adding a new target requires only appending a new entry here.
HANDLER_REGISTRY: dict[str, BaseSubscriptionHandler] = {
    "telemetry": TelemetryHandler(),
    "lan_hosts": LanHostsHandler(),
}

# --- Public API ---
# Re-export the base class and registry for convenient imports.
__all__ = [
    "BaseSubscriptionHandler",
    "HANDLER_REGISTRY",
    "TelemetryHandler",
    "LanHostsHandler",
]