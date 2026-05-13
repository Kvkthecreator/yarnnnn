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


def test_dispatch_specialist_schema_accepts_required_capabilities():
    from services.primitives.dispatch_specialist import DISPATCH_SPECIALIST_TOOL
    schema = DISPATCH_SPECIALIST_TOOL["input_schema"]
    properties = schema["properties"]
    assert_true(
        "required_capabilities" in properties,
        "DispatchSpecialist input_schema has required_capabilities property",
    )
    rc_prop = properties["required_capabilities"]
    assert_eq(rc_prop.get("type"), "array", "required_capabilities is array type")
    assert_eq(
        rc_prop.get("items", {}).get("type"),
        "string",
        "required_capabilities items are strings",
    )
    assert_true(
        "required_capabilities" not in schema.get("required", []),
        "required_capabilities is optional in schema",
    )


def test_dispatcher_threads_capabilities_into_context():
    dispatcher_src = (_REPO_ROOT / "services" / "invocation_dispatcher.py").read_text()
    assert_true(
        "recurrence_required_capabilities" in dispatcher_src,
        "dispatcher source threads recurrence_required_capabilities",
    )
    assert_true(
        "list(recurrence.required_capabilities)" in dispatcher_src,
        "dispatcher reads from recurrence.required_capabilities",
    )


def test_reviewer_reads_capabilities_from_context():
    reviewer_src = (_REPO_ROOT / "agents" / "reviewer_agent.py").read_text()
    assert_true(
        "recurrence_required_capabilities" in reviewer_src,
        "reviewer reads recurrence_required_capabilities from context",
    )
    assert_true(
        "Required capabilities for dispatched specialists" in reviewer_src,
        "reviewer surfaces capabilities section in system context",
    )


def test_handle_dispatch_specialist_passes_capabilities():
    ds_src = (_REPO_ROOT / "services" / "primitives" / "dispatch_specialist.py").read_text()
    assert_true(
        "task_required_capabilities=task_required_capabilities" in ds_src,
        "handle passes task_required_capabilities kwarg to get_headless_tools_for_agent",
    )
    assert_true(
        'input.get("required_capabilities")' in ds_src,
        "handle reads required_capabilities from tool input",
    )
    # iter-5 surfacing: AGENT_TEMPLATES import was a holdover; should be ALL_ROLES.
    assert_true(
        "from services.orchestration import ALL_ROLES" in ds_src,
        "dispatch_specialist imports ALL_ROLES (not deleted AGENT_TEMPLATES)",
    )
    assert_true(
        "AGENT_TEMPLATES" not in ds_src or "AGENT_TEMPLATES + AGENT_TYPES aliases were deleted" in ds_src,
        "no live AGENT_TEMPLATES reference in dispatch_specialist (comment OK)",
    )


def test_alpha_trader_bundle_declares_capabilities():
    bundle_path = (
        _REPO_ROOT.parent / "docs" / "programs" / "alpha-trader"
        / "reference-workspace" / "_recurrences.yaml"
    )
    content = bundle_path.read_text()
    parsed = parse_recurrences_yaml(content)
    by_slug = {r.slug: r for r in parsed}

    expected = {
        "track-universe": {"read_trading"},
        "signal-evaluation": {"read_trading"},
        "track-regime": {"read_trading"},
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

    housekeeping_slugs = [
        "narrative-digest", "morning-reflection", "morning-calibration",
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

    mirror_slugs = ["track-positions", "track-account", "track-orders"]
    for slug in mirror_slugs:
        rec = by_slug.get(slug)
        if rec is None:
            continue
        assert_eq(
            rec.required_capabilities, [],
            f"mechanical mirror {slug!r} has empty required_capabilities",
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
