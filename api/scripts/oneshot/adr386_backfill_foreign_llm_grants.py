"""ADR-386 D1.a one-time backfill: provision foreign-LLM grants for the live population.

The auto-provision hook (ADR-386 D1) originally fired at OAuth *authorize* only.
But every connector in production authorized BEFORE the hook deployed and stays
alive via silent refresh-token rotation — so authorize-only never fired for any
of them. Result (measured 2026-06-30): real, writing foreign-LLM principals
(Claude / ChatGPT) with ZERO grant rows, and an empty External-Agents / AI
Connections pane while the LLMs were demonstrably active.

D1.a adds refresh-path provisioning (the durable fix, so the gap can't recur).
This script is the belt-and-suspenders companion: it populates the pane NOW
instead of waiting for each connector's next silent rotation.

For every `mcp_oauth_clients` row that has a LIVE access OR refresh token:
  - resolve the authorizing user (from its tokens) → owner workspace
  - ensure_principal_grant(role='foreign-llm', granted_by='system:adr386-backfill')

Idempotent + re-runnable (ensure_principal_grant no-ops on an existing active
grant). Pure deterministic Python — no LLM calls. Service client (RLS bypass).

Usage (run the file directly — the script self-inserts the api root on sys.path):
    cd api && python scripts/oneshot/adr386_backfill_foreign_llm_grants.py          # dry-run
    cd api && python scripts/oneshot/adr386_backfill_foreign_llm_grants.py --apply  # write grants
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("adr386_backfill")


def _live_client_users(svc) -> dict[str, str]:
    """Map client_id → authorizing user_id for every client with a LIVE token.

    A client is "live" if it has at least one access OR refresh token. The
    user_id is the principal who authorized it (all tokens for a client carry
    the same user_id in the N=1 world — one human connecting their own LLMs).
    """
    client_user: dict[str, str] = {}
    for table in ("mcp_oauth_access_tokens", "mcp_oauth_refresh_tokens"):
        rows = (
            svc.table(table)
            .select("client_id, user_id")
            .execute()
        ).data or []
        for r in rows:
            cid, uid = r.get("client_id"), r.get("user_id")
            if cid and uid and cid not in client_user:
                client_user[cid] = uid
    return client_user


def main(apply: bool) -> int:
    from services.supabase import get_service_client, resolve_owner_workspace_id
    from services.principal_grants import ensure_principal_grant

    svc = get_service_client()

    # Humanize for the log (client_id → name).
    name_rows = (
        svc.table("mcp_oauth_clients").select("client_id, client_name").execute()
    ).data or []
    names = {r["client_id"]: r.get("client_name") or r["client_id"] for r in name_rows}

    client_user = _live_client_users(svc)
    logger.info("Found %d clients with a live token.", len(client_user))

    provisioned = 0
    skipped_no_ws = 0
    for client_id, user_id in sorted(client_user.items(), key=lambda kv: names.get(kv[0], kv[0])):
        name = names.get(client_id, client_id)
        workspace_id = resolve_owner_workspace_id(user_id)
        if not workspace_id:
            logger.warning(
                "  SKIP %s (%s): no owner workspace for user %s",
                name, client_id[:8], user_id,
            )
            skipped_no_ws += 1
            continue

        if not apply:
            logger.info(
                "  [dry-run] would ensure foreign-llm grant: %s (%s) → workspace %s",
                name, client_id[:8], workspace_id[:8],
            )
            provisioned += 1
            continue

        grant = ensure_principal_grant(
            principal_id=client_id,
            workspace_id=workspace_id,
            role="foreign-llm",
            granted_by="system:adr386-backfill",
        )
        status = grant.get("status", "?")
        logger.info(
            "  ensured foreign-llm grant: %s (%s) → workspace %s [status=%s]",
            name, client_id[:8], workspace_id[:8], status,
        )
        provisioned += 1

    logger.info(
        "%s: %d grants %s, %d skipped (no workspace).",
        "APPLIED" if apply else "DRY-RUN",
        provisioned,
        "ensured" if apply else "would be ensured",
        skipped_no_ws,
    )
    return 0


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    if not apply:
        logger.info("DRY-RUN (pass --apply to write grants).")
    raise SystemExit(main(apply))
