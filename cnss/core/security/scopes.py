# ==============================================================================
# CnSS Scope and Authorization Module
# Enforces Role-Based Access Control (RBAC) by validating JWT scopes against
# requested channel identifiers. Ensures strict adherence to the authorization matrix.
# ==============================================================================

from core.contracts.auth import TokenPayload
from core.exceptions import AuthorizationError

# --- Scope Verification Logic ---


def verify_channel_access(payload: TokenPayload, channel_id: str) -> None:
    """
    Validates if the authenticated user has access to the specified channel.
    Raises AuthorizationError if the user lacks the required permissions.
    """
    # Admins bypass scope restrictions and have unrestricted access to all channels
    if payload.role == "admin":
        return

    # Viewers are strictly limited to the channel IDs explicitly granted in their scope
    if channel_id not in payload.scope:
        raise AuthorizationError(message=f"Access denied to channel '{channel_id}'.")
