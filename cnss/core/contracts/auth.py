# ==============================================================================
# CnSS Authentication Contracts
# Pydantic models for validating and typing JWT payloads and auth-related data.
# ==============================================================================

from typing import List, Literal

from pydantic import BaseModel, Field


# --- JWT Payload Model ---
# Represents the decoded structure of a CnSS JWT.
# Enforces strict typing for role-based access control (RBAC).
class TokenPayload(BaseModel):
    """
    Decoded JWT payload structure.
    Validates claims and enforces the authorization matrix roles.
    """

    # User identifier (UUID as string)
    sub: str = Field(..., description="User ID (subject).")

    # Unique JWT ID for revocation tracking
    jti: str = Field(..., description="JWT ID for revocation.")

    # Timestamps (PyJWT returns these as integers)
    iat: int = Field(..., description="Issued at (UNIX timestamp).")
    exp: int = Field(..., description="Expiration time (UNIX timestamp).")

    # Role-Based Access Control (RBAC)
    # Strictly limited to 'admin' or 'viewer' as per architecture Section 5.1
    role: Literal["admin", "viewer"] = Field(..., description="User role.")

    # Channel scopes (ignored for admin, enforced for viewer)
    scope: List[str] = Field(default_factory=list, description="Allowed channel IDs.")

# --- Refresh Token Payload Model ---
# Represents the decoded structure of a long-lived Refresh JWT.
# Includes a 'type' claim to strictly prevent misuse as an access token.
class RefreshTokenPayload(BaseModel):
    """
    Decoded Refresh JWT payload structure.
    """
    # User identifier (UUID as string)
    sub: str = Field(..., description="User ID (subject).")
    # Unique JWT ID for revocation tracking
    jti: str = Field(..., description="JWT ID for revocation.")
    # Timestamps (PyJWT returns these as integers)
    iat: int = Field(..., description="Issued at (UNIX timestamp).")
    exp: int = Field(..., description="Expiration time (UNIX timestamp).")
    # Role-Based Access Control (RBAC)
    role: Literal["admin", "viewer"] = Field(..., description="User role.")
    # Channel scopes (ignored for admin, enforced for viewer)
    scope: List[str] = Field(default_factory=list, description="Allowed channel IDs.")
    # Token type discriminator (prevents using access tokens for refresh operations)
    type: Literal["refresh"] = Field(..., description="Token type discriminator.")