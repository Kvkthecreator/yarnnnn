"""
Validation Suite — Commit F (autonomy schema alignment)

Asserts the autonomy mode is wired end-to-end after Commit F. The defect
this guards against:

  Pre-Commit-F (2026-05-07 → 2026-05-11), the FE wrote
  `level: bounded_autonomous` to _autonomy.yaml on every operator
  selection. The backend `_validate_autonomy_block` reads `delegation:`
  (3-value enum), defaulted missing field to `manual`, logged a warning,
  and `should_auto_execute_verdict` correctly refused to auto-execute.
  The autonomy mode UI was COSMETIC for ~5 days — operators picking
  "Bounded" or "Autonomous" got the same backend behavior as "Manual."

  Migration 172 + the FE/BE rewrite in Commit F (cbe32d6) unified the
  schema. This gate prevents the defect from re-introducing.

Tests:
  1. _VALID_DELEGATION_LEVELS == {manual, bounded, autonomous} (3 values)
  2. _validate_autonomy_block reads `delegation` and rejects unknown values
  3. should_auto_execute_verdict — manual defers
  4. should_auto_execute_verdict — bounded + within ceiling auto-executes
  5. should_auto_execute_verdict — bounded + over ceiling defers
  6. should_auto_execute_verdict — autonomous + reversible auto-executes
  7. should_auto_execute_verdict — irreversible always defers regardless of delegation
  8. should_auto_execute_verdict — paused_until in future defers (Commit G)
  9. should_auto_execute_verdict — paused_until in past does NOT defer
 10. Live data: every _autonomy.yaml in production carries `delegation:`
     (no legacy `level:` survivors after Migration 172)
 11. Live alpha-trader-2 round-trip: load_autonomy returns {delegation, ceiling_cents}
     in canonical shape; the gate fires correctly on a synthetic verdict

Strategy: Pure-Python contract assertions for tests 1-9 (no DB required);
real DB reads via service key for tests 10-11.

Usage:
    cd api && python test_commit_f_autonomy_alignment.py
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key] = value

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Live alpha-trader-2 — used for the round-trip test only
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


def get_client():
    """Supabase service-role client (bypasses RLS — safe in this test context)."""
    from supabase import create_client
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL + SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


# =============================================================================
# Tests 1-2: contract on the validator
# =============================================================================


def test_valid_delegation_levels_is_three_values():
    from services.review_policy import _VALID_DELEGATION_LEVELS

    expected = {"manual", "bounded", "autonomous"}
    actual = set(_VALID_DELEGATION_LEVELS)
    if actual == expected:
        record("1. _VALID_DELEGATION_LEVELS is canonical 3-value set", True, str(sorted(actual)))
    else:
        record(
            "1. _VALID_DELEGATION_LEVELS is canonical 3-value set",
            False,
            f"expected {sorted(expected)}, got {sorted(actual)} — drift would mean either re-adding a removed value (assisted/bounded_autonomous) or removing a valid one",
        )


def test_validate_autonomy_block_reads_delegation():
    from services.review_policy import _validate_autonomy_block

    # Canonical shape — should pass through unchanged
    canonical = {"delegation": "bounded", "ceiling_cents": 20000}
    result = _validate_autonomy_block(canonical, "default")
    if result.get("delegation") == "bounded" and result.get("ceiling_cents") == 20000:
        record("2a. _validate_autonomy_block accepts canonical {delegation, ceiling_cents}", True, str(result))
    else:
        record(
            "2a. _validate_autonomy_block accepts canonical {delegation, ceiling_cents}",
            False,
            f"got {result}",
        )

    # Unknown delegation value → defaults to manual
    bad = {"delegation": "bounded_autonomous"}  # legacy 4-value name
    result = _validate_autonomy_block(bad, "default")
    if result.get("delegation") == "manual":
        record("2b. _validate_autonomy_block rejects legacy 'bounded_autonomous' value", True, "→ manual")
    else:
        record(
            "2b. _validate_autonomy_block rejects legacy 'bounded_autonomous' value",
            False,
            f"got {result}",
        )

    # Missing delegation field — _validate_autonomy_block intentionally
    # leaves the field absent (the validator only normalizes invalid
    # values; it doesn't synthesize missing ones). Downstream
    # should_auto_execute_verdict uses its own .get("delegation", "manual")
    # default. Assert the gate's downstream defaulting works on a missing
    # field, which is the contract that actually matters end-to-end.
    from services.review_policy import should_auto_execute_verdict
    missing = {"ceiling_cents": 20000}  # no delegation field
    validated = _validate_autonomy_block(missing, "default")
    ok, reason = should_auto_execute_verdict(validated, verdict="approve", estimated_cents=100, reversibility="reversible")
    if not ok and "manual" in reason.lower():
        record("2c. missing-delegation field still defers via downstream default", True, reason)
    else:
        record(
            "2c. missing-delegation field still defers via downstream default",
            False,
            f"validated={validated} ok={ok} reason={reason}",
        )


# =============================================================================
# Tests 3-7: should_auto_execute_verdict gate logic
# =============================================================================


def test_gate_manual_defers():
    from services.review_policy import should_auto_execute_verdict

    policy = {"delegation": "manual"}
    ok, reason = should_auto_execute_verdict(policy, verdict="approve", estimated_cents=100, reversibility="reversible")
    if not ok and "manual" in reason.lower():
        record("3. gate(manual) defers", True, reason)
    else:
        record("3. gate(manual) defers", False, f"ok={ok} reason={reason}")


def test_gate_bounded_within_ceiling_auto_executes():
    from services.review_policy import should_auto_execute_verdict

    policy = {"delegation": "bounded", "ceiling_cents": 20000}
    ok, reason = should_auto_execute_verdict(policy, verdict="approve", estimated_cents=1500, reversibility="reversible")
    if ok:
        record("4. gate(bounded, $15 within $200 ceiling, reversible) auto-executes", True, reason)
    else:
        record("4. gate(bounded, $15 within $200 ceiling, reversible) auto-executes", False, f"reason={reason}")


def test_gate_bounded_over_ceiling_defers():
    from services.review_policy import should_auto_execute_verdict

    policy = {"delegation": "bounded", "ceiling_cents": 20000}
    ok, reason = should_auto_execute_verdict(policy, verdict="approve", estimated_cents=50000, reversibility="reversible")
    if not ok and "ceiling" in reason.lower():
        record("5. gate(bounded, $500 over $200 ceiling) defers", True, reason)
    else:
        record("5. gate(bounded, $500 over $200 ceiling) defers", False, f"ok={ok} reason={reason}")


def test_gate_autonomous_reversible_auto_executes():
    from services.review_policy import should_auto_execute_verdict

    policy = {"delegation": "autonomous"}
    ok, reason = should_auto_execute_verdict(policy, verdict="approve", estimated_cents=99999999, reversibility="reversible")
    if ok:
        record("6. gate(autonomous, reversible) auto-executes regardless of value", True, reason)
    else:
        record("6. gate(autonomous, reversible) auto-executes regardless of value", False, f"reason={reason}")


def test_gate_irreversible_always_defers():
    from services.review_policy import should_auto_execute_verdict

    # Even autonomous + small value defers when irreversible
    policy = {"delegation": "autonomous"}
    ok, reason = should_auto_execute_verdict(policy, verdict="approve", estimated_cents=100, reversibility="irreversible")
    if not ok and "irreversible" in reason.lower():
        record("7. gate(autonomous, irreversible) defers regardless", True, reason)
    else:
        record("7. gate(autonomous, irreversible) defers regardless", False, f"ok={ok} reason={reason}")


# =============================================================================
# Tests 8-9: pause field gating (Commit G — pause supersedes delegation)
# =============================================================================


def test_gate_pause_in_future_defers():
    from services.review_policy import should_auto_execute_verdict

    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    # Even autonomous + reversible + within ceiling defers when paused
    policy = {
        "delegation": "autonomous",
        "paused_until": future,
        "pause_reason": "test pause",
    }
    ok, reason = should_auto_execute_verdict(policy, verdict="approve", estimated_cents=100, reversibility="reversible")
    if not ok and "paus" in reason.lower():
        record("8. gate(paused_until in future) defers with pause reason", True, reason[:120])
    else:
        record("8. gate(paused_until in future) defers with pause reason", False, f"ok={ok} reason={reason}")


def test_gate_pause_expired_does_not_defer():
    from services.review_policy import should_auto_execute_verdict

    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    policy = {
        "delegation": "bounded",
        "ceiling_cents": 20000,
        "paused_until": past,
        "pause_reason": "expired pause",
    }
    ok, reason = should_auto_execute_verdict(policy, verdict="approve", estimated_cents=1500, reversibility="reversible")
    if ok:
        record("9. gate(paused_until in past) does NOT defer", True, reason)
    else:
        record("9. gate(paused_until in past) does NOT defer", False, f"ok={ok} reason={reason}")


# =============================================================================
# Tests 10-11: live production data shape (post-Migration-172)
# =============================================================================


def test_live_no_legacy_level_survivors():
    """Every _autonomy.yaml in production should carry `delegation:` (canonical)
    and NOT carry `level:` or `heartbeat_triggers:` (legacy schemas dropped)."""
    try:
        client = get_client()
    except Exception as exc:
        record("10. live: no legacy `level:` survivors in _autonomy.yaml", False, f"client init failed: {exc}")
        return

    rows = (
        client.table("workspace_files")
        .select("user_id,content")
        .eq("path", "/workspace/governance/_autonomy.yaml")
        .execute()
    ).data or []

    if not rows:
        record(
            "10. live: no legacy `level:` survivors in _autonomy.yaml",
            True,
            "0 _autonomy.yaml files in production (vacuously true; gate stands by)",
        )
        return

    legacy_hits: list[str] = []
    canonical_count = 0
    for row in rows:
        user_id = row.get("user_id", "?")
        content = row.get("content") or ""
        # Indented `level:` (under default/domains, not in a comment)
        has_legacy_level = False
        for line in content.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if line.startswith("  ") and stripped.startswith("level:"):
                has_legacy_level = True
                break
        has_heartbeat = "heartbeat_triggers:" in content
        has_canonical = "delegation:" in content
        if has_legacy_level or has_heartbeat or not has_canonical:
            legacy_hits.append(
                f"user={user_id[:8]} legacy_level={has_legacy_level} heartbeat={has_heartbeat} canonical={has_canonical}"
            )
        else:
            canonical_count += 1

    if not legacy_hits:
        record(
            "10. live: no legacy `level:` survivors in _autonomy.yaml",
            True,
            f"{canonical_count}/{len(rows)} files canonical",
        )
    else:
        record(
            "10. live: no legacy `level:` survivors in _autonomy.yaml",
            False,
            f"{len(legacy_hits)} legacy file(s): {legacy_hits[:3]}",
        )


def test_live_alpha_trader_round_trip():
    """Load alpha-trader-2's live _autonomy.yaml via the backend reader and
    confirm the gate fires correctly on a synthetic verdict — the same end-
    to-end verification we did manually in F.6."""
    try:
        client = get_client()
        from services.review_policy import load_autonomy, autonomy_for_domain, should_auto_execute_verdict

        autonomy = load_autonomy(client, TEST_USER_ID)
        if not autonomy or not autonomy.get("default"):
            record(
                "11. live: alpha-trader-2 round-trip — gate fires correctly",
                False,
                f"load_autonomy returned empty or missing default: {autonomy}",
            )
            return

        policy = autonomy_for_domain(autonomy, "trading")
        if policy.get("delegation") not in {"manual", "bounded", "autonomous"}:
            record(
                "11. live: alpha-trader-2 round-trip — gate fires correctly",
                False,
                f"loaded delegation not canonical: {policy.get('delegation')!r}",
            )
            return

        # Small-value reversible — should auto-execute under bounded
        small_ok, small_reason = should_auto_execute_verdict(
            policy, verdict="approve", estimated_cents=100, reversibility="reversible",
        )
        # Large-value reversible — should defer (over ceiling)
        big_ok, big_reason = should_auto_execute_verdict(
            policy, verdict="approve", estimated_cents=99999, reversibility="reversible",
        )

        delegation = policy.get("delegation")
        ceiling = policy.get("ceiling_cents") or 0

        if delegation == "bounded" and ceiling > 0:
            # Tightest assertion: small must auto, big must defer
            if small_ok and not big_ok:
                record(
                    "11. live: alpha-trader-2 round-trip — gate fires correctly",
                    True,
                    f"delegation={delegation} ceiling=${ceiling/100:.2f} | small($1)={small_ok} big($999)={big_ok}",
                )
            else:
                record(
                    "11. live: alpha-trader-2 round-trip — gate fires correctly",
                    False,
                    f"delegation={delegation} ceiling=${ceiling/100:.2f} BUT small={small_ok}/{small_reason!r} big={big_ok}/{big_reason!r}",
                )
        elif delegation == "autonomous":
            if small_ok and big_ok:
                record(
                    "11. live: alpha-trader-2 round-trip — gate fires correctly",
                    True,
                    f"delegation=autonomous | small={small_ok} big={big_ok} (both auto)",
                )
            else:
                record(
                    "11. live: alpha-trader-2 round-trip — gate fires correctly",
                    False,
                    f"delegation=autonomous BUT small={small_ok} big={big_ok} (expected both auto)",
                )
        elif delegation == "manual":
            if not small_ok and not big_ok:
                record(
                    "11. live: alpha-trader-2 round-trip — gate fires correctly",
                    True,
                    f"delegation=manual | both defer as expected",
                )
            else:
                record(
                    "11. live: alpha-trader-2 round-trip — gate fires correctly",
                    False,
                    f"delegation=manual BUT small={small_ok} big={big_ok} (expected both defer)",
                )
        else:
            record(
                "11. live: alpha-trader-2 round-trip — gate fires correctly",
                False,
                f"unexpected delegation={delegation!r}",
            )
    except Exception as exc:
        record("11. live: alpha-trader-2 round-trip — gate fires correctly", False, f"exception: {exc}")


# =============================================================================
# Driver
# =============================================================================


def main() -> int:
    print("=== Commit F autonomy alignment regression gate ===")
    print()

    # Pure-contract tests (no DB)
    test_valid_delegation_levels_is_three_values()
    test_validate_autonomy_block_reads_delegation()
    test_gate_manual_defers()
    test_gate_bounded_within_ceiling_auto_executes()
    test_gate_bounded_over_ceiling_defers()
    test_gate_autonomous_reversible_auto_executes()
    test_gate_irreversible_always_defers()
    test_gate_pause_in_future_defers()
    test_gate_pause_expired_does_not_defer()

    # Live-data tests (require Supabase service key)
    test_live_no_legacy_level_survivors()
    test_live_alpha_trader_round_trip()

    print()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    total = len(RESULTS)
    print(f"=== {passed}/{total} passed, {failed} failed ===")
    if failed:
        print()
        print("Failures:")
        for name, ok, detail in RESULTS:
            if not ok:
                print(f"  ✗ {name} — {detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
