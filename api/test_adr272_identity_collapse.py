"""ADR-272 Regression Gate — Identity-Layer Collapse Invariants.

UPDATED by the ADR-417 follow-on (2026-07-08): ADR-272 collapsed the specialist
roster to {"designer"}; ADR-417 retired the designer's asset-generation half
with the render service and its compose-only remainder is Reviewer-inline work,
so the follow-on collapses further to ZERO specialist roles. This gate now
asserts the empty-roster state and that DispatchSpecialist is REMOVED from the
LLM registry (dormant seam).

Asserts:
  1. VALID_SPECIALIST_ROLES is empty (designer removed — ADR-417 follow-on).
  2. PRODUCTION_ROLES dict is empty.
  3. ALL_ROLES has exactly {"thinking_partner"}.
  4. LEGACY_ROLE_MAP has only thinking_partner; legacy specialist targets
     (researcher/analyst/writer/tracker/executive/designer) are absent so
     legacy callers fail loudly through resolve_role()'s passthrough.
  5. orchestration_prompts.py is DELETED (the module no longer importable).
  6. agent_creation.py defines _DEFAULT_INSTRUCTIONS inline (thinking_partner).
  7. PRODUCTION_ROLE_SLUGS in agent_creation.py is empty.
  8. The alpha-trader bundle no longer declares the falsify-signals recurrence.
  9. DispatchSpecialist is REMOVED from the CHAT/HEADLESS/FREDDIE tool surfaces
     + HANDLERS (ADR-417 follow-on — zero roles to dispatch). Module + handler
     retained dormant as the seam a future role re-enters through.
 10. dispatch_specialist.py's VALID_SPECIALIST_ROLES enum is empty.

Phase 2 FE (deferred to follow-on commit) invariants — NOT asserted here:
  - chat bubble shapes collapse to {user-bubble, reviewer-bubble,
    agent-bubble, system-activity}
  - /agents roster does not include System Agent card
  - /agents?agent=system 404s cleanly

Run: cd api && python test_adr272_identity_collapse.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent

_passed = 0
_failed = 0


def assert_eq(actual, expected, msg):
    global _passed, _failed
    if actual == expected:
        print(f"  PASS  {msg}")
        _passed += 1
    else:
        print(f"  FAIL  {msg}\n         expected: {expected!r}\n         actual:   {actual!r}")
        _failed += 1


def assert_true(cond, msg):
    global _passed, _failed
    if cond:
        print(f"  PASS  {msg}")
        _passed += 1
    else:
        print(f"  FAIL  {msg}")
        _failed += 1


def test_valid_specialist_roles_narrowed():
    """ADR-417 follow-on: VALID_SPECIALIST_ROLES is empty (designer removed)."""
    from services.primitives.dispatch_specialist import VALID_SPECIALIST_ROLES
    assert_eq(
        VALID_SPECIALIST_ROLES, set(),
        "VALID_SPECIALIST_ROLES is empty (designer removed — ADR-417 follow-on)",
    )


def test_production_roles_narrowed():
    """ADR-417 follow-on: PRODUCTION_ROLES dict is empty."""
    from services.orchestration import PRODUCTION_ROLES
    assert_eq(
        set(PRODUCTION_ROLES.keys()), set(),
        "PRODUCTION_ROLES is empty (designer removed — ADR-417 follow-on)",
    )


def test_all_roles_surviving():
    """ADR-417 follow-on: ALL_ROLES = SYSTEMIC_AGENTS only = {thinking_partner}."""
    from services.orchestration import ALL_ROLES
    assert_eq(
        set(ALL_ROLES.keys()), {"thinking_partner"},
        "ALL_ROLES has exactly {thinking_partner} (PRODUCTION_ROLES empty)",
    )


def test_legacy_role_map_only_survivors():
    """ADR-417 follow-on: LEGACY_ROLE_MAP contains only thinking_partner."""
    from services.orchestration import LEGACY_ROLE_MAP
    legacy_targets = set(LEGACY_ROLE_MAP.values())
    assert_eq(
        legacy_targets, {"thinking_partner"},
        "LEGACY_ROLE_MAP targets only {thinking_partner} — specialist targets absent",
    )
    # Dissolved + designer roles must NOT be present as keys either (passthrough
    # to failed ALL_ROLES lookup is the discipline).
    for dissolved in ("researcher", "analyst", "writer", "tracker", "executive", "reporting", "designer"):
        assert_true(
            dissolved not in LEGACY_ROLE_MAP,
            f"LEGACY_ROLE_MAP does not map {dissolved!r} (loud failure preferred)",
        )


def test_orchestration_prompts_deleted():
    """Phase 1 sweep: orchestration_prompts.py removed (was dead-code legacy)."""
    try:
        import services.orchestration_prompts  # noqa: F401
        assert_true(
            False,
            "services.orchestration_prompts module should NOT be importable (deleted)",
        )
    except ImportError:
        assert_true(
            True,
            "services.orchestration_prompts is deleted (ImportError on import)",
        )


def test_agent_creation_module_deleted():
    """D7's DEFAULT_INSTRUCTIONS + ADR-417's PRODUCTION_ROLE_SLUGS both lived in
    services/agent_creation.py. Re-anchored 2026-08-26: that module is DELETED
    with the pre-ADR-596 agent model — it wrote rows to the `agents` table
    (dropped by migration 248) and its last caller was a dev script. Deletion
    subsumes both narrowings: an empty roster cannot be non-empty when the
    module holding it does not exist.
    """
    import importlib

    try:
        importlib.import_module("services.agent_creation")
        importable = True
    except ModuleNotFoundError:
        importable = False
    assert_true(
        not importable,
        "services.agent_creation is deleted (ModuleNotFoundError on import)",
    )
    from pathlib import Path
    root = Path(__file__).resolve().parent
    assert_true(
        not (root / "services" / "agent_creation.py").exists(),
        "services/agent_creation.py is absent from disk",
    )


def test_falsify_signals_recurrence_deleted():
    """ADR-272 D5: falsify-signals recurrence is deleted.

    Pre-ADR-275, ADR-272 absorbed falsify-signals' bootstrap-research
    intent into morning-reflection's prompt as a precondition.

    Post-ADR-275, morning-reflection itself is deleted — judgment
    cadence is Reviewer-authored, not bundle-scaffolded. Bootstrap
    research is the Reviewer's first-wake judgment call (informed by
    Operating Context + _preferences.yaml + IDENTITY + principles),
    not a precondition on a pre-scheduled morning ritual.

    This test now asserts both deletions: neither falsify-signals
    nor morning-reflection ship in the bundle. The Reviewer handles
    bootstrap research from cold-start judgment.
    """
    from services.recurrence import parse_recurrences_yaml

    bundle_path = (
        _REPO_ROOT.parent / "docs" / "programs" / "alpha-trader"
        / "reference-workspace" / "_recurrences.yaml"
    )
    parsed = parse_recurrences_yaml(bundle_path.read_text())
    slugs = {r.slug for r in parsed}
    assert_true(
        "falsify-signals" not in slugs,
        "alpha-trader bundle no longer declares falsify-signals recurrence",
    )
    assert_true(
        "morning-reflection" not in slugs,
        "alpha-trader bundle no longer declares morning-reflection (ADR-275)",
    )


def test_dispatch_specialist_primitive_preserved():
    """ADR-417 follow-on: DispatchSpecialist is REMOVED from every LLM surface
    (zero specialist roles). The module + handler stay dormant as a seam, but
    the primitive is not registered — an unusable tool must not be exposed."""
    from services.primitives.registry import (
        CHAT_PRIMITIVES,
        HEADLESS_PRIMITIVES,
        FREDDIE_PRIMITIVES,
        HANDLERS,
    )
    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}
    reviewer_names = {t["name"] for t in FREDDIE_PRIMITIVES}

    assert_true(
        "DispatchSpecialist" not in chat_names,
        "DispatchSpecialist removed from CHAT_PRIMITIVES (ADR-417 follow-on)",
    )
    assert_true(
        "DispatchSpecialist" not in headless_names,
        "DispatchSpecialist removed from HEADLESS_PRIMITIVES",
    )
    assert_true(
        "DispatchSpecialist" not in reviewer_names,
        "DispatchSpecialist removed from FREDDIE_PRIMITIVES",
    )
    assert_true(
        "DispatchSpecialist" not in HANDLERS,
        "DispatchSpecialist handler removed from HANDLERS",
    )


def test_record_task_run_preserves_activation_arming_on_capability_missing():
    """Cold-start ordering fix (2026-05-14): record_task_run must NOT
    consume `fire_on_activation` arming when the dispatch failed with
    error_reason='capability_missing'. Without this, operators who
    activate-before-connect have a silent workspace until next periodic
    cron — the flag is consumed by a failure that wasn't the work's fault.

    Asserts the function signature accepts `error_reason` and the
    source contains the preservation branch.
    """
    import inspect
    from services.scheduling import record_task_run
    sig = inspect.signature(record_task_run)
    assert_true(
        "error_reason" in sig.parameters,
        "record_task_run accepts error_reason keyword",
    )
    source = inspect.getsource(record_task_run)
    assert_true(
        'capability_missing' in source,
        "record_task_run source references capability_missing reason",
    )
    assert_true(
        'fire_on_activation' in source,
        "record_task_run source references fire_on_activation flag",
    )
    assert_true(
        "preserve_activation_arming" in source or "re-arms" in source.lower(),
        "record_task_run source documents the preservation branch (variable or comment)",
    )


def test_reviewer_prompt_defaults_to_inline():
    """ADR-272 inline-default, post-ADR-306 collapse: the inline-default
    discipline is no longer system prose (ablation §3 row 6: `production_default`
    is DELETE-REDUNDANT / code-enforced — "the model uses the tools it has").
    The discipline is now STRUCTURAL: the Reviewer's curated tool surface
    (`FREDDIE_PRIMITIVES`) carries the inline production tools directly, and
    `DispatchSpecialist`'s role enum is narrowed to `designer` (asserted by
    the sibling test_dispatch_specialist_tool_enum_narrowed). The model
    reaches for inline tools because those are the tools it has; designer
    dispatch is the one narrow exception encoded in the enum.
    """
    from services.primitives.registry import FREDDIE_PRIMITIVES

    names = {t["name"] for t in FREDDIE_PRIMITIVES}

    # Inline production tools present → inline IS the default by tool surface.
    for tool in ("WriteFile", "ReadFile", "SearchFiles", "WebSearch", "QueryKnowledge"):
        assert_true(
            tool in names,
            f"FREDDIE_PRIMITIVES must carry inline production tool {tool!r} "
            "(structural inline-default per ADR-272, replacing the deleted "
            "production_default prose per ADR-306 D3)",
        )
    # ADR-417 follow-on: DispatchSpecialist is REMOVED (zero specialist roles);
    # production work is fully inline via the tools above.
    assert_true(
        "DispatchSpecialist" not in names,
        "FREDDIE_PRIMITIVES must NOT carry DispatchSpecialist (ADR-417 follow-on "
        "— zero specialist roles; production work is inline)",
    )


def test_legacy_agents_router_deleted():
    """ADR-272 D7, re-anchored 2026-08-26: the orchestration LLM identity row
    was filtered out of /api/agents responses. That router is now DELETED in
    full (the pre-ADR-596 Scope x Role x Trigger model: 0 rows and 0 callers in
    production), which subsumes the filter — there is no response left to leak
    into. Asserting the DELETION rather than the filter is the stronger claim,
    and it is the one that stays true.
    """
    import os
    from pathlib import Path

    root = Path(__file__).resolve().parent
    assert_true(
        not (root / "routes" / "agents.py").exists(),
        "routes/agents.py is deleted (the retired agent model has no router)",
    )
    # And nothing mounts it. A stale `include_router` would be an ImportError
    # at boot, but a stale import line in the `from routes import ...` tuple is
    # the failure that actually happened before — so pin the mount too.
    main_src = (root / "main.py").read_text()
    assert_true(
        "agents.router" not in main_src,
        "main.py mounts no agents router",
    )
    # `thinking_partner` was the row the filter existed for. It must not come
    # back through any other door.
    assert_true(
        "thinking_partner" not in main_src,
        "main.py carries no thinking_partner carve-out",
    )


def test_dispatch_specialist_tool_enum_narrowed():
    """ADR-417 follow-on: the role enum reflects the empty VALID_SPECIALIST_ROLES."""
    from services.primitives.dispatch_specialist import DISPATCH_SPECIALIST_TOOL
    role_enum = (
        DISPATCH_SPECIALIST_TOOL.get("input_schema", {})
        .get("properties", {})
        .get("role", {})
        .get("enum", [])
    )
    assert_eq(
        list(role_enum), [],
        "DispatchSpecialist tool schema's role enum is empty (dormant — ADR-417 follow-on)",
    )


def main():
    tests = [
        test_valid_specialist_roles_narrowed,
        test_production_roles_narrowed,
        test_all_roles_surviving,
        test_legacy_role_map_only_survivors,
        test_orchestration_prompts_deleted,
        test_agent_creation_module_deleted,
        test_falsify_signals_recurrence_deleted,
        test_dispatch_specialist_primitive_preserved,
        test_dispatch_specialist_tool_enum_narrowed,
        test_legacy_agents_router_deleted,
        test_reviewer_prompt_defaults_to_inline,
        test_record_task_run_preserves_activation_arming_on_capability_missing,
    ]

    print("=" * 70)
    print("ADR-272 Identity-Layer Collapse — Phase 1 BE invariants")
    print("=" * 70)
    for t in tests:
        print(f"\n[{t.__name__}]")
        try:
            t()
        except Exception as e:
            print(f"  FAIL  {t.__name__} raised: {e}")
            globals()["_failed"] += 1

    print()
    print("=" * 70)
    print(f"ADR-272 regression gate: {_passed} passed, {_failed} failed")
    print("=" * 70)
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
