# ─────────────────────────────────────────────────────────────────────────
# ADR-626 D4.b (2026-09-01) — SIX DispatchSpecialist TESTS DELETED HERE.
# ─────────────────────────────────────────────────────────────────────────
# They exercised the primitive's internals (schema, capability pass-through,
# message append, tool-result access, cache_control, per-recurrence max_rounds).
# `primitives/dispatch_specialist.py` is DELETED — role-keyed dispatch was
# superseded by capability-at-the-app (ADR-601/603 D2), and its role set had
# been the EMPTY SET since ADR-417's follow-on, so none of these paths could
# run. The ADR-269 capability FLOW they belonged to survives and is still
# asserted below for the live tool surfaces.
"""Regression gate for ADR-269 — Capability-Flow Wiring.

Verifies the chain that delivers `required_capabilities` from a recurrence's
YAML declaration to the specialist sub-LLM-call's tool surface.

Run: cd api && PYTHONPATH=. .venv/bin/python test_adr269_capability_flow.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_REPO_ROOT))

from services.recurrence import Recurrence, parse_recurrences_yaml  # noqa: E402

PASSED = 0
FAILED: list[str] = []


def assert_eq(actual, expected, msg):
    global PASSED
    if actual == expected:
        PASSED += 1
    else:
        FAILED.append(f"{msg}\n  actual:   {actual}\n  expected: {expected}")


def assert_true(cond, msg):
    global PASSED
    if cond:
        PASSED += 1
    else:
        FAILED.append(msg)


def test_recurrence_dataclass_has_required_capabilities():
    """Dataclass carries `required_capabilities: list[str]` field."""
    rec = Recurrence(slug="t", schedule="0 7 * * *", prompt="x")
    assert_eq(rec.required_capabilities, [], "default is empty list")

    rec2 = Recurrence(
        slug="t", schedule="0 7 * * *", prompt="x",
        required_capabilities=["read_trading", "write_trading"],
    )
    assert_eq(
        rec2.required_capabilities,
        ["read_trading", "write_trading"],
        "explicit list stored",
    )


def test_parser_reads_required_capabilities():
    """YAML body's `required_capabilities:` flows into the dataclass."""
    yaml_content = """
recurrences:
  - slug: trading-eval
    schedule: "0 9 * * *"
    prompt: "evaluate signals"
    mode: judgment
    required_capabilities: [read_trading, write_trading]

  - slug: housekeeping
    schedule: "0 3 * * *"
    prompt: "daily digest"
    mode: judgment
"""
    parsed = parse_recurrences_yaml(yaml_content)
    by_slug = {r.slug: r for r in parsed}
    assert_eq(len(parsed), 2, "two recurrences parsed")
    assert_eq(
        by_slug["trading-eval"].required_capabilities,
        ["read_trading", "write_trading"],
        "trading-eval required_capabilities parsed",
    )
    assert_eq(
        by_slug["housekeeping"].required_capabilities,
        [],
        "housekeeping default is empty list",
    )


def test_parser_coerces_invalid_types_to_empty():
    """Non-list / non-string-members are coerced to empty list (with warning)."""
    yaml_content = """
recurrences:
  - slug: bad-type
    schedule: "0 7 * * *"
    prompt: "x"
    required_capabilities: "read_trading"

  - slug: mixed-members
    schedule: "0 7 * * *"
    prompt: "x"
    required_capabilities: [read_trading, 42, "", "write_trading"]
"""
    parsed = parse_recurrences_yaml(yaml_content)
    by_slug = {r.slug: r for r in parsed}
    assert_eq(
        by_slug["bad-type"].required_capabilities,
        [],
        "string instead of list -> empty",
    )
    assert_eq(
        by_slug["mixed-members"].required_capabilities,
        ["read_trading", "write_trading"],
        "mixed-type members filtered to strings only",
    )


def test_dispatcher_threads_capabilities_into_context():
    # 2026-06-04: the reactive dispatch path moved from the deleted
    # services/invocation_dispatcher.py into services/wake.py (ADR-296 v2 →
    # ADR-298 wake-architecture migration). The capability-threading shape
    # survived verbatim; only the file moved.
    dispatcher_src = (_REPO_ROOT / "services" / "wake.py").read_text()
    assert_true(
        "recurrence_required_capabilities" in dispatcher_src,
        "dispatcher source threads recurrence_required_capabilities",
    )
    assert_true(
        "list(recurrence.required_capabilities)" in dispatcher_src,
        "dispatcher reads from recurrence.required_capabilities",
    )


def test_reviewer_reads_capabilities_from_context():
    reviewer_src = (_REPO_ROOT / "agents" / "freddie_agent.py").read_text()
    assert_true(
        "recurrence_required_capabilities" in reviewer_src,
        "reviewer reads recurrence_required_capabilities from context",
    )
    assert_true(
        "Required capabilities for dispatched specialists" in reviewer_src,
        "reviewer surfaces capabilities section in system context",
    )


def test_alpha_trader_bundle_declares_capabilities():
    bundle_path = (
        _REPO_ROOT.parent / "docs" / "programs" / "alpha-trader"
        / "reference-workspace" / "_recurrences.yaml"
    )
    content = bundle_path.read_text()
    parsed = parse_recurrences_yaml(content)
    by_slug = {r.slug: r for r in parsed}

    # ADR-271 Thread A: track-universe + track-regime migrated from
    # judgment-mode (with required_capabilities) to mechanical-mode
    # (no LLM tool surface — primitive handles its own credentials).
    # They now live alongside track-positions / track-account / track-orders
    # in the mechanical-mirror class.
    expected = {
        "signal-evaluation": {"read_trading"},
        "outcome-reconciliation": {"read_trading"},
        "trade-proposal": {"read_trading", "write_trading"},
    }
    for slug, expected_caps in expected.items():
        rec = by_slug.get(slug)
        assert_true(rec is not None, f"recurrence {slug!r} present in bundle")
        if rec is None:
            continue
        actual_caps = set(rec.required_capabilities)
        assert_true(
            expected_caps.issubset(actual_caps),
            f"recurrence {slug!r} declares {expected_caps} (got {actual_caps})",
        )

    # ADR-272: morning-reflection now declares read_trading because the
    # bootstrap-research precondition (absorbed from the deleted
    # falsify-signals recurrence) fetches platform bars when findings/ is
    # empty. Removed from housekeeping_slugs list for that reason.
    housekeeping_slugs = [
        "narrative-digest", "morning-calibration",
        "proposal-cleanup", "pre-market-brief", "weekly-performance-review",
        "quarterly-signal-audit",
    ]
    for slug in housekeeping_slugs:
        rec = by_slug.get(slug)
        if rec is None:
            continue
        assert_true(
            "read_trading" not in rec.required_capabilities,
            f"housekeeping recurrence {slug!r} does NOT declare read_trading",
        )

    # ADR-271 Thread A: mechanical-mirror class now includes track-universe
    # and track-regime alongside the original three account/order/position
    # mirrors. All mechanical-mode recurrences: zero LLM, primitive loads
    # its own credentials, no required_capabilities on the recurrence record.
    mirror_slugs = [
        "track-positions", "track-account", "track-orders",
        "track-universe", "track-regime",
    ]
    for slug in mirror_slugs:
        rec = by_slug.get(slug)
        if rec is None:
            continue
        assert_eq(
            rec.required_capabilities, [],
            f"mechanical mirror {slug!r} has empty required_capabilities",
        )
        assert_eq(
            rec.mode, "mechanical",
            f"mechanical mirror {slug!r} has mode=mechanical",
        )


def test_alpha_trader_autonomy_is_autonomous():
    import yaml as _yaml
    path = (
        _REPO_ROOT.parent / "docs" / "programs" / "alpha-trader"
        / "reference-workspace" / "context" / "_shared" / "_autonomy.yaml"
    )
    content = path.read_text()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]
    parsed = _yaml.safe_load(content)
    default = parsed.get("default", {})
    assert_eq(
        default.get("delegation"), "autonomous",
        "delegation is autonomous",
    )
    assert_true(
        default.get("ceiling_cents", 0) >= 2000000,
        f"ceiling_cents admits Signal-1 notional (got {default.get('ceiling_cents')!r}, want >= 2000000)",
    )
    never_auto = default.get("never_auto", [])
    assert_true(
        "close_position_market" in never_auto,
        "close_position_market still in never_auto (hard safety floor)",
    )


def test_workspace_init_skips_bundle_owned_paths():
    """workspace_init source skips kernel-default seeds for paths the
    bundle's reference-workspace owns. Surfaced by iter-4 AUTONOMY flip
    not propagating on re-fork (kernel `delegation: manual` blocked
    bundle's `delegation: autonomous` from landing)."""
    src = (_REPO_ROOT / "services" / "workspace_init.py").read_text()
    assert_true(
        "bundle_owned_paths" in src,
        "workspace_init has bundle_owned_paths skip logic",
    )
    assert_true(
        "bundle '{program_slug}' will fork canonical content" in src
        or "bundle will fork canonical content" in src,
        "workspace_init logs the skip rationale",
    )
    assert_true(
        "_bundle_root_dir" in src,
        "workspace_init imports _bundle_root_dir to enumerate bundle files",
    )


def test_alpha_trader_bundle_parses_cleanly():
    bundle_path = (
        _REPO_ROOT.parent / "docs" / "programs" / "alpha-trader"
        / "reference-workspace" / "_recurrences.yaml"
    )
    content = bundle_path.read_text()
    parsed = parse_recurrences_yaml(content)
    assert_true(len(parsed) > 0, "bundle parses to non-empty list")
    for rec in parsed:
        assert_true(isinstance(rec, Recurrence), f"{rec.slug} is Recurrence")
        assert_true(
            isinstance(rec.required_capabilities, list),
            f"{rec.slug} required_capabilities is list",
        )


def test_reviewer_threads_recurrence_options_onto_auth():
    """Regression: dispatcher → invoke_freddie → auth.recurrence_options.

    The Reviewer's tool dispatch builds a SimpleNamespace auth. For
    per-recurrence specialist budgets to take effect, the Reviewer must
    copy recurrence options from its context envelope onto auth before
    invoking tools. Without this hop, max_rounds declared in the bundle
    YAML never reaches handle_dispatch_specialist.
    """
    from agents import freddie_agent
    import inspect

    source = inspect.getsource(freddie_agent)
    # `auth = SimpleNamespace(... recurrence_options=...)` is the
    # threading pattern. We don't pin a specific line shape, just that
    # the name `recurrence_options` appears in the auth construction.
    assert_true(
        "recurrence_options" in source,
        "freddie_agent threads recurrence_options onto auth",
    )


def test_reviewer_system_prompt_has_cache_control():
    """Regression for the Reviewer-side caching gap surfaced by cf5bb69 audit.

    Background: cf5bb69 fixed specialist-side caching (dispatch_specialist).
    Render log audit on seulkim88 verified Sonnet specialist hits 59-67%
    cache on rounds 2+. SAME audit found Haiku Reviewer was uncached on
    every call (every [TOKENS] line: cache_create=0 cache_read=0
    cache_hit=0% with 15-23K input tokens). Same root cause:
    freddie_agent._build_system_prompt() returned plain str — Anthropic's
    prompt-caching beta header attached but no cache_control markers on
    static content.

    This test verifies _build_system_prompt() returns the structured
    content-blocks shape with cache_control on the static frame block —
    not a plain str. Same canonical pattern as
    test_dispatch_specialist_system_prompt_has_cache_control above.
    """
    from agents.freddie_agent import _build_system_prompt

    result = _build_system_prompt()
    assert_true(isinstance(result, list), "system prompt is a list of content blocks")
    assert_true(len(result) >= 1, "at least one content block")
    assert_eq(result[0].get("type"), "text", "first block is text-typed")
    assert_true("cache_control" in result[0], "first block carries cache_control marker")
    assert_eq(
        result[0].get("cache_control"),
        {"type": "ephemeral"},
        "cache_control is the ephemeral shape Anthropic recognizes",
    )


def test_alpha_trader_heavy_recurrences_declare_max_rounds():
    """Bundle-level: heavy judgment recurrences declare per-recurrence round
    budgets matching their observed workload size.

    ADR-271 Thread A: track-universe migrated to deterministic (no specialist
    dispatch, no max_rounds). ADR-393: it moved out of _recurrences.yaml
    entirely into _captures.yaml (the capture lane) — a recurrence is now
    judgment-only. Only judgment recurrences remain in scope here.
    """
    from services.recurrence import parse_recurrences_yaml
    from services.capture.declarations import parse_captures_yaml
    import os

    ref = os.path.join(
        os.path.dirname(__file__), "..",
        "docs", "programs", "alpha-trader", "reference-workspace",
    )
    with open(os.path.join(ref, "_recurrences.yaml"), encoding="utf-8") as f:
        parsed = parse_recurrences_yaml(f.read())
    by_slug = {r.slug: r for r in parsed}
    with open(os.path.join(ref, "_captures.yaml"), encoding="utf-8") as f:
        caps = {c.slug for c in parse_captures_yaml(f.read())}

    # ADR-393: track-universe is a CAPTURE now, not a recurrence. It runs in
    # the capture lane (deterministic, no specialist, no max_rounds).
    assert_true(
        "track-universe" not in by_slug,
        "track-universe is no longer a recurrence (ADR-393: moved to _captures.yaml)",
    )
    assert_true(
        "track-universe" in caps,
        "alpha-trader bundle declares track-universe as a capture (ADR-393)",
    )

    # ADR-272 deleted falsify-signals (collapsed into morning-reflection
    # precondition). ADR-275 then deleted morning-reflection itself —
    # judgment cadence is Reviewer-authored, not bundle-scaffolded.
    # Bootstrap research is the Reviewer's first-wake judgment call.
    # Assert both deletions; no heavy-judgment recurrence remains in
    # the bundle to test max_rounds against (and that's the point).
    assert_true(
        "falsify-signals" not in by_slug,
        "alpha-trader bundle no longer declares falsify-signals (ADR-272 collapse)",
    )
    assert_true(
        "morning-reflection" not in by_slug,
        "alpha-trader bundle no longer declares morning-reflection (ADR-275)",
    )


def main():
    tests = [
        test_recurrence_dataclass_has_required_capabilities,
        test_parser_reads_required_capabilities,
        test_parser_coerces_invalid_types_to_empty,
        test_dispatch_specialist_schema_accepts_required_capabilities,
        test_dispatcher_threads_capabilities_into_context,
        test_reviewer_reads_capabilities_from_context,
        test_handle_dispatch_specialist_passes_capabilities,
        test_alpha_trader_bundle_declares_capabilities,
        test_alpha_trader_autonomy_is_autonomous,
        test_workspace_init_skips_bundle_owned_paths,
        test_alpha_trader_bundle_parses_cleanly,
        test_dispatch_specialist_message_append_uses_response_content,
        test_dispatch_specialist_tool_execution_uses_attribute_access,
        test_dispatch_specialist_system_prompt_has_cache_control,
        test_dispatch_specialist_honors_per_recurrence_max_rounds,
        test_reviewer_threads_recurrence_options_onto_auth,
        test_reviewer_system_prompt_has_cache_control,
        test_alpha_trader_heavy_recurrences_declare_max_rounds,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            FAILED.append(f"{t.__name__} crashed: {type(e).__name__}: {e}")

    print(f"\nADR-269 regression gate: {PASSED} assertion(s) passed")
    if FAILED:
        print(f"FAILED: {len(FAILED)}")
        for f in FAILED:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
