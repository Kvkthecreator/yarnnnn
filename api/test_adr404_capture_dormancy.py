"""ADR-404 D2 / ADR-591 — capture-lane dormancy regression gate.

ADR-404 D2 put a capture lane DORMANT for the commons-first launch. ADR-591
then split what that flag actually gated: the CONNECTOR walk, its digest
walker, and the raw-lane GC are DELETED outright (capture is consumer-
invoked, D2/D3), while the ADR-393 DECLARATION lane — a different lane with
different tenants (ground-truth mirrors, perception watches) — keeps its own
dormancy under `CAPTURE_LANE_ENABLED`.

This gate locks what survives:

1. The `is_capture_lane_enabled()` resolver — default OFF when unset, ON only
   on an explicit true token; unrecognized values fail safe to OFF.
2. The scheduler holds exactly ONE gated capture block (the ADR-393 drain)
   and NO connector job of any kind.
3. No seeding exists in the routes (ADR-582 D2 deleted it outright — the
   strongest form of the cut).
4. Hide-not-revert, for what is hidden rather than deleted: the capture lane
   modules and the connector WRITER modules stay importable. The walkers are
   gone by decision (ADR-591), which is a re-cut, not a dormancy cut.

Run: python3 api/test_adr404_capture_dormancy.py
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
        os.environ.pop("CAPTURE_LANE_ENABLED", None)
    else:
        os.environ["CAPTURE_LANE_ENABLED"] = value


# =============================================================================
# Group 1 — the resolver (default OFF; explicit true → ON; fail-safe OFF)
# =============================================================================


def test_resolver() -> None:
    print("\n[1] is_capture_lane_enabled() resolver — default OFF (ADR-404 D2)")
    from services.capture_lane_gating import is_capture_lane_enabled as is_connector_capture_enabled

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
    print("\n[2] scheduler — one gated lane, and NO connector job (ADR-591)")
    src = (_API_ROOT / "jobs" / "unified_scheduler.py").read_text()

    _assert(
        "is_capture_lane_enabled" in src,
        "unified_scheduler imports the ADR-393 lane resolver",
    )
    _assert(
        "if is_capture_lane_enabled():" in src,
        "the declaration-capture drain is gated on it",
    )
    # ADR-591: the connector has NO scheduled job. Each of these names would
    # be a clock reintroducing itself.
    for dead in ("drain_due_connector_captures", "drain_due_connector_derives",
                 "prune_raw_lane", "gather_cited_raw_paths",
                 "CONNECTOR_CAPTURE_ENABLED", "connector_capture_gating"):
        _assert(dead not in src, f"no {dead} in the scheduler (ADR-591)")


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
    # ADR-591 D5: there is no capture flag to surface. The field is pinned
    # False for not-yet-deployed clients; nothing may resurrect a resolver.
    _assert(
        "is_connector_capture_enabled" not in src,
        "the routes consult NO capture resolver (ADR-591 D5)",
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
        # ADR-582 deleted capture_connector + connector_watch; ADR-591
        # deleted the walkers inside these. The modules themselves survive —
        # they hold the WRITERS a consumer invokes (D3).
        "services.connectors",
        "services.connector_derive",
        "services.connector_retention",
        "services.capture_lane_gating",
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
