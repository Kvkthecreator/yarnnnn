#!/usr/bin/env python3
"""
Verify a persona workspace matches its declared invariants.

Usage:
    python -m api.scripts.alpha_ops.verify alpha-trader
    python -m api.scripts.alpha_ops.verify alpha-commerce
    python -m api.scripts.alpha_ops.verify --all

Read-only. Uses the Supabase service-role key to inspect the DB directly
(the same access pattern the user and Claude already share via
docs/database/ACCESS.md). No JWT required.

Checks, per persona:
    - agent_count matches expected
    - active_bots are active (not paused)
    - essential_tasks exist and are status=active, essential=true
    - scaffolded_tasks exist (status may be paused, e.g. trading-sync)
    - platform_connections count matches, provider + metadata match
    - core workspace files present
    - context_domains scaffolded

Exit code 0 = all invariants hold, 1 = one or more failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared import Persona, load_registry, pg_connect  # noqa: E402


class Check:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passes: list[str] = []

    def assert_(self, cond: bool, msg: str) -> None:
        """Neutral framing — message should read correctly either way (e.g.
        'got X, expected Y')."""
        (self.passes if cond else self.failures).append(msg)

    def present(self, cond: bool, subject: str) -> None:
        """Presence check — 'X present' on pass, 'X missing' on fail."""
        if cond:
            self.passes.append(f"{subject} present")
        else:
            self.failures.append(f"{subject} missing")


def _verify_one(cur, persona: Persona) -> Check:
    check = Check()
    uid = persona.user_id
    exp = persona.expected

    # Agents.
    cur.execute("SELECT role, status FROM agents WHERE user_id=%s", (uid,))
    rows = cur.fetchall()
    by_role = {r[0]: r[1] for r in rows}
    check.assert_(
        len(rows) == exp.get("agent_count"),
        f"agent_count: got {len(rows)}, expected {exp.get('agent_count')}",
    )
    for bot in exp.get("active_bots", []):
        status = by_role.get(bot)
        check.assert_(status == "active", f"bot {bot}: status={status} (expected active)")

    # Tasks.
    cur.execute(
        "SELECT slug, status, essential FROM tasks WHERE user_id=%s",
        (uid,),
    )
    tasks = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    for slug in exp.get("essential_tasks", []):
        t = tasks.get(slug)
        check.assert_(
            t is not None and t[0] == "active" and t[1] is True,
            f"essential task '{slug}': {t} (expected status=active, essential=True)",
        )
    for slug in exp.get("scaffolded_tasks", []):
        check.present(slug in tasks, f"scaffolded task '{slug}'")

    # Platform connections.
    cur.execute(
        "SELECT platform, status, metadata FROM platform_connections WHERE user_id=%s",
        (uid,),
    )
    conns = cur.fetchall()
    check.assert_(
        len(conns) == exp.get("platform_connections"),
        f"platform_connections count: got {len(conns)}, expected {exp.get('platform_connections')}",
    )
    for platform, status, metadata in conns:
        meta = metadata if isinstance(metadata, dict) else (json.loads(metadata) if metadata else {})
        check.assert_(
            platform == persona.platform_kind and status == "active",
            f"connection {platform}: status={status} (expected active, kind={persona.platform_kind})",
        )
        check.assert_(
            meta.get("provider") == persona.platform_provider,
            f"connection provider: got {meta.get('provider')}, expected {persona.platform_provider}",
        )
        # Trading-specific sanity: account suffix.
        if persona.platform_kind == "trading":
            acct = meta.get("account_number")
            check.assert_(
                acct == persona.platform.get("account_suffix"),
                f"trading account_number: got {acct}, expected {persona.platform.get('account_suffix')}",
            )

    # Core files.
    cur.execute(
        "SELECT path FROM workspace_files WHERE user_id=%s",
        (uid,),
    )
    paths = {r[0] for r in cur.fetchall()}
    for core in exp.get("core_files", []):
        check.present(core in paths, f"core file {core}")

    # Risk file (may lack leading slash — documented in persona yaml).
    risk = exp.get("risk_md_path")
    if risk:
        check.present(risk in paths, f"risk file {risk}")

    # Context domain stubs: at least one file present under each domain.
    for domain in persona.context_domains:
        has_files = any(p.startswith(f"/workspace/context/{domain}/") for p in paths)
        check.present(has_files, f"context domain '{domain}' files under /workspace/context/{domain}/")

    return check


def _print(label: str, check: Check) -> None:
    print(f"\n{'=' * 72}")
    print(f"{label}")
    print(f"{'=' * 72}")
    for p in check.passes:
        print(f"  OK   {p}")
    for f in check.failures:
        print(f"  FAIL {f}")
    total = len(check.passes) + len(check.failures)
    print(f"\n  {len(check.passes)}/{total} checks passed")


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify persona workspace invariants.")
    ap.add_argument("persona", nargs="?", help="Persona slug (omit with --all)")
    ap.add_argument("--all", action="store_true", help="Verify every persona in the registry")
    args = ap.parse_args()

    if not args.all and not args.persona:
        ap.error("provide a persona slug or --all")

    registry = load_registry()
    slugs = list(registry.personas.keys()) if args.all else [args.persona]

    any_fail = False
    with pg_connect() as conn:
        with conn.cursor() as cur:
            for slug in slugs:
                persona = registry.require(slug)
                check = _verify_one(cur, persona)
                _print(f"{persona.slug}  —  {persona.label}", check)
                if check.failures:
                    any_fail = True

    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
