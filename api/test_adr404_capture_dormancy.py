"""ADR-404 D2 — connector-capture dormancy regression gate.

The commons-first launch (ADR-404) puts the connector capture lane DORMANT
behind `CONNECTOR_CAPTURE_ENABLED` (default OFF — dormancy is the ratified
decision, inverting the AGENT_ENABLED default-ON rationale). This gate locks
the dormant-state contract:

1. The `is_connector_capture_enabled()` resolver — default OFF when unset,
   ON only on an explicit true token; unrecognized values fail safe to OFF.
2. Cut site #1 — the scheduler consults the resolver for BOTH the capture
   drain and the connector raw-lane GC (source inspection).
3. Cut site #2 — the seed-at-select route consults the resolver; disconnect
   teardown (`remove_connector_capture`) stays UNGUARDED (cleanup always
   works).
4. Cut site #3 — the capture-signal endpoint surfaces
   `connector_capture_enabled` for the FE (source inspection).
5. Hide-not-revert invariant — every capture module survives intact and
   importable: `services.capture.*`, `connectors`, `connector_derive`,
   `connector_retention`. Dormant, not deleted. (ADR-582 deleted
   `capture_connector` + `connector_watch` outright — that deletion is a
   re-cut, not a dormancy cut, and is gated by test_adr392/test_adr582.)

Run: .venv/bin/python api/test_adr404_capture_dormancy.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

_API_ROOT = Path(__file__).resolve().parent

_passed = 0
_failed = 0


def _assert(cond: bool, msg: str) -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {msg}")
    else:
        _failed += 1
        print(f"  FAIL  {msg}")


def _set_flag(value: str | None) -> None:
    if value is None:
        os.environ.pop("CONNECTOR_CAPTURE_ENABLED", None)
    else:
        os.environ["CONNECTOR_CAPTURE_ENABLED"] = value


# =============================================================================
# Group 1 — the resolver (default OFF; explicit true → ON; fail-safe OFF)
# =============================================================================


def test_resolver() -> None:
    print("\n[1] is_connector_capture_enabled() resolver — default OFF (ADR-404 D2)")
    from services.connector_capture_gating import is_connector_capture_enabled

    _set_flag(None)
    _assert(is_connector_capture_enabled() is False, "unset → OFF (dormancy is the decision)")

    for tok in ("1", "true", "yes", "on", "TRUE", " On "):
        _set_flag(tok)
        _assert(is_connector_capture_enabled() is True, f"explicit true token {tok!r} → ON")

    for tok in ("0", "false", "no", "off", "False"):
        _set_flag(tok)
        _assert(is_connector_capture_enabled() is False, f"explicit false token {tok!r} → OFF")

    for tok in ("maybe", "", "  "):
        _set_flag(tok)
        _assert(
            is_connector_capture_enabled() is False,
            f"unrecognized token {tok!r} → OFF (fail-safe toward dormancy)",
        )

    _set_flag(None)


# =============================================================================
# Group 2 — cut sites consult the resolver (source inspection)
# =============================================================================


def test_scheduler_cut_sites() -> None:
    print("\n[2] scheduler cut sites — drain + GC gated as a unit")
    src = (_API_ROOT / "jobs" / "unified_scheduler.py").read_text()

    _assert(
        "is_connector_capture_enabled" in src,
        "unified_scheduler imports the resolver",
    )
    # Every connector-lane block is behind the same computed flag variable:
    # the declaration-capture drain, the ADR-582 connector capture walk, the
    # raw-lane GC, and the ADR-580 digest drain.
    _assert(
        src.count("if capture_lane_on:") == 4,
        "exactly four blocks (capture drain + connector walk + GC + digest) "
        "gate on capture_lane_on",
    )
    # Ordering: the flag is computed before the drain call.
    _assert(
        src.index("capture_lane_on = is_connector_capture_enabled()")
        < src.index("drain_due_captures"),
        "flag computed before the drain call",
    )


def test_seed_and_signal_cut_sites() -> None:
    print("\n[3] route cut sites — no seeding exists, signal surfaced")
    src = (_API_ROOT / "routes" / "integrations.py").read_text()

    # ADR-582 D2: seed-at-select is DELETED, which is the strongest form of
    # the dormancy cut — saving a selection touches nothing but the landscape
    # row, flag on or off. Nothing may quietly reintroduce a seed.
    _assert(
        "seed_connector_capture" not in src
        and "remove_connector_capture" not in src,
        "no capture seeding/teardown exists in the routes (ADR-582 D2)",
    )
    # The capture-signal endpoint surfaces the flag for the FE.
    _assert(
        '"connector_capture_enabled": is_connector_capture_enabled()' in src,
        "capture-signal response carries connector_capture_enabled",
    )


# =============================================================================
# Group 3 — hide-not-revert: every capture module intact + importable
# =============================================================================


def test_modules_survive() -> None:
    print("\n[4] hide-not-revert — capture modules intact and importable")
    import importlib

    for mod in (
        "services.capture.lane",
        "services.capture.declarations",
        "services.capture.scheduling",
        "services.capture.drainer",
        # ADR-582: capture_connector + connector_watch are DELETED (not
        # hidden); the connector lane's live modules are these two.
        "services.connectors",
        "services.connector_derive",
        "services.connector_retention",
    ):
        try:
            importlib.import_module(mod)
            _assert(True, f"{mod} imports")
        except Exception as exc:  # noqa: BLE001
            _assert(False, f"{mod} imports ({exc})")


def main() -> int:
    print("=" * 72)
    print("ADR-404 D2 — connector-capture dormancy gate")
    print("=" * 72)

    test_resolver()
    test_scheduler_cut_sites()
    test_seed_and_signal_cut_sites()
    test_modules_survive()

    print("\n" + "=" * 72)
    print(f"RESULT: {_passed} passed, {_failed} failed")
    print("=" * 72)
    return 1 if _failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
