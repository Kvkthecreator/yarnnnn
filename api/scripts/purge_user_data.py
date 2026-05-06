#!/usr/bin/env python3
"""
Purge all data for a specific user to test cold-start/onboarding flow.

Usage:
    cd /Users/macbook/yarnnn/api
    python scripts/purge_user_data.py <email> [--dry-run]

This gives a TRUE cold-start. Wipe order (FK-safe):
1. workspace_file_versions (ADR-209 Authored Substrate revisions — delete
   before workspace_files; no FK cascade on (user_id, path))
2. workspace_files (Axiom 1 substrate — IDENTITY, MANDATE, context domains,
   task charters, /workspace/review/, agent workspaces)
3. action_proposals (ADR-194 Reviewer queue)
4. tasks (ADR-138)
5. agents + agent_runs (cascaded via agent_id)
6. chat_sessions (cascades session_messages — ADR-125)
7. platform_connections (OAuth tokens)
8. token_usage (ADR-171 billing ledger)
9. notifications (ADR-041)
10. uploaded documents purged via workspace_files (ADR-249: /workspace/uploads/*)
11. user_admin_flags (ADR-194 v2 Phase 2b impersonation scope)
12. activity_log

NOT deleted (intentional):
- auth.users row — keep the login; we just wipe their workspace state
- workspaces row itself — balance + signup audit preserved (ADR-172)
- balance_transactions ledger — lifecycle audit, signup grant idempotency
- user_notification_preferences — email prefs survive workspace wipe
  (the account-level reset at Settings L4 handles them)

After purge, next login should trigger workspace_init which scaffolds the
post-LAYER-MAPPING-flip substrate: YARNNN agent row + Reviewer substrate
at /workspace/review/ (seven files) + _shared/ context skeleton + essential
tasks (daily-update + back-office set per ADR-161/164).

WARNING: This is destructive and cannot be undone!
"""

import os
import sys
from pathlib import Path
from typing import Optional

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


def _count(client, table: str, user_id: str, column: str = "user_id") -> int:
    """Return row count for table where column == user_id.

    Uses `*` rather than a specific column so it works for tables without an
    `id` surrogate key (e.g. `user_admin_flags` is PK'd on `user_id`).
    """
    try:
        result = client.table(table).select("*", count="exact", head=True).eq(column, user_id).execute()
        return result.count or 0
    except Exception as e:
        print(f"   (count failed for {table}: {e})")
        return 0


def _delete(client, table: str, user_id: str, column: str = "user_id", dry_run: bool = False) -> int:
    """Delete rows from table where column == user_id. Returns deleted count (or would-delete on dry-run)."""
    n = _count(client, table, user_id, column)
    if n == 0:
        return 0
    if dry_run:
        return n
    try:
        client.table(table).delete().eq(column, user_id).execute()
        return n
    except Exception as e:
        print(f"   (delete failed for {table}: {e})")
        return 0


def purge_user_data(email: str, dry_run: bool = False):
    """Purge all data for a user to reset to cold-start state.

    Order matters for referential integrity: delete child rows before parents
    where CASCADE isn't sufficient.
    """
    client = get_service_client()

    print(f"\n🔍 Looking up user: {email}")
    user_id = get_user_id_by_email(client, email)

    if not user_id:
        print(f"✗ Could not find user with email: {email}")
        return

    print(f"✓ Found user_id: {user_id}")
    label = "Would delete" if dry_run else "Deleting"
    print()

    # ──────────────────────────────────────────────────────────────────────
    # 1. Authored Substrate (ADR-209) — FK order matters:
    #    workspace_files.head_version_id → workspace_file_versions.id, so
    #    null the pointer first, then wipe revisions, then wipe files.
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} null workspace_files.head_version_id pointers...")
    if dry_run:
        # Count rows we'd update
        try:
            r = (
                client.table("workspace_files")
                .select("*", count="exact", head=True)
                .eq("user_id", user_id)
                .not_.is_("head_version_id", "null")
                .execute()
            )
            print(f"   {r.count or 0} pointers would be nulled")
        except Exception as e:
            print(f"   (count failed: {e})")
    else:
        try:
            (
                client.table("workspace_files")
                .update({"head_version_id": None})
                .eq("user_id", user_id)
                .execute()
            )
            print("   OK (pointers nulled)")
        except Exception as e:
            print(f"   (update failed: {e})")

    print(f"🗑️  {label} workspace_file_versions (Authored Substrate revisions)...")
    n = _delete(client, "workspace_file_versions", user_id, dry_run=dry_run)
    print(f"   {n} revision rows")

    print(f"🗑️  {label} workspace_files (filesystem substrate)...")
    n = _delete(client, "workspace_files", user_id, dry_run=dry_run)
    print(f"   {n} workspace files")

    # ──────────────────────────────────────────────────────────────────────
    # 2. Proposals (ADR-194 — Reviewer queue)
    # ──────────────────────────────────────────────────────────────────────
    # ADR-195 v2 migrated outcomes out of SQL onto the filesystem
    # (_performance.md per domain) — no action_outcomes table to wipe.
    print(f"🗑️  {label} action_proposals...")
    n = _delete(client, "action_proposals", user_id, dry_run=dry_run)
    print(f"   {n} proposals")

    # ──────────────────────────────────────────────────────────────────────
    # 3. Tasks (ADR-138)
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} tasks...")
    n = _delete(client, "tasks", user_id, dry_run=dry_run)
    print(f"   {n} tasks")

    # ──────────────────────────────────────────────────────────────────────
    # 4. Agent runs + agents (ADR-103 renames from deliverable_versions)
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} agent_runs (joining through agent_id)...")
    agents_result = client.table("agents").select("id").eq("user_id", user_id).execute()
    agent_ids = [a["id"] for a in (agents_result.data or [])]
    runs_total = 0
    if agent_ids:
        for aid in agent_ids:
            if dry_run:
                c = _count(client, "agent_runs", aid, column="agent_id")
                runs_total += c
            else:
                try:
                    client.table("agent_runs").delete().eq("agent_id", aid).execute()
                    runs_total += 1  # count of agents whose runs were purged
                except Exception as e:
                    print(f"   (delete failed for agent {aid[:8]}: {e})")
    print(f"   {runs_total} agent run batches")

    print(f"🗑️  {label} agents...")
    n = _delete(client, "agents", user_id, dry_run=dry_run)
    print(f"   {n} agents")

    # ──────────────────────────────────────────────────────────────────────
    # 5. Chat sessions (cascades session_messages) — ADR-125
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} chat_sessions (cascades session_messages)...")
    n = _delete(client, "chat_sessions", user_id, dry_run=dry_run)
    print(f"   {n} chat sessions")

    # ──────────────────────────────────────────────────────────────────────
    # 6. Platform connections (OAuth tokens) — ADR-059 rename
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} platform_connections (OAuth tokens)...")
    n = _delete(client, "platform_connections", user_id, dry_run=dry_run)
    print(f"   {n} platform connections")

    # ──────────────────────────────────────────────────────────────────────
    # 7. Billing/audit ledger (ADR-171)
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} token_usage (billing/audit ledger)...")
    n = _delete(client, "token_usage", user_id, dry_run=dry_run)
    print(f"   {n} token usage rows")

    # ──────────────────────────────────────────────────────────────────────
    # 8. Notifications (ADR-041)
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} notifications...")
    n = _delete(client, "notifications", user_id, dry_run=dry_run)
    print(f"   {n} notifications")

    # ──────────────────────────────────────────────────────────────────────
    # 9. Uploaded documents (ADR-249: now in workspace_files /workspace/uploads/)
    # Purged via workspace_files user-scoped delete above — no separate step needed.
    # ──────────────────────────────────────────────────────────────────────

    # ──────────────────────────────────────────────────────────────────────
    # 10. Admin flags (ADR-194 v2 Phase 2b — impersonation scope)
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} user_admin_flags...")
    n = _delete(client, "user_admin_flags", user_id, dry_run=dry_run)
    print(f"   {n} admin flag rows")

    # ──────────────────────────────────────────────────────────────────────
    # 11. Activity log
    # ──────────────────────────────────────────────────────────────────────
    print(f"🗑️  {label} activity_log...")
    n = _delete(client, "activity_log", user_id, dry_run=dry_run)
    print(f"   {n} activity events")

    # ──────────────────────────────────────────────────────────────────────
    # 11. Balance transactions audit (preserve signup_grant for re-signup test)
    # ──────────────────────────────────────────────────────────────────────
    # Intentionally NOT deleted — the balance_transactions ledger tracks
    # lifecycle events (signup, topups, refunds); wiping it would make
    # re-signup attempts look like fresh signups and grant duplicate balance.

    print(f"\n{'🔍 DRY RUN COMPLETE' if dry_run else '✅ PURGE COMPLETE'}")
    print(f"\nUser {email} workspace state wiped.")
    print("Auth.users row preserved — user can log in again.")
    print("workspaces row + balance_transactions preserved — signup grant")
    print("  is not re-awarded, balance state continuous.")
    print()
    print("Next login should trigger workspace_init → post-flip substrate")
    print("scaffold (YARNNN + Reviewer seat + 7 /workspace/review/ files).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python purge_user_data.py <email> [--dry-run]")
        print("\nExample:")
        print("  python scripts/purge_user_data.py kvkthecreator@gmail.com --dry-run")
        print("  python scripts/purge_user_data.py kvkthecreator@gmail.com")
        sys.exit(1)

    email = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    if not dry_run:
        print(f"\n⚠️  WARNING: This will permanently delete ALL workspace state for {email}")
        print("This includes: agents, tasks, proposals, workspace_files, chat, platform")
        print("connections, tokens, notifications, activity log. Auth + balance preserved.")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    purge_user_data(email, dry_run=dry_run)
