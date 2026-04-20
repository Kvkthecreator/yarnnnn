#!/usr/bin/env python3
"""
Purge all data for a specific user to test cold-start/onboarding flow.

Usage:
    cd /Users/macbook/yarnnn/api
    python scripts/purge_user_data.py seulkim88@gmail.com

This will:
1. Delete all agent_runs for user's agents
2. Delete all agents
3. Delete all chat_sessions (and cascade to session_messages)

Note: workspace_files (the filesystem substrate — identity, memory,
context domains, task charters, _performance.md) is NOT purged here.
For a full cold-start including filesystem state, also delete
workspace_files rows for the user.

WARNING: This is destructive and cannot be undone!
"""

import os
import sys
from pathlib import Path
from typing import Optional, List

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client


def get_service_client():
    """Get Supabase client with service role key (bypasses RLS)."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

    return create_client(url, key)


def get_user_id_by_email(client, email: str) -> Optional[str]:
    """Look up user ID from auth.users by email."""
    try:
        users = client.auth.admin.list_users()
        for user in users:
            if user.email == email:
                return user.id
    except Exception as e:
        print(f"Error looking up user: {e}")
    return None


def purge_user_data(email: str, dry_run: bool = False):
    """Purge all data for a user to reset to cold-start state."""
    client = get_service_client()

    # Find the user_id
    print(f"\n🔍 Looking up user: {email}")
    user_id = get_user_id_by_email(client, email)

    if not user_id:
        print(f"✗ Could not find user with email: {email}")
        return

    print(f"✓ Found user_id: {user_id}")
    action = "Would delete" if dry_run else "Deleting"

    # 1. Delete agent_runs and agents
    print(f"\n📦 Fetching agents...")
    agents = client.table("agents").select("id, title").eq("user_id", user_id).execute()
    agent_ids = [d["id"] for d in (agents.data or [])]
    print(f"   Found {len(agent_ids)} agents")

    if agent_ids:
        print(f"\n🗑️  {action} agent_runs...")
        for did in agent_ids:
            if not dry_run:
                client.table("agent_runs").delete().eq("agent_id", did).execute()
            print(f"   - Versions for {did[:8]}...")

    print(f"\n🗑️  {action} agents...")
    if not dry_run:
        result = client.table("agents").delete().eq("user_id", user_id).execute()
        print(f"   Deleted {len(result.data or [])} agents")
    else:
        print(f"   Would delete {len(agent_ids)} agents")

    # 2. Delete chat_sessions (session_messages cascade automatically)
    print(f"\n🗑️  {action} chat_sessions...")
    if not dry_run:
        result = client.table("chat_sessions").delete().eq("user_id", user_id).execute()
        print(f"   Deleted {len(result.data or [])} chat sessions (messages cascade)")
    else:
        sessions = client.table("chat_sessions").select("id").eq("user_id", user_id).execute()
        print(f"   Would delete {len(sessions.data or [])} chat sessions")

    # ADR-196: user_memory table dropped (migration 151). Memory is
    # filesystem-native in workspace_files since ADR-156 — not purged here.
    # knowledge_domains removed (ADR-059); work_tickets removed (ADR-090).

    print(f"\n{'🔍 DRY RUN COMPLETE' if dry_run else '✅ PURGE COMPLETE'}")
    print(f"User {email} is now in cold-start state (zero agents, no chat history).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python purge_user_data.py <email> [--dry-run]")
        print("\nExample:")
        print("  python scripts/purge_user_data.py seulkim88@gmail.com --dry-run")
        print("  python scripts/purge_user_data.py seulkim88@gmail.com")
        sys.exit(1)

    email = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    if not dry_run:
        print(f"\n⚠️  WARNING: This will permanently delete ALL data for {email}")
        print("This includes: agents, chat history, memories")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    purge_user_data(email, dry_run=dry_run)
