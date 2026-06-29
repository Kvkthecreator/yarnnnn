#!/usr/bin/env python3
"""
Backfill embeddings for eligible-but-unembedded workspace files (ADR-325 follow-on).

Remediation for the 2026-06-29 finding (docs/evaluations/2026-06-29-recall-empty-
embedding-gap.md): embedding was decoupled from writes into the explicit `Embed`
primitive (ADR-325), but nothing in the memory/derivation loop ever called it, so
the workspace accumulated with `embedding IS NULL` everywhere → semantic `recall`
matched nothing. The wake-time fix (services/wake.py::_embed_derived_files) closes
the gap GOING FORWARD; this script makes EXISTING substrate AI-ready.

It reuses the SAME mechanism as the Embed primitive (Singular Implementation):
  - eligibility: services.primitives.embed.is_embed_eligible (ADR-325 D5)
  - execution:  services.primitives.workspace._embed_workspace_file

Usage:
    cd /Users/macbook/yarnnn/api
    python scripts/backfill_embeddings.py <email>            # one user
    python scripts/backfill_embeddings.py --all              # every user with files
    python scripts/backfill_embeddings.py <email> --dry-run  # report only, no embeds

Idempotent: only embeds rows where embedding IS NULL and the path is eligible.
Re-running after a partial run resumes cleanly. Honors no daily cap (this is an
operator-run remediation, not an autonomous loop) but logs the count.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

from services.primitives.embed import is_embed_eligible
from services.primitives.workspace import _embed_workspace_file


def get_service_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    return create_client(url, key)


def get_user_id_by_email(client, email: str) -> Optional[str]:
    try:
        users = client.auth.admin.list_users()
        for user in users:
            if user.email == email:
                return user.id
    except Exception as e:
        print(f"Error looking up user: {e}")
    return None


def _eligible_unembedded(client, user_id: str) -> list[dict]:
    """Return rows (path, content) that are unembedded AND embed-eligible."""
    rows = (
        client.table("workspace_files")
        .select("path, content, embedding")
        .eq("user_id", user_id)
        .is_("embedding", "null")
        .execute()
    ).data or []
    out = []
    for r in rows:
        path = r.get("path") or ""
        content = r.get("content") or ""
        rel = path[len("/workspace/"):] if path.startswith("/workspace/") else path.lstrip("/")
        ok, _reason = is_embed_eligible(rel, content)
        if ok:
            out.append({"path": path, "content": content})
    return out


async def _backfill_user(client, user_id: str, email: str, dry_run: bool) -> tuple[int, int]:
    targets = _eligible_unembedded(client, user_id)
    print(f"\n[{email or user_id[:8]}] {len(targets)} eligible-unembedded file(s)")
    if dry_run:
        for t in targets[:20]:
            print(f"    would embed: {t['path']}")
        if len(targets) > 20:
            print(f"    … +{len(targets) - 20} more")
        return len(targets), 0
    embedded = 0
    for t in targets:
        try:
            await _embed_workspace_file(client, user_id, t["path"], t["content"])
            embedded += 1
            if embedded % 25 == 0:
                print(f"    … embedded {embedded}/{len(targets)}")
        except Exception as e:
            print(f"    [!] failed {t['path']}: {e}")
    print(f"    embedded {embedded}/{len(targets)}")
    return len(targets), embedded


async def _amain():
    ap = argparse.ArgumentParser(description="Backfill workspace embeddings (ADR-325 follow-on).")
    ap.add_argument("email", nargs="?", help="user email (omit with --all)")
    ap.add_argument("--all", action="store_true", help="backfill every user that has workspace files")
    ap.add_argument("--dry-run", action="store_true", help="report only, do not embed")
    args = ap.parse_args()

    client = get_service_client()

    if args.all:
        # distinct user_ids that have any workspace_files
        rows = client.table("workspace_files").select("user_id").execute().data or []
        user_ids = sorted({r["user_id"] for r in rows if r.get("user_id")})
        print(f"Backfilling {len(user_ids)} user(s){' (dry-run)' if args.dry_run else ''}")
        tot_t = tot_e = 0
        for uid in user_ids:
            t, e = await _backfill_user(client, uid, "", args.dry_run)
            tot_t += t; tot_e += e
        print(f"\nTOTAL: {tot_e}/{tot_t} embedded across {len(user_ids)} user(s)")
        return

    if not args.email:
        ap.error("provide an email or --all")
    uid = get_user_id_by_email(client, args.email)
    if not uid:
        print(f"No user found for {args.email}")
        sys.exit(1)
    t, e = await _backfill_user(client, uid, args.email, args.dry_run)
    print(f"\nDONE: {e}/{t} embedded for {args.email}")


if __name__ == "__main__":
    asyncio.run(_amain())
