#!/usr/bin/env python3
# ==============================================================================
# CnSS User Creation Utility
# Console utility to create new users with specific roles and channel scopes.
# ==============================================================================
import argparse
import asyncio
import getpass
import sys
from typing import List, Optional

from core.database import close_db_pool, get_db_pool, init_db_pool
from core.security.passwords import hash_password


# --- Helper Functions ---
def parse_scopes(scopes_str: Optional[str]) -> List[str]:
    """Parses a comma-separated string of channel IDs into a list."""
    if not scopes_str:
        return []
    return [scope.strip() for scope in scopes_str.split(",") if scope.strip()]


async def create_user(username: str, password: str, role: str, scopes: List[str]) -> None:
    """
    Connects to the database, hashes the password, and inserts the user
    along with their channel scopes (if applicable).
    """
    print("[*] Initializing database connection...")
    await init_db_pool()
    pool = get_db_pool()

    try:
        async with pool.acquire() as conn:
            # 1. Check if user already exists
            existing_user = await conn.fetchrow("SELECT id, role FROM users WHERE username = $1", username)
            if existing_user:
                print(f"[!] Error: User '{username}' already exists with role '{existing_user['role']}'.")
                return

            # 2. Hash the password using Argon2id
            print("[*] Hashing password...")
            password_hash = hash_password(password)

            # 3. Insert the new user
            print(f"[*] Creating user '{username}' with role '{role}'...")
            user_row = await conn.fetchrow(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                username,
                password_hash,
                role,
            )
            user_id = str(user_row["id"])
            print(f"[+] Successfully created user '{username}' (ID: {user_id})")

            # 4. Assign channel scopes (only for 'viewer' role)
            if role == "viewer" and scopes:
                print(f"[*] Assigning {len(scopes)} channel scope(s)...")
                for channel_id in scopes:
                    await conn.execute(
                        """
                        INSERT INTO user_channel_scopes (user_id, channel_id)
                        VALUES ($1::uuid, $2)
                        ON CONFLICT (user_id, channel_id) DO NOTHING
                        """,
                        user_id,
                        channel_id,
                    )
                print(f"[+] Scopes assigned: {', '.join(scopes)}")
            elif role == "admin":
                print("[+] Admin role assigned. No specific scopes needed (unrestricted access).")

        print("[*] Operation completed successfully.")

    except Exception as e:
        print(f"[!] Database error occurred: {e}")
        sys.exit(1)
    finally:
        print("[*] Closing database connection...")
        await close_db_pool()


# --- Main Entry Point ---
def main() -> None:
    parser = argparse.ArgumentParser(description="CnSS Console Utility: Create a new user with role and scopes.")
    parser.add_argument("username", type=str, help="The username for the new user (max 50 characters)")
    parser.add_argument(
        "--role",
        type=str,
        choices=["admin", "viewer"],
        default="viewer",
        help="The role of the user. Default is 'viewer'.",
    )
    parser.add_argument(
        "--scopes",
        type=str,
        default="",
        help="Comma-separated list of channel IDs (e.g., 'bridge-berlin-01,bridge-prague-01'). "
        "Ignored if role is 'admin'.",
    )

    args = parser.parse_args()
    scopes_list = parse_scopes(args.scopes)

    # Securely prompt for password without echoing to the console
    password = getpass.getpass(f"Enter password for user '{args.username}': ")
    if not password:
        print("[!] Error: Password cannot be empty.")
        sys.exit(1)

    # Confirm password
    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("[!] Error: Passwords do not match.")
        sys.exit(1)

    print("\n--- User Creation Summary ---")
    print(f"Username : {args.username}")
    print(f"Role     : {args.role}")
    print(f"Scopes   : {', '.join(scopes_list) if scopes_list else 'N/A (Admin gets all)'}")
    print("-----------------------------\n")

    confirm = input("Proceed with user creation? (y/N): ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        sys.exit(0)

    # Run the async database operations
    asyncio.run(create_user(args.username, password, args.role, scopes_list))


if __name__ == "__main__":
    main()
