"""ADR-272 Regression Gate — Identity-Layer Collapse Invariants.

Phase 1 BE (this commit) — asserts:
  1. VALID_SPECIALIST_ROLES is exactly {"designer"}.
  2. PRODUCTION_ROLES dict has exactly one entry — "designer".
  3. ALL_ROLES has exactly {"designer", "thinking_partner"}.
  4. LEGACY_ROLE_MAP has only the two surviving roles (designer +
     thinking_partner); legacy targets (researcher/analyst/writer/tracker/
     executive) are absent so legacy callers fail loudly through
     resolve_role()'s passthrough.
  5. orchestration_prompts.py is DELETED (the module no longer importable).
  6. agent_creation.py defines _DEFAULT_INSTRUCTIONS inline with the two
     surviving roles.
  7. PRODUCTION_ROLE_SLUGS in agent_creation.py is {"designer"}.
  8. The alpha-trader bundle no longer declares the falsify-signals
     recurrence; its bootstrap-research intent moved into
     morning-reflection's prompt.
  9. DispatchSpecialist primitive infrastructure is PRESERVED — the
     primitive is still registered in CHAT/HEADLESS/REVIEWER tool surfaces,
     handler still in HANDLERS. Only the role catalog narrows.
 10. dispatch_specialist.py's tool schema enum lists exactly the surviving
     roles (sorted output of VALID_SPECIALIST_ROLES → ["designer"]).

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
    """D3: VALID_SPECIALIST_ROLES = {"designer"}."""
    from services.primitives.dispatch_specialist import VALID_SPECIALIST_ROLES
    assert_eq(
        VALID_SPECIALIST_ROLES, {"designer"},
        "VALID_SPECIALIST_ROLES is exactly {'designer'} (5 dissolved roles removed)",
    )


def test_production_roles_narrowed():
    """D3: PRODUCTION_ROLES dict has one entry — designer."""
    from services.orchestration import PRODUCTION_ROLES
    assert_eq(
        set(PRODUCTION_ROLES.keys()), {"designer"},
        "PRODUCTION_ROLES has exactly one key: 'designer'",
    )


def test_all_roles_surviving():
    """D3: ALL_ROLES = SYSTEMIC_AGENTS + PRODUCTION_ROLES = {designer, thinking_partner}."""
    from services.orchestration import ALL_ROLES
    assert_eq(
        set(ALL_ROLES.keys()), {"designer", "thinking_partner"},
        "ALL_ROLES has exactly {designer, thinking_partner}",
    )


def test_legacy_role_map_only_survivors():
    """D3: LEGACY_ROLE_MAP only contains the two surviving roles."""
    from services.orchestration import LEGACY_ROLE_MAP
    legacy_targets = set(LEGACY_ROLE_MAP.values())
    assert_eq(
        legacy_targets, {"designer", "thinking_partner"},
        "LEGACY_ROLE_MAP targets only {designer, thinking_partner} — dissolved targets absent",
    )
    # Dissolved roles must NOT be present as keys either (passthrough to
    # failed ALL_ROLES lookup is the discipline).
    for dissolved in ("researcher", "analyst", "writer", "tracker", "executive", "reporting"):
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


def test_default_instructions_inlined_to_agent_creation():
    """D7 doc cascade: DEFAULT_INSTRUCTIONS moved inline into agent_creation."""
    from services import agent_creation
    di = getattr(agent_creation, "_DEFAULT_INSTRUCTIONS", None)
    assert_true(
        di is not None,
        "agent_creation._DEFAULT_INSTRUCTIONS exists (inlined from deleted orchestration_prompts)",
    )
    if di is None:
        return
    assert_eq(
        set(di.keys()), {"designer", "thinking_partner"},
        "agent_creation._DEFAULT_INSTRUCTIONS keyed by the two surviving roles only",
    )


def test_production_role_slugs_narrowed():
    """D7 cascade: PRODUCTION_ROLE_SLUGS in agent_creation.py = {designer}."""
    from services.agent_creation import PRODUCTION_ROLE_SLUGS
    assert_eq(
        set(PRODUCTION_ROLE_SLUGS), {"designer"},
        "PRODUCTION_ROLE_SLUGS = {'designer'} (dissolved slugs removed)",
    )


def test_falsify_signals_recurrence_deleted():
    """D5: falsify-signals recurrence collapsed into morning-reflection."""
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
        "morning-reflection" in slugs,
        "alpha-trader bundle declares morning-reflection (absorbs bootstrap-research)",
    )
    mr = next(r for r in parsed if r.slug == "morning-reflection")
    assert_true(
        "read_trading" in set(mr.required_capabilities),
        "morning-reflection declares read_trading for bootstrap-research precondition",
    )
    assert_true(
        "/workspace/research/findings/" in mr.prompt or "bootstrap research" in mr.prompt.lower(),
        "morning-reflection prompt mentions bootstrap research path",
    )


def test_dispatch_specialist_primitive_preserved():
    """D4: DispatchSpecialist mechanism survives across all three caller surfaces."""
    from services.primitives.registry import (
        CHAT_PRIMITIVES,
        HEADLESS_PRIMITIVES,
        REVIEWER_PRIMITIVES,
        HANDLERS,
    )
    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}
    reviewer_names = {t["name"] for t in REVIEWER_PRIMITIVES}

    assert_true(
        "DispatchSpecialist" in chat_names,
        "DispatchSpecialist still in CHAT_PRIMITIVES (mechanism preserved)",
    )
    assert_true(
        "DispatchSpecialist" in headless_names,
        "DispatchSpecialist still in HEADLESS_PRIMITIVES",
    )
    assert_true(
        "DispatchSpecialist" in reviewer_names,
        "DispatchSpecialist still in REVIEWER_PRIMITIVES",
    )
    assert_true(
        "DispatchSpecialist" in HANDLERS,
        "DispatchSpecialist handler still in HANDLERS",
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
    """ADR-272 Phase 2 follow-up: Reviewer system prompt must explicitly
    instruct inline-default for non-asset production work. Without this,
    the Reviewer reaches for DispatchSpecialist(role='designer') when
    work is analyst/research-shaped — a semantic misroute observed live
    on 2026-05-14.
    """
    from agents.reviewer_agent import _PERSONA_FRAME
    assert_true(
        "INLINE execution" in _PERSONA_FRAME or "inline execution" in _PERSONA_FRAME.lower(),
        "Reviewer prompt explicitly names inline-default discipline",
    )
    assert_true(
        "ADR-272" in _PERSONA_FRAME,
        "Reviewer prompt cites ADR-272 as the source of the inline-default discipline",
    )
    assert_true(
        "asset rendering" in _PERSONA_FRAME.lower(),
        "Reviewer prompt names 'asset rendering' as the test for designer dispatch",
    )
    assert_true(
        "designer" in _PERSONA_FRAME,
        "Reviewer prompt names `designer` as the surviving specialist role",
    )


def test_list_agents_filters_orchestration_row():
    """ADR-272 D1 + D7 (Phase 2 BE): the orchestration LLM identity row
    (role='thinking_partner') is filtered out of /api/agents responses.
    The FE never sees it; System Agent no longer surfaces as a peer entity.
    Asserts by source-text inspection (no live DB call needed).
    """
    import inspect
    from routes.agents import list_agents
    source = inspect.getsource(list_agents)
    # The filter expression should EXCLUDE thinking_partner explicitly
    assert_true(
        'a.get("role") != "thinking_partner"' in source,
        "list_agents filter excludes role='thinking_partner' (ADR-272 D7)",
    )
    # And should NOT preserve thinking_partner via the legacy ADR-214 carve-out
    legacy_carveout = 'a.get("origin") != "system_bootstrap" or a.get("role") == "thinking_partner"'
    assert_true(
        legacy_carveout not in source,
        "legacy ADR-214 carve-out (thinking_partner kept regardless of origin) removed",
    )


def test_dispatch_specialist_tool_enum_narrowed():
    """D3: tool schema's role enum reflects the narrowed VALID_SPECIALIST_ROLES."""
    from services.primitives.dispatch_specialist import DISPATCH_SPECIALIST_TOOL
    role_enum = (
        DISPATCH_SPECIALIST_TOOL.get("input_schema", {})
        .get("properties", {})
        .get("role", {})
        .get("enum", [])
    )
    assert_eq(
        list(role_enum), ["designer"],
        "DispatchSpecialist tool schema's role enum is exactly ['designer']",
    )


def main():
    tests = [
        test_valid_specialist_roles_narrowed,
        test_production_roles_narrowed,
        test_all_roles_surviving,
        test_legacy_role_map_only_survivors,
        test_orchestration_prompts_deleted,
        test_default_instructions_inlined_to_agent_creation,
        test_production_role_slugs_narrowed,
        test_falsify_signals_recurrence_deleted,
        test_dispatch_specialist_primitive_preserved,
        test_dispatch_specialist_tool_enum_narrowed,
        test_list_agents_filters_orchestration_row,
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
