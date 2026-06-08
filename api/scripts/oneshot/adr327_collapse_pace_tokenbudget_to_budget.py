"""
One-shot (ADR-327): collapse `_pace.yaml` + `_token_budget.yaml` into one
`governance/_budget.yaml` per workspace, then delete the old files.

Run this AT/AFTER the ADR-327 code deploy — the code reads `_budget.yaml`,
so live workspaces need their governance migrated. The loader's kernel
default ($50/monthly) is the safety net for any workspace whose
`_budget.yaml` is absent, so this migration is about faithful porting +
dead-file cleanup, not correctness-criticality.

Mapping (ADR-327 D2):
    _token_budget.yaml::daily_spend_ceiling_usd  →  budget.amount_usd (×30, monthly)
                                                     capped/floored to a sane band
    _token_budget.yaml::min_interval_between_..   →  preserved verbatim
    _token_budget.yaml::overrides                 →  preserved verbatim
    _token_budget.yaml::max_judgment_recurrences  →  DROPPED (fire-count cap deleted)
    _pace.yaml::kind / every                       →  DROPPED (tempo retires — it is
                                                      the Reviewer's allocation problem)

Window is always `monthly` (ADR-327 seed decision 2026-06-08). amount_usd
derives from the operator's old daily ceiling (×30) when present, else the
kernel default $50.

Attribution: writes via Authored Substrate (ADR-209) with
`authored_by="system:adr327-budget-collapse"`. Idempotent: workspaces that
already have a `_budget.yaml` are skipped (only their stale old files, if
any, are cleaned up).

Old files are DELETED via workspace_files.delete() (deletion is a distinct
operation, not a revision — see authored_substrate.py header). The revision
chain of the NEW _budget.yaml preserves provenance; the deleted old files'
revision history remains in workspace_file_versions (not purged).

Usage:
    cd api
    python -m scripts.oneshot.adr327_collapse_pace_tokenbudget_to_budget [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any, Optional

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("adr327_budget_collapse")

BUDGET_PATH = "/workspace/governance/_budget.yaml"
TOKEN_BUDGET_PATH = "/workspace/governance/_token_budget.yaml"
PACE_PATH = "/workspace/governance/_pace.yaml"
# A counterfactual-eval seed placed _pace.yaml at the pre-ADR-320 path.
LEGACY_PACE_PATH = "/workspace/context/_shared/_pace.yaml"

_KERNEL_DEFAULT_AMOUNT_USD = 50.0
# Sane band for the derived monthly amount so a stale/odd daily ceiling
# doesn't produce an absurd envelope.
_MIN_AMOUNT_USD = 20.0
_MAX_AMOUNT_USD = 500.0


def _strip_yaml_frontmatter(content: str) -> str:
    """Drop `---\\n...\\n---\\n` tier frontmatter (ADR-254), return body."""
    if not content.startswith("---"):
        return content
    end = content.find("\n---\n", 3)
    if end == -1:
        return content
    return content[end + 5 :]


def _parse(content: str) -> dict:
    try:
        parsed = yaml.safe_load(_strip_yaml_frontmatter(content)) or {}
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _derive_budget_yaml(token_budget_content: Optional[str]) -> str:
    """Build _budget.yaml body from the old _token_budget.yaml (pace is
    discarded — tempo retires)."""
    amount = _KERNEL_DEFAULT_AMOUNT_USD
    min_interval = 60
    overrides: dict[str, Any] = {}

    if token_budget_content:
        parsed = _parse(token_budget_content)
        daily = parsed.get("daily_spend_ceiling_usd")
        if isinstance(daily, (int, float)) and daily > 0:
            derived = float(daily) * 30.0
            amount = max(_MIN_AMOUNT_USD, min(_MAX_AMOUNT_USD, derived))
        mi = parsed.get("min_interval_between_recurrence_fires_seconds")
        if isinstance(mi, int) and mi > 0:
            min_interval = mi
        ov = parsed.get("overrides")
        if isinstance(ov, dict):
            overrides = ov

    doc: dict[str, Any] = {
        "budget": {"amount_usd": round(amount, 2), "window": "monthly"},
        "per_wake_ceiling_usd": 1.00,
        "min_interval_between_recurrence_fires_seconds": min_interval,
    }
    if overrides:
        doc["overrides"] = overrides

    header = (
        "# _budget.yaml — the operation's spend envelope (ADR-327)\n"
        "# Migrated from _pace.yaml + _token_budget.yaml (collapsed per ADR-327 D2).\n"
        "# Operator declares; the Reviewer respects + allocates wakes within it.\n"
        "# GOVERNANCE per ADR-293 D2 — the Reviewer cannot author this file.\n"
        "\n"
    )
    return header + yaml.safe_dump(doc, sort_keys=False, default_flow_style=False)


def _fetch_one(client, user_id: str, path: str) -> Optional[str]:
    res = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", user_id)
        .eq("path", path)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0].get("content") if rows else None


def _delete_one(client, user_id: str, path: str, *, dry_run: bool) -> bool:
    """Delete a workspace_files row. Returns True if a row existed."""
    existing = (
        client.table("workspace_files")
        .select("id")
        .eq("user_id", user_id)
        .eq("path", path)
        .limit(1)
        .execute()
    ).data or []
    if not existing:
        return False
    if dry_run:
        logger.info("[%s]   would delete %s", user_id[:8], path)
        return True
    client.table("workspace_files").delete().eq("user_id", user_id).eq("path", path).execute()
    logger.info("[%s]   deleted %s", user_id[:8], path)
    return True


def migrate_one(client, user_id: str, *, dry_run: bool) -> str:
    """Migrate one workspace. Returns a short status string."""
    has_budget = _fetch_one(client, user_id, BUDGET_PATH) is not None
    token_content = _fetch_one(client, user_id, TOKEN_BUDGET_PATH)
    has_pace = (
        _fetch_one(client, user_id, PACE_PATH) is not None
        or _fetch_one(client, user_id, LEGACY_PACE_PATH) is not None
    )

    # Clean up stale old files in all cases.
    def _cleanup() -> None:
        _delete_one(client, user_id, TOKEN_BUDGET_PATH, dry_run=dry_run)
        _delete_one(client, user_id, PACE_PATH, dry_run=dry_run)
        _delete_one(client, user_id, LEGACY_PACE_PATH, dry_run=dry_run)

    if has_budget:
        _cleanup()
        return "already has _budget.yaml — cleaned old files only"

    if token_content is None and not has_pace:
        return "no governance cost files — kernel default applies, nothing to do"

    new_content = _derive_budget_yaml(token_content)

    if dry_run:
        logger.info("[%s] would write _budget.yaml:\n%s", user_id[:8], new_content)
        _cleanup()
        return "dry-run write + cleanup"

    from services.authored_substrate import write_revision

    write_revision(
        client,
        user_id=user_id,
        path=BUDGET_PATH,
        content=new_content,
        authored_by="system:adr327-budget-collapse",
        message="ADR-327: collapse _pace.yaml + _token_budget.yaml into _budget.yaml (dollar spend envelope)",
        summary="Budget governance — the operation's spend envelope",
        tags=["_budget", "governance"],
        lifecycle="active",
        content_type="text/yaml",
    )
    logger.info("[%s] wrote _budget.yaml", user_id[:8])
    _cleanup()
    return "migrated"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without applying.")
    args = parser.parse_args()

    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL + SUPABASE_SERVICE_KEY required")
        return 1
    client = create_client(url, key)

    # Find every workspace touched by either old file.
    user_ids: set[str] = set()
    for path in (TOKEN_BUDGET_PATH, PACE_PATH, LEGACY_PACE_PATH):
        rows = (
            client.table("workspace_files")
            .select("user_id")
            .eq("path", path)
            .execute()
        ).data or []
        for r in rows:
            uid = r.get("user_id")
            if uid:
                user_ids.add(uid)

    logger.info("Found %d workspaces with legacy pace/token-budget files", len(user_ids))

    migrated = skipped = failed = 0
    for uid in sorted(user_ids):
        try:
            status = migrate_one(client, uid, dry_run=args.dry_run)
            if status == "migrated" or status.startswith("dry-run"):
                migrated += 1
            else:
                skipped += 1
            logger.info("[%s] %s", uid[:8], status)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.exception("[%s] failed: %s", uid[:8], exc)

    logger.info("Done — migrated=%d skipped=%d failed=%d", migrated, skipped, failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
