"""
One-shot: rewrite all `_autonomy.yaml` files to canonical
{delegation, ceiling_cents} schema (Commit F.1 / Migration 172).

Defect being fixed (audit 2026-05-11): the FE writes `level:
bounded_autonomous` (4-value union: manual / assisted /
bounded_autonomous / autonomous); the backend reads `delegation:`
(3-value enum: manual / bounded / autonomous). The mismatch silently
defaults the auto-execute gate to `manual` on every workspace —
operator selections on the FE chip have been cosmetic.

This script does the live data rewrite. Migration 172's SQL is the
verification gate — run THIS first, then apply the migration.

Mapping (per Commit F decisions):
    level: bounded_autonomous   →  delegation: bounded
    level: autonomous           →  delegation: autonomous
    level: manual               →  delegation: manual
    level: assisted             →  delegation: manual    (had no backend semantics)
    (no level field)            →  delegation: manual

Also dropped (ADR-263 D4):
    heartbeat_triggers — explicitly retired; cron is part of the
    environment that fires recurrences, not a wake-trigger registry.

Attribution: writes via Authored Substrate (ADR-209) with
`authored_by="system:autonomy-schema-rewrite"`. Idempotent: rows
already on the canonical schema are skipped.

Usage:
    cd api
    python -m scripts.oneshot.rewrite_autonomy_yaml_to_delegation_schema [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("autonomy_rewrite")


AUTONOMY_PATH = "/workspace/governance/_autonomy.yaml"


def _map_level_to_delegation(level: Any) -> str:
    """Map FE 4-value union to backend 3-value enum."""
    if not isinstance(level, str):
        return "manual"
    s = level.strip().lower()
    if s == "bounded_autonomous":
        return "bounded"
    if s == "autonomous":
        return "autonomous"
    if s == "manual":
        return "manual"
    if s == "assisted":
        return "manual"  # never had backend semantics; was silently treated as manual
    if s in {"bounded", "delegation"}:
        return "bounded" if s == "bounded" else "manual"
    return "manual"


def _strip_yaml_frontmatter(content: str) -> tuple[str, str]:
    """Split off `---\\n...\\n---\\n` tier frontmatter (ADR-254)."""
    if not content.startswith("---"):
        return "", content
    end = content.find("\n---\n", 3)
    if end == -1:
        return "", content
    return content[: end + 5], content[end + 5 :]


def _rewrite_block(block: dict | None) -> dict:
    """Rewrite one autonomy block (default or per-domain)."""
    if not isinstance(block, dict):
        return {"delegation": "manual"}
    out: dict = {}
    if "delegation" in block:
        # Already canonical
        delegation = block["delegation"]
        if delegation not in {"manual", "bounded", "autonomous"}:
            delegation = "manual"
    elif "level" in block:
        delegation = _map_level_to_delegation(block["level"])
    else:
        delegation = "manual"
    out["delegation"] = delegation

    if "ceiling_cents" in block:
        try:
            out["ceiling_cents"] = int(block["ceiling_cents"])
        except (TypeError, ValueError):
            pass

    if "never_auto" in block and isinstance(block["never_auto"], list):
        out["never_auto"] = list(block["never_auto"])

    return out


def _rebuild_content(parsed: dict, frontmatter: str) -> str:
    """Render canonical _autonomy.yaml content."""
    out_doc: dict = {"default": _rewrite_block(parsed.get("default"))}

    raw_domains = parsed.get("domains")
    if isinstance(raw_domains, dict) and raw_domains:
        domains_out = {}
        for k, v in raw_domains.items():
            if isinstance(v, dict):
                domains_out[k] = _rewrite_block(v)
        if domains_out:
            out_doc["domains"] = domains_out

    # Preserve pause fields (ADR-248 D3)
    if parsed.get("paused_until") is not None:
        out_doc["paused_until"] = parsed["paused_until"]
    if parsed.get("pause_reason") is not None:
        out_doc["pause_reason"] = parsed["pause_reason"]

    body = (
        "# _autonomy.yaml — delegation declaration (ADR-254)\n"
        "# Machine-parsed by review_policy + working_memory.\n"
        "# Schema (Commit F / 2026-05-11):\n"
        "#   default:\n"
        "#     delegation: manual | bounded | autonomous\n"
        "#     ceiling_cents: <int> (required when delegation=bounded)\n"
        "#     never_auto: [<action_type>, ...] (always route to operator)\n"
        "#   paused_until: <ISO timestamp> (set by Reviewer / operator, ADR-248 D3)\n"
        "#   pause_reason: <string>\n"
        "# See AUTONOMY.md for documentation.\n"
        "\n"
    )
    body += yaml.safe_dump(out_doc, sort_keys=False, default_flow_style=False)

    return frontmatter + body


def needs_rewrite(content: str) -> bool:
    """True if the file carries legacy schema (level: / heartbeat_triggers:)."""
    if "heartbeat_triggers:" in content:
        return True
    # Any indented `  level:` (under default/domains, not a comment) → legacy
    for line in content.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        if line.startswith("  ") and stripped.startswith("level:"):
            return True
    return False


def rewrite_one(client, user_id: str, content: str, *, dry_run: bool) -> tuple[bool, str]:
    """Rewrite one user's _autonomy.yaml. Returns (rewrote, reason)."""
    if not needs_rewrite(content):
        return False, "already canonical"

    frontmatter, body = _strip_yaml_frontmatter(content)
    try:
        parsed = yaml.safe_load(body) or {}
    except yaml.YAMLError as exc:
        return False, f"yaml parse error: {exc}"
    if not isinstance(parsed, dict):
        return False, "yaml root not a mapping"

    new_content = _rebuild_content(parsed, frontmatter)

    if dry_run:
        logger.info("[%s] would rewrite", user_id[:8])
        logger.info("--- before ---\n%s", content)
        logger.info("--- after ---\n%s", new_content)
        return True, "dry-run rewrite"

    from services.authored_substrate import write_revision

    write_revision(
        client,
        user_id=user_id,
        path=AUTONOMY_PATH,
        content=new_content,
        authored_by="system:autonomy-schema-rewrite",
        message="Commit F.1: rewrite _autonomy.yaml to canonical {delegation, ceiling_cents} schema; drop heartbeat_triggers (ADR-263 D4)",
        summary="Autonomy delegation policy",
        tags=["_autonomy", "_shared"],
        lifecycle="active",
        content_type="text/yaml",
    )
    return True, "rewrote"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show planned rewrites without applying.")
    args = parser.parse_args()

    # Service client — bypasses RLS so we can rewrite all users.
    from supabase import create_client

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL + SUPABASE_SERVICE_KEY required")
        return 1
    client = create_client(url, key)

    rows = (
        client.table("workspace_files")
        .select("user_id,content")
        .eq("path", AUTONOMY_PATH)
        .execute()
    ).data or []

    logger.info("Found %d _autonomy.yaml files to inspect", len(rows))

    rewrote = 0
    skipped = 0
    failed = 0
    for row in rows:
        user_id = row.get("user_id")
        content = row.get("content") or ""
        if not user_id:
            continue
        try:
            did, reason = rewrite_one(client, user_id, content, dry_run=args.dry_run)
            if did:
                rewrote += 1
                logger.info("[%s] %s", user_id[:8], reason)
            else:
                skipped += 1
                logger.info("[%s] skipped: %s", user_id[:8], reason)
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.exception("[%s] failed: %s", user_id[:8], exc)

    logger.info("Done — rewrote=%d skipped=%d failed=%d", rewrote, skipped, failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
