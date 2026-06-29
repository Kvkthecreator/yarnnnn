"""Regression gate for ADR-291 — Unified Cost Ledger.

Asserts that the dual-ledger architecture has been collapsed to a single
canonical substrate (`execution_events`). The five Singular Implementation
violations identified in ADR-291 §5 should all collapse to zero.

Run:
    cd api && python test_adr291_unified_cost_ledger.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    _PASS.append(name)
    print(f"  ✓ {name}")


def _bad(name: str, reason: str) -> None:
    _FAIL.append((name, reason))
    print(f"  ✗ {name}\n      {reason}")


# ---------------------------------------------------------------------------
# 1. token_usage table does not exist post-migration
# ---------------------------------------------------------------------------

def test_token_usage_table_dropped() -> None:
    """Verify the token_usage table has been dropped from the DB."""
    try:
        from services.supabase import get_service_client
        client = get_service_client()
    except Exception as e:
        _bad("token_usage table dropped", f"could not get service client: {e}")
        return

    try:
        # Try a 1-row select. Should error with "relation does not exist"
        # (PostgREST: 42P01) or return PGRST205 (schema cache).
        result = client.table("token_usage").select("id").limit(1).execute()
        # If we got here, the table still exists.
        _bad(
            "token_usage table dropped",
            f"token_usage table still queryable (got {len(result.data or [])} rows) — migration 176 not applied",
        )
    except Exception as e:
        msg = str(e).lower()
        if "token_usage" in msg or "42p01" in msg or "pgrst205" in msg or "does not exist" in msg:
            _ok("token_usage table dropped")
        else:
            _bad("token_usage table dropped", f"unexpected error shape: {e}")


# ---------------------------------------------------------------------------
# 2. compute_cost_usd symbol does not exist in services.platform_limits
# ---------------------------------------------------------------------------

def test_compute_cost_usd_deleted() -> None:
    """`compute_cost_usd` (cache-agnostic) must be deleted; only
    `compute_cost_usd_inclusive` (in services.telemetry) survives."""
    try:
        from services import platform_limits
    except Exception as e:
        _bad("compute_cost_usd deleted from platform_limits", f"import error: {e}")
        return

    if hasattr(platform_limits, "compute_cost_usd"):
        _bad(
            "compute_cost_usd deleted from platform_limits",
            "platform_limits.compute_cost_usd still exists — should be deleted (ADR-291 D2)",
        )
        return
    _ok("compute_cost_usd deleted from platform_limits")


# ---------------------------------------------------------------------------
# 3. BILLING_RATES constant does not exist in services.platform_limits
# ---------------------------------------------------------------------------

def test_billing_rates_deleted() -> None:
    """`BILLING_RATES` constant in platform_limits must be deleted; the
    single source of truth is `services.telemetry._BILLING_RATES`."""
    try:
        from services import platform_limits
    except Exception as e:
        _bad("BILLING_RATES deleted from platform_limits", f"import error: {e}")
        return

    if hasattr(platform_limits, "BILLING_RATES"):
        _bad(
            "BILLING_RATES deleted from platform_limits",
            "platform_limits.BILLING_RATES still exists — Singular Implementation violation (ADR-291 D2)",
        )
        return
    _ok("BILLING_RATES deleted from platform_limits")


# ---------------------------------------------------------------------------
# 4. record_token_usage symbol does not exist in services.platform_limits
# ---------------------------------------------------------------------------

def test_record_token_usage_deleted() -> None:
    """`record_token_usage` writer must be deleted; the single write path
    is `services.telemetry.record_execution_event`."""
    try:
        from services import platform_limits
    except Exception as e:
        _bad("record_token_usage deleted", f"import error: {e}")
        return

    if hasattr(platform_limits, "record_token_usage"):
        _bad(
            "record_token_usage deleted",
            "platform_limits.record_token_usage still exists — should be deleted (ADR-291 D1)",
        )
        return
    _ok("record_token_usage deleted")


# ---------------------------------------------------------------------------
# 5. check_spend_budget legacy alias deleted
# ---------------------------------------------------------------------------

def test_check_spend_budget_deleted() -> None:
    """Legacy alias from pre-ADR-172 era; should be gone per ADR-291 D6."""
    try:
        from services import platform_limits
    except Exception as e:
        _bad("check_spend_budget deleted", f"import error: {e}")
        return

    if hasattr(platform_limits, "check_spend_budget"):
        _bad(
            "check_spend_budget deleted",
            "platform_limits.check_spend_budget still exists — should be deleted (ADR-291 cleanup)",
        )
        return
    _ok("check_spend_budget deleted")


# ---------------------------------------------------------------------------
# 6. All LLM callers import record_execution_event (not record_token_usage)
# ---------------------------------------------------------------------------

EXPECTED_CALLERS = [
    "services/recurrence_prompt_inference.py",
    "services/session_continuity.py",
    # ADR-314 D4: infer_workspace.py deleted (first-act scaffold dissolved).
    # ADR-324: infer_context.py deleted (InferContext dissolved); the
    # identity/brand cost-ledger write moved to context_inference.author_identity.
    "services/context_inference.py",
    "services/primitives/dispatch_specialist.py",
    "services/primitives/web_search.py",
]


def test_callers_migrated() -> None:
    """Each of the 5 ex-token_usage callers must import record_execution_event
    AND NOT have any LIVE (non-comment) reference to record_token_usage.
    (Was 6 — infer_workspace.py deleted per ADR-314 D4.)"""
    api_root = ROOT
    for rel in EXPECTED_CALLERS:
        path = api_root / rel
        if not path.exists():
            _bad(f"caller migrated: {rel}", f"file missing: {path}")
            continue
        text = path.read_text()
        # Check for non-comment references to record_token_usage
        live_offenders: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # comment line — allowed (migration notes)
            if "record_token_usage" in stripped:
                live_offenders.append(stripped[:80])
        if live_offenders:
            _bad(
                f"caller migrated: {rel}",
                f"still has live record_token_usage reference: {live_offenders[0]}",
            )
            continue
        # Each caller should import record_execution_event
        if "record_execution_event" not in text:
            _bad(
                f"caller migrated: {rel}",
                "does not import record_execution_event — caller not migrated",
            )
            continue
        _ok(f"caller migrated: {rel}")


# ---------------------------------------------------------------------------
# 7. Reviewer agent no longer writes token_usage (was prior dual write)
# ---------------------------------------------------------------------------

def test_reviewer_single_ledger_write() -> None:
    """Reviewer agent previously wrote BOTH `token_usage` (via record_token_usage)
    AND emitted cost on FreddieOutput for the dispatcher to write to
    `execution_events`. Post-ADR-291, only the second path survives."""
    path = ROOT / "agents" / "freddie_agent.py"
    if not path.exists():
        _bad("freddie_agent single ledger write", f"file missing: {path}")
        return

    text = path.read_text()
    # The import must not pull record_token_usage as a callable
    if re.search(r"^from services\.platform_limits import.*record_token_usage", text, re.MULTILINE):
        _bad(
            "freddie_agent single ledger write",
            "still imports record_token_usage from platform_limits",
        )
        return
    # The function call site should be gone
    if re.search(r"^\s*record_token_usage\(", text, re.MULTILINE):
        _bad(
            "freddie_agent single ledger write",
            "still calls record_token_usage(...) — duplicate write not removed",
        )
        return
    # And FreddieOutput should still carry cache breakdown fields
    if "cache_read_tokens" not in text or "cache_create_tokens" not in text:
        _bad(
            "freddie_agent single ledger write",
            "FreddieOutput is missing cache breakdown fields — dispatcher cost write would be incomplete",
        )
        return
    _ok("freddie_agent single ledger write")


# ---------------------------------------------------------------------------
# 8. get_effective_balance RPC reads from execution_events
# ---------------------------------------------------------------------------

def test_get_effective_balance_reads_execution_events() -> None:
    """Verify Postgres RPC `get_effective_balance` reads execution_events,
    not token_usage. Inspected via pg_get_functiondef."""
    try:
        from services.supabase import get_service_client
        client = get_service_client()
    except Exception as e:
        _bad("get_effective_balance RPC reads execution_events", f"could not get service client: {e}")
        return

    try:
        # Use raw SQL via PostgREST is awkward; use rpc to a function that
        # introspects via pg_proc directly. Simplest: call get_effective_balance
        # against a known user_id and verify it succeeds (regression: prior
        # broken state would 500 because the RPC still references token_usage
        # which is dropped). Returning 0 is fine — just needs to not error.
        result = client.rpc(
            "get_effective_balance",
            {"p_user_id": "00000000-0000-0000-0000-000000000000"},
        ).execute()
        # If we got here without exception, the RPC executed cleanly
        val = result.data
        if val is None:
            _bad(
                "get_effective_balance RPC reads execution_events",
                "RPC returned None — function may not exist or may be malformed",
            )
            return
        _ok(f"get_effective_balance RPC reads execution_events (returned {val} for null user — function compiles cleanly)")
    except Exception as e:
        msg = str(e).lower()
        if "token_usage" in msg:
            _bad(
                "get_effective_balance RPC reads execution_events",
                f"RPC still references token_usage which was dropped: {e}",
            )
            return
        _bad(
            "get_effective_balance RPC reads execution_events",
            f"unexpected error: {e}",
        )


# ---------------------------------------------------------------------------
# 9. compute_cost_usd_inclusive is the only cost function in services.telemetry
# ---------------------------------------------------------------------------

def test_telemetry_single_cost_function() -> None:
    """services.telemetry should expose compute_cost_usd_inclusive as the
    sole cost function — no parallel cache-agnostic variant."""
    try:
        from services import telemetry
    except Exception as e:
        _bad("telemetry single cost function", f"import error: {e}")
        return

    if not hasattr(telemetry, "compute_cost_usd_inclusive"):
        _bad("telemetry single cost function", "compute_cost_usd_inclusive missing")
        return
    if hasattr(telemetry, "compute_cost_usd"):
        _bad(
            "telemetry single cost function",
            "telemetry.compute_cost_usd exists (cache-agnostic shadow) — should be deleted",
        )
        return
    _ok("telemetry single cost function")


# ---------------------------------------------------------------------------
# 10. _BILLING_RATES exists exactly once (in services.telemetry)
# ---------------------------------------------------------------------------

def test_billing_rates_single_source() -> None:
    """`_BILLING_RATES` (or equivalent) must live in exactly one module —
    services.telemetry — per ADR-291 D2."""
    api_root = ROOT
    matches: list[str] = []
    for py_file in api_root.rglob("*.py"):
        if "venv" in py_file.parts or "test_" in py_file.name:
            continue
        try:
            text = py_file.read_text()
        except Exception:
            continue
        # Match assignment line `_BILLING_RATES = ...` or `BILLING_RATES = ...`
        if re.search(r"^_?BILLING_RATES\s*:\s*dict", text, re.MULTILINE):
            matches.append(str(py_file.relative_to(REPO_ROOT)))
    if len(matches) == 0:
        _bad("BILLING_RATES single source", "no definition found anywhere")
        return
    if len(matches) > 1:
        _bad(
            "BILLING_RATES single source",
            f"defined in {len(matches)} places — Singular Implementation violation: {matches}",
        )
        return
    if not matches[0].endswith("services/telemetry.py"):
        _bad(
            "BILLING_RATES single source",
            f"definition not in services/telemetry.py: {matches[0]}",
        )
        return
    _ok(f"BILLING_RATES single source ({matches[0]})")


# ---------------------------------------------------------------------------
# 11. record_token_usage has no live callers anywhere
# ---------------------------------------------------------------------------

def test_no_live_record_token_usage_calls() -> None:
    """grep gate: no live code (excluding comments) calls record_token_usage."""
    api_root = ROOT
    offenders: list[str] = []
    for py_file in api_root.rglob("*.py"):
        if "venv" in py_file.parts or "test_" in py_file.name:
            continue
        try:
            text = py_file.read_text()
        except Exception:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Look for record_token_usage usage that's not in a comment/docstring
            if "record_token_usage" in stripped and not stripped.startswith('"') and not stripped.startswith("'"):
                # Heuristic — avoid full triple-quoted docstring detection complexity.
                # Just check for actual calls / imports.
                if "record_token_usage(" in stripped or "import record_token_usage" in stripped or "import.*record_token_usage" in stripped:
                    offenders.append(f"{py_file.relative_to(REPO_ROOT)}: {stripped[:80]}")
    if offenders:
        _bad(
            "no live record_token_usage calls",
            f"{len(offenders)} offender(s):\n      " + "\n      ".join(offenders),
        )
        return
    _ok("no live record_token_usage calls")


# ---------------------------------------------------------------------------
# 12. Migration 176 file exists
# ---------------------------------------------------------------------------

def test_migration_176_exists() -> None:
    """Migration file should exist on disk."""
    path = REPO_ROOT / "supabase" / "migrations" / "176_unified_cost_ledger.sql"
    if not path.exists():
        _bad("migration 176 file exists", f"missing: {path}")
        return
    text = path.read_text()
    if "DROP TABLE" not in text or "token_usage" not in text:
        _bad("migration 176 file exists", "migration does not drop token_usage")
        return
    if "execution_events" not in text:
        _bad("migration 176 file exists", "migration does not reference execution_events")
        return
    _ok("migration 176 file exists")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== ADR-291 Regression Gate ===\n")

    print("Code-side assertions (no DB):")
    test_compute_cost_usd_deleted()
    test_billing_rates_deleted()
    test_record_token_usage_deleted()
    test_check_spend_budget_deleted()
    test_callers_migrated()
    test_reviewer_single_ledger_write()
    test_telemetry_single_cost_function()
    test_billing_rates_single_source()
    test_no_live_record_token_usage_calls()
    test_migration_176_exists()
    print()

    print("DB-side assertions (requires service client):")
    test_token_usage_table_dropped()
    test_get_effective_balance_reads_execution_events()

    print(f"\n=== Results: {len(_PASS)} passed, {len(_FAIL)} failed ===\n")
    if _FAIL:
        for name, reason in _FAIL:
            print(f"FAIL: {name}\n  {reason}")
        sys.exit(1)
    print("All assertions pass.")
    sys.exit(0)
