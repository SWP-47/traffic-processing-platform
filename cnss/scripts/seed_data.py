#!/usr/bin/env python3
# ==============================================================================
# CnSS Seed Data Script
# Populates the database with mock users, channels, and access scopes
# for local development and testing. Idempotent: safe to run multiple times.
# ==============================================================================

import asyncio
import logging
import sys
from typing import Dict, List

import asyncpg

from core.config import settings
from core.database import close_db_pool, init_db_pool
from core.security.passwords import hash_password

# --- Module Logger ---
logger = logging.getLogger(__name__)

# --- Mock Data Configuration ---
# Test users with their roles, passwords, and channel access scopes.
# Admin scope is intentionally empty — admins bypass scope restrictions entirely.
MOCK_USERS: Dict[str, Dict] = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "scope": [],  # Admin scope is dynamically populated at login
    },
    "viewer": {
        "password": "viewer123",
        "role": "viewer",
        "scope": ["bridge-berlin-01", "bridge-prague-01"],
    },
}

# Test channels that will be registered in the 'channels' table.
# These channels are referenced by the viewer's scope and used for testing.
MOCK_CHANNELS: List[str] = [
    "bridge-berlin-01",
    "bridge-prague-01",
]


# --- Database Seeding Functions ---

async def seed_channels(conn: asyncpg.Connection) -> None:
    """
    Inserts mock channels into the 'channels' table.
    Uses ON CONFLICT DO NOTHING to ensure idempotency.
    """
    for channel_id in MOCK_CHANNELS:
        await conn.execute(
            """
            INSERT INTO channels (channel_id, is_active, last_activity_at)
            VALUES ($1, FALSE, NULL)
            ON CONFLICT (channel_id) DO NOTHING
            """,
            channel_id,
        )
    logger.info(f"✓ Seeded {len(MOCK_CHANNELS)} channels: {MOCK_CHANNELS}")


async def seed_users(conn: asyncpg.Connection) -> Dict[str, str]:
    """
    Inserts mock users into the 'users' table with Argon2id-hashed passwords.
    Returns a mapping of username -> user_id for scope insertion.
    Uses ON CONFLICT DO NOTHING to ensure idempotency.
    """
    user_ids: Dict[str, str] = {}

    for username, user_data in MOCK_USERS.items():
        # Hash the password using Argon2id (matches core.security.passwords)
        password_hash = hash_password(user_data["password"])

        # Insert user; retrieve existing id if already present
        row = await conn.fetchrow(
            """
            INSERT INTO users (username, password_hash, role)
            VALUES ($1, $2, $3)
            ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash
            RETURNING id
            """,
            username,
            password_hash,
            user_data["role"],
        )
        user_ids[username] = str(row["id"])

    logger.info(f"✓ Seeded {len(MOCK_USERS)} users: {list(MOCK_USERS.keys())}")
    return user_ids


async def seed_scopes(conn: asyncpg.Connection, user_ids: Dict[str, str]) -> None:
    """
    Inserts channel access scopes for viewer users.
    Deletes existing scopes for each user before re-inserting to ensure consistency.
    """
    for username, user_data in MOCK_USERS.items():
        user_id = user_ids[username]
        scope = user_data["scope"]

        # Skip users without scope (e.g., admins)
        if not scope:
            continue

        # Clear existing scopes for this user to ensure clean state
        await conn.execute(
            "DELETE FROM user_channel_scopes WHERE user_id = $1::uuid",
            user_id,
        )

        # Insert new scopes
        for channel_id in scope:
            await conn.execute(
                """
                INSERT INTO user_channel_scopes (user_id, channel_id)
                VALUES ($1::uuid, $2)
                ON CONFLICT (user_id, channel_id) DO NOTHING
                """,
                user_id,
                channel_id,
            )

        logger.info(f"✓ Seeded {len(scope)} scopes for user '{username}': {scope}")


# --- Main Entry Point ---

async def main() -> None:
    """
    Main seeding routine. Initializes the database connection,
    seeds channels, users, and scopes in the correct order.
    """
    print("=" * 60)
    print("CnSS Seed Data Script")
    print("=" * 60)

    # Initialize database connection pool
    await init_db_pool()
    logger.info("Database connection pool initialized.")

    try:
        async with (await init_db_pool()).acquire() as conn:
            # Step 1: Seed channels first (referenced by scopes)
            await seed_channels(conn)

            # Step 2: Seed users and retrieve their IDs
            user_ids = await seed_users(conn)

            # Step 3: Seed channel access scopes for viewers
            await seed_scopes(conn, user_ids)

        print("=" * 60)
        print("✓ Seeding completed successfully!")
        print("=" * 60)
        print("\nTest Credentials:")
        print("-" * 40)
        for username, user_data in MOCK_USERS.items():
            print(f"  Username: {username}")
            print(f"  Password: {user_data['password']}")
            print(f"  Role:     {user_data['role']}")
            print(f"  Scope:    {user_data['scope'] or '(all channels)'}")
            print("-" * 40)

    except Exception as e:
        logger.error(f"✗ Seeding failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Close database connection pool
        await close_db_pool()
        logger.info("Database connection pool closed.")


if __name__ == "__main__":
    # Configure basic logging for console output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(main())