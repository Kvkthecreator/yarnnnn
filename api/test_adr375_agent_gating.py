"""ADR-375 §6 — steward-presence gate regression gate.

Phase 1 (ADR-375) defines YARNNN positively as *the file-system-native
substrate operated by humans AND external agents as principals*; the internal
steward (the Reviewer — future "Freddie") ships dormant behind `AGENT_ENABLED`.
This gate locks the off-state contract:

1. The `is_agent_enabled()` resolver — default ON when unset (D4), OFF only on
   an explicit false token; unrecognized values fail safe to ON.
2. Chokepoint #4 — `kernel_surface_entries()` filters out exactly the
   steward-coupled surfaces when off, and retains every keeper (ledger +
   membrane + constitution mirrors + chrome).
3. Chokepoint #2 — `submit_wake_proposal` no-ops (no enqueue) when off; the
   MCP→wake adapter, reaching the queue only via this fn, is covered.
4. The OFF-state INVARIANT (ADR-375 D3): a substrate write still commits +
   attributes when the steward is off — the write path (`write_revision`) does
   NOT consult the gate. Asserted structurally (the producer is decoupled from
   the consumer; ADR-209/307 untouched).
5. Chokepoints #1 / #3 are guarded against `is_agent_enabled` — asserted by
   source inspection (the scheduler steward block + the feed addressed path
   both consult the resolver).

Run: .venv/bin/python api/test_adr375_agent_gating.py
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Make `services.*` importable when running from project root.
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
        os.environ.pop("AGENT_ENABLED", None)
    else:
        os.environ["AGENT_ENABLED"] = value


# =============================================================================
# Group 1 — the resolver (D4: default ON; explicit false → OFF; fail-safe ON)
# =============================================================================


def test_resolver_default_on() -> None:
    print("\n[1] is_agent_enabled() resolver — default ON (D4)")
    from services.agent_gating import is_agent_enabled

    _set_flag(None)
    _assert(is_agent_enabled() is True, "unset → ON (isolation seam, not a behavior flip)")

    for tok in ("false", "0", "no", "off", "FALSE", "Off"):
        _set_flag(tok)
        _assert(is_agent_enabled() is False, f"AGENT_ENABLED={tok!r} → OFF")

    for tok in ("true", "1", "yes", "on", "TRUE"):
        _set_flag(tok)
        _assert(is_agent_enabled() is True, f"AGENT_ENABLED={tok!r} → ON")

    for tok in ("garbage", "", "  "):
        _set_flag(tok)
        _assert(
            is_agent_enabled() is True,
            f"AGENT_ENABLED={tok!r} (unrecognized) → fail-safe ON",
        )

    # workspace_id is accepted (forward-compatible) and does not change the
    # per-deploy answer today.
    _set_flag("false")
    _assert(
        is_agent_enabled(workspace_id="any-ws") is False,
        "workspace_id arg accepted (forward-compat), reads env only today",
    )
    _set_flag(None)


# =============================================================================
# Group 2 — chokepoint #4: kernel_surface_entries() filter
# =============================================================================


def test_surface_filter() -> None:
    print("\n[2] chokepoint #4 — kernel_surface_entries() steward-surface filter")
    import services.kernel_surfaces as ks
    importlib.reload(ks)

    steward = set(ks.STEWARD_SURFACE_SLUGS)
    _assert(
        steward == {
            "agents", "queue", "notifications", "autonomy",
            "program", "recurrence", "expected-output", "activity",
        },
        f"STEWARD_SURFACE_SLUGS is the ADR-375 §6 set ({sorted(steward)})",
    )

    _set_flag(None)  # ON
    on_slugs = {e["slug"] for e in ks.kernel_surface_entries()}
    _assert(
        steward <= on_slugs,
        "ON (default): full registry — every steward surface present",
    )
    _assert(
        len(on_slugs) == len(ks.KERNEL_SURFACES),
        "ON: entry count == full KERNEL_SURFACES (nothing filtered)",
    )

    _set_flag("false")  # OFF
    off_slugs = {e["slug"] for e in ks.kernel_surface_entries()}
    removed = on_slugs - off_slugs
    _assert(
        removed == steward,
        f"OFF: removes EXACTLY the steward set (removed={sorted(removed)})",
    )

    keepers = {
        # ADR-415 (2026-07-08): `channels` DELETED (Channels dissolved). Its
        # connectors/sources panes survive, re-homed to workspace-settings.
        "files", "connectors", "sources",
        "settings", "workspace-settings",
        "identity", "mandate", "principles", "home", "budget",
        "top-bar", "launcher", "chat-drawer", "setup",
    }
    missing_keepers = keepers - off_slugs
    _assert(
        not missing_keepers,
        f"OFF: every keeper survives (missing={sorted(missing_keepers) or 'none'})",
    )
    _assert(
        not (off_slugs & steward),
        "OFF: no steward surface leaks into the filtered registry",
    )

    _set_flag(None)
    back_on = {e["slug"] for e in ks.kernel_surface_entries()}
    _assert(
        steward <= back_on,
        "Toggle back to ON: steward surfaces return (reversible, no deletion — D5)",
    )

    # kernel_surface_slugs() is the canonical declaration — unfiltered always.
    _set_flag("false")
    _assert(
        steward <= ks.kernel_surface_slugs(),
        "kernel_surface_slugs() stays unfiltered (canonical declaration, not the nav view)",
    )
    _set_flag(None)


# =============================================================================
# Group 3 — chokepoint #2: submit_wake_proposal no-ops when off
# =============================================================================


def test_wake_enqueue_gate() -> None:
    print("\n[3] chokepoint #2 — submit_wake_proposal no-ops when off")
    import asyncio
    from services import wake as wake_mod

    # A client whose .table(...).insert(...).execute() would raise if reached —
    # proves the off-state path never touches the DB / enqueue.
    sentinel = MagicMock()
    sentinel.table.side_effect = AssertionError(
        "submit_wake_proposal reached the DB while AGENT_ENABLED=off"
    )

    _set_flag("false")
    result = asyncio.get_event_loop().run_until_complete(
        wake_mod.submit_wake_proposal(
            sentinel,
            "user-123",
            source="substrate_event",
            payload={"hook": {}, "path": "x", "field_change": {}, "revision_id": "r"},
        )
    )
    _assert(
        result.get("success") is True and result.get("skipped") == "agent_disabled",
        f"OFF: returns no-op {{success, skipped:agent_disabled}} (got {result})",
    )
    _assert(
        not sentinel.table.called,
        "OFF: no enqueue — the wake gateway never touches the queue",
    )
    _set_flag(None)


# =============================================================================
# Group 4 — the OFF-state invariant + chokepoint source-presence
# =============================================================================


def test_write_path_does_not_consult_gate() -> None:
    print("\n[4a] ADR-375 D3 invariant — the write path does NOT consult the gate")
    src = (_API_ROOT / "services" / "authored_substrate.py").read_text()
    _assert(
        "is_agent_enabled" not in src and "agent_gating" not in src,
        "write_revision() / authored_substrate.py never imports the gate "
        "(a foreign/agent write still commits + attributes when off — D3)",
    )


def test_chokepoints_present_in_source() -> None:
    print("\n[4b] chokepoints #1 + #3 consult is_agent_enabled (source inspection)")

    sched = (_API_ROOT / "jobs" / "unified_scheduler.py").read_text()
    _assert(
        "from services.agent_gating import is_agent_enabled" in sched
        and "if is_agent_enabled():" in sched,
        "#1 scheduler: the steward block (dispatch+walker+drain+mirrors) is gated",
    )
    # The three named calls must sit INSIDE the gate (after the if), as a unit.
    # Search the gated region only (text after the `if`), so a symbol's earlier
    # mention in the module docstring/comments doesn't false-negative.
    gate_idx = sched.index("if is_agent_enabled():")
    gated_region = sched[gate_idx:]
    for sym in ("dispatch_due_invocations(supabase)", "await walk_hooks(", "drain_all_users_with_pending("):
        _assert(
            sym in gated_region,
            f"#1: {sym} is inside the gate (walker+drain gated as a unit, not drain-only)",
        )

    feed = (_API_ROOT / "routes" / "feed.py").read_text()
    _assert(
        "is_agent_enabled" in feed
        and "_dispatch_reviewer_turn" in feed
        and feed.index("is_agent_enabled(workspace_id=auth.user_id)")
        < feed.rindex("_dispatch_reviewer_turn(images_for_api, invocation_id)"),
        "#3 feed: the addressed path is guarded BEFORE _dispatch_reviewer_turn",
    )


# =============================================================================
# Run
# =============================================================================


if __name__ == "__main__":
    try:
        test_resolver_default_on()
        test_surface_filter()
        test_wake_enqueue_gate()
        test_write_path_does_not_consult_gate()
        test_chokepoints_present_in_source()
    finally:
        _set_flag(None)

    print(f"\n{'='*64}")
    print(f"ADR-375 agent-gating regression gate: {_passed} passed, {_failed} failed")
    print(f"{'='*64}")
    sys.exit(0 if _failed == 0 else 1)
