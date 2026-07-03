# ==============================================================================
# CnSS Subscription Handlers Package
# Central registry for all subscription target handlers.
# Each handler is responsible for generating safe, parameterized SQL queries
# for a specific subscription target (e.g., 'telemetry', 'hosts_table').
#
# To add a new subscription target:
#   1. Create a new module (e.g., 'new_target_handler.py') in this package.
#   2. Implement a class inheriting from BaseSubscriptionHandler.
#   3. Register it in the HANDLER_REGISTRY dictionary below.
# The Poller will automatically pick it up via the registry.
# ==============================================================================

# --- Base Class Import ---
# Re-exported for convenient access by handler implementations and tests.
from services.reporting.handlers.base import BaseSubscriptionHandler

# --- Handler Imports ---
# Each handler implements target-specific SQL logic for the Reporting Worker.
# Handlers are instantiated as singletons in the registry to avoid repeated
# object creation during the 1Hz polling loop.
from services.reporting.handlers.host_details_handler import HostDetailsHandler
from services.reporting.handlers.host_top_destinations_handler import HostTopDestinationsHandler
from services.reporting.handlers.host_top_ports_handler import HostTopPortsHandler
from services.reporting.handlers.hosts_table_handler import HostsTableHandler
from services.reporting.handlers.telemetry_handler import TelemetryHandler

# --- Handler Registry ---
# Maps target names (from SubscribeRequest.target) to their handler instances.
# This dictionary is the single source of truth for target routing in the Poller.
# Adding a new target requires only appending a new entry here.
#
# Target names MUST match the 'target' field values defined in the API specification:
#   - "telemetry": Real-time channel packet rates (packets_in/out per second).
#   - "hosts_table": Aggregated table of all observed hosts with pagination.
#   - "host_details": Real-time Rx/Tx rate for a specific host IP.
#   - "host_top_destinations": Top remote IPs for a specific host.
#   - "host_top_ports": Top remote ports and protocols for a specific host.
HANDLER_REGISTRY: dict[str, BaseSubscriptionHandler] = {
    "telemetry": TelemetryHandler(),
    "hosts_table": HostsTableHandler(),
    "host_details": HostDetailsHandler(),
    "host_top_destinations": HostTopDestinationsHandler(),
    "host_top_ports": HostTopPortsHandler(),
}


# --- Public API ---
# Re-export the base class, registry, and all handler classes for convenient imports.
# This allows external modules (e.g., Poller, tests) to import from a single location.
__all__ = [
    "BaseSubscriptionHandler",
    "HANDLER_REGISTRY",
    "TelemetryHandler",
    "HostsTableHandler",
    "HostDetailsHandler",
    "HostTopDestinationsHandler",
    "HostTopPortsHandler",
]
