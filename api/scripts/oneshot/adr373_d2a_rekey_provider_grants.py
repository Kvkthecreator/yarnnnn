"""ADR-373 D2.a migration: re-key foreign-LLM grants from client_id → PROVIDER host-id.

The grant-consult (ADR-373 D2) + the ADR-386 backfill keyed foreign-LLM membership
on the OAuth `client_id`. But a connector re-mints its client_id on every
re-registration, so one provider (Claude / ChatGPT) fragmented into many grant
rows — an unbounded stale tail, and a roster showing "Claude" 5× / "ChatGPT" 2×.

ADR-373 D2.a re-keys the member to the STABLE provider host-id (via the ADR-379
registry): one grant per (workspace, provider), across all the provider's
client_id re-registrations.

This migration:
  1. Reads every active foreign-llm/platform/a2a grant.
  2. Resolves each principal_id → provider host-id (resolve_provider_id_for_client;
     a row already keyed on a host-id is left as-is).
  3. Ensures the PROVIDER grant exists (ensure_principal_grant, host-id key),
     preserving any explicit `scopes` from a client_id-keyed row (so a narrow
     survives the re-key — the strictest scope across the provider's rows wins).
  4. Revokes the old client_id-keyed rows (status='revoked' — reversible audit;
     no tokens deleted, the connector stays connected; only the GRANT KEY changes).

Idempotent + re-runnable. A row already keyed on a host-id is a no-op. Pure
deterministic Python — no LLM calls. Service client (RLS bypass).

Usage (run the file directly):
    cd api && python scripts/oneshot/adr373_d2a_rekey_provider_grants.py          # dry-run
    cd api && python scripts/oneshot/adr373_d2a_rekey_provider_grants.py --apply  # migrate
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_API_ROOT / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("adr373_d2a_rekey")

_FOREIGN_ROLES = ("foreign-llm", "platform", "a2a")


def main(apply: bool) -> int:
    from services.supabase import get_service_client
    from services.principal_grants import (
        ensure_principal_grant, resolve_provider_id_for_client, provider_label,
    )
    from mcp_server.presentation.hosts import _BY_ID

    svc = get_service_client()

    grants = (
        svc.table("principal_grants")
        .select("id, principal_id, workspace_id, role, scopes, status")
        .in_("role", list(_FOREIGN_ROLES))
        .eq("status", "active")
        .execute()
    ).data or []
    logger.info("Found %d active foreign-principal grants.", len(grants))

    # Group: (workspace, provider) → {scopes set, old client_id grant ids}
    providers: dict[tuple, dict] = {}
    already_keyed = 0
    for g in grants:
        pid = g["principal_id"]
        if pid in _BY_ID:
            # Already a host-id — leave it (and don't revoke it).
            already_keyed += 1
            continue
        provider_id = resolve_provider_id_for_client(pid)
        if not provider_id:
            logger.warning("  UNKNOWN provider for client %s — leaving as-is (best-effort key).", pid[:8])
            continue
        key = (g["workspace_id"], provider_id)
        slot = providers.setdefault(key, {"scopes": None, "old_ids": [], "label": provider_label(provider_id) or provider_id})
        slot["old_ids"].append(g["id"])
        # Preserve the STRICTEST narrowing across the provider's rows: if any row
        # has explicit scopes, the provider inherits the intersection-ish floor.
        # Simplest correct rule: if exactly one row is narrowed, take it; if
        # multiple differ, take the smallest set (tightest). NULL scopes = class
        # default (no narrowing), so only consider explicit ones.
        if g.get("scopes"):
            cur = slot["scopes"]
            cand = list(g["scopes"])
            slot["scopes"] = cand if (cur is None or len(cand) < len(cur)) else cur

    logger.info(
        "%d already host-keyed; %d providers to ensure across %d client_id rows.",
        already_keyed, len(providers), sum(len(v["old_ids"]) for v in providers.values()),
    )

    for (workspace_id, provider_id), slot in providers.items():
        label, scopes, old_ids = slot["label"], slot["scopes"], slot["old_ids"]
        if not apply:
            logger.info(
                "  [dry-run] ensure provider grant %s (%s) ws=%s scopes=%s; revoke %d old rows",
                label, provider_id, workspace_id[:8], scopes, len(old_ids),
            )
            continue
        ensure_principal_grant(
            principal_id=provider_id,
            workspace_id=workspace_id,
            role="foreign-llm",
            scopes=scopes,
            granted_by="system:adr373-d2a-rekey",
        )
        for old_id in old_ids:
            svc.table("principal_grants").update({"status": "revoked"}).eq("id", old_id).execute()
        logger.info(
            "  ensured provider grant %s (%s) ws=%s scopes=%s; revoked %d old client_id rows",
            label, provider_id, workspace_id[:8], scopes, len(old_ids),
        )

    logger.info("%s complete.", "MIGRATION" if apply else "DRY-RUN")
    return 0


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    if not apply:
        logger.info("DRY-RUN (pass --apply to migrate).")
    raise SystemExit(main(apply))
