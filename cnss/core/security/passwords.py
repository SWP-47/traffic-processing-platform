# ==============================================================================
# CnSS Password Hashing Module
# Handles secure password hashing and verification using Argon2id via passlib.
# Ensures that plaintext passwords are never stored or processed insecurely.
# ==============================================================================

from passlib.context import CryptContext

# --- Password Hashing Context ---
# Initializes the passlib CryptContext with Argon2id as the default scheme.
# Argon2id provides robust protection against both side-channel and GPU-based attacks.
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)

# --- Hashing and Verification Functions ---

def hash_password(plain_password: str) -> str:
    """
    Hashes a plaintext password using Argon2id.
    """
    # Apply the Argon2id hashing algorithm to the raw password
    return pwd_context.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plaintext password against a stored Argon2id hash.
    """
    # Compare the raw password with the stored hash securely
    return pwd_context.verify(plain_password, hashed_password)