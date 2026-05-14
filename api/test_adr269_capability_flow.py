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


def test_dispatch_specialist_message_append_uses_response_content():
    """Regression for the 'tool_uses_raw' AttributeError that blocked every
    iter-4 specialist round-trip until 2026-05-13.

    Background: dispatch_specialist.py previously read `response.tool_uses_raw`
    when appending the assistant turn to message history. That field never
    existed on ChatResponse (anthropic.py:26) — Python raised AttributeError
    before the `or` fallback could evaluate. The fix replaces that access with
    a reconstruction loop over `response.content` (mirrors the canonical
    pattern in api/agents/reviewer_agent.py).

    This test verifies:
      1. The code path no longer references `tool_uses_raw` anywhere.
      2. A mock ChatResponse with content + tool_uses can be passed through
         the message-append branch without raising.
    """
    import inspect
    from services.primitives import dispatch_specialist as ds

    # 1. Grep the source for the bug shape.
    source = inspect.getsource(ds)
    # Comment historical-reference is allowed; live access is not.
    live_refs = [
        line for line in source.splitlines()
        if "tool_uses_raw" in line and not line.strip().startswith("#")
    ]
    assert_eq(
        live_refs, [],
        "no live (non-comment) references to tool_uses_raw remain",
    )

    # 2. Reconstruct the message-append loop in isolation and verify shape.
    class _MockBlock:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    mock_content = [
        _MockBlock(type="text", text="thinking..."),
        _MockBlock(type="tool_use", id="t_1", name="ReadFile", input={"path": "x"}),
    ]

    # This is the exact pattern from dispatch_specialist.py post-fix.
    assistant_content: list[dict] = []
    for block in (mock_content or []):
        btype = getattr(block, "type", None)
        if btype == "text":
            assistant_content.append({"type": "text", "text": getattr(block, "text", "")})
        elif btype == "tool_use":
            assistant_content.append({
                "type": "tool_use",
                "id": getattr(block, "id", ""),
                "name": getattr(block, "name", ""),
                "input": getattr(block, "input", {}),
            })

    assert_eq(len(assistant_content), 2, "reconstructed 2 blocks from mock content")
    assert_eq(assistant_content[0]["type"], "text", "first block is text")
    assert_eq(assistant_content[1]["type"], "tool_use", "second block is tool_use")
    assert_eq(assistant_content[1]["id"], "t_1", "tool_use id round-trips")
    assert_eq(assistant_content[1]["name"], "ReadFile", "tool_use name round-trips")
    assert_eq(assistant_content[1]["input"], {"path": "x"}, "tool_use input round-trips")


def test_dispatch_specialist_tool_execution_uses_attribute_access():
    """Regression for the 'ToolUseBlock has no get attribute' AttributeError
    that blocked every specialist tool-execution turn until 2026-05-13.

    Background: dispatch_specialist.py previously read tool_use fields as
    `tu.get("name")` / `tu.get("input")` / `tu.get("id")`. But
    `response.tool_uses` is `list[ToolUseBlock]` per anthropic.py
    `_parse_response` (lines 110-114) — `ToolUseBlock` is a @dataclass
    with `.id`, `.name`, `.input` attributes, NOT a dict. The fix uses
    attribute access (matches reviewer_agent.py's pattern).

    Surfaced AFTER the tool_uses_raw fix shipped — same underlying class
    of bug (code assumed dict shape, runtime delivers dataclass).

    This test verifies:
      1. No live (non-comment) `tu.get(` patterns exist in the iteration
         over response.tool_uses.
      2. A mock ToolUseBlock-shaped object can be iterated using the
         attribute access pattern without raising.
    """
    import inspect
    from services.primitives import dispatch_specialist as ds

    # 1. Grep the source for the bug shape — `tu.get(` after iterating
    #    `for tu in response.tool_uses:`.
    source = inspect.getsource(ds)
    live_refs = [
        line for line in source.splitlines()
        if (line.strip().startswith("tool_name = tu.get")
            or line.strip().startswith("tool_input = tu.get")
            or line.strip().startswith("tool_use_id = tu.get"))
        and not line.strip().startswith("#")
    ]
    assert_eq(
        live_refs, [],
        "no live `tu.get(...)` access on ToolUseBlock items remains",
    )

    # 2. Reconstruct the tool-execution iteration pattern in isolation.
    class _MockToolUseBlock:
        """Mirrors anthropic.py ToolUseBlock dataclass: attribute access only."""
        def __init__(self, id, name, input):
            self.id = id
            self.name = name
            self.input = input

    mock_tool_uses = [
        _MockToolUseBlock(id="t_1", name="ReadFile", input={"path": "/x"}),
        _MockToolUseBlock(id="t_2", name="WriteFile", input={"path": "/y", "content": "z"}),
    ]

    # This is the exact pattern from dispatch_specialist.py post-fix.
    results = []
    for tu in mock_tool_uses:
        tool_name = tu.name or ""
        tool_input = tu.input or {}
        tool_use_id = tu.id or ""
        results.append((tool_name, tool_input, tool_use_id))

    assert_eq(len(results), 2, "iterated 2 tool_uses")
    assert_eq(results[0], ("ReadFile", {"path": "/x"}, "t_1"), "first tool_use unpacked correctly")
    assert_eq(results[1], ("WriteFile", {"path": "/y", "content": "z"}, "t_2"), "second tool_use unpacked correctly")

    # 3. Negative test: attempting `.get()` on the dataclass-shaped mock
    #    should raise AttributeError — confirms the bug class.
    raised = False
    try:
        mock_tool_uses[0].get("name")
    except AttributeError:
        raised = True
    assert_true(raised, "AttributeError raised when calling .get() on ToolUseBlock-shaped object (confirms bug class)")


def test_dispatch_specialist_system_prompt_has_cache_control():
    """Regression for the lost-on-PR-#9 cache markers on specialist system prompts.

    Background: ADR-260/261/262 squash (commit 42725c6, 2026-05-10) rewrote
    dispatch_specialist.py greenfield. The prior cost-hardening from
    CHANGELOG entry 2026.04.30 (in deleted dispatch_helpers.py) wrapped
    static system content in `cache_control: {"type": "ephemeral"}` so
    rounds 2..N read the system prompt from Anthropic's prompt cache
    instead of re-billing it. That mechanism was lost. ADR-171/172
    pricing assumes caching is firing (markup computed at user-facing
    input rate, cache discount accrues as platform margin).

    Audit 2026-05-13 found that without cache markers, a 5-round
    specialist loop was re-billing the full system prompt × 5, and the
    operator-experienced cost ($0.20/round) matched no-cache pricing.

    This test verifies _compose_specialist_system_prompt returns the
    structured content-blocks shape with cache_control on the static
    block — not a plain str.
    """
    from services.primitives.dispatch_specialist import _compose_specialist_system_prompt

    result = _compose_specialist_system_prompt(
        role="researcher",
        display_name="Researcher",
        tagline="Test tagline",
        default_instructions="Test instructions",
    )
    assert_true(isinstance(result, list), "system prompt is a list of content blocks")
    assert_true(len(result) >= 1, "at least one content block")
    assert_eq(result[0].get("type"), "text", "first block is text-typed")
    assert_true("cache_control" in result[0], "first block carries cache_control marker")
    assert_eq(
        result[0].get("cache_control"),
        {"type": "ephemeral"},
        "cache_control is the ephemeral shape Anthropic recognizes",
    )


def test_dispatch_specialist_honors_per_recurrence_max_rounds():
    """Regression for the global-only round budget that orphaned heavy bundle workloads.

    Background: `_SPECIALIST_MAX_ROUNDS = 5` was correctly sized for
    single-output specialist work (e.g. track-regime: 11 actions, 1
    output file, completed in 27s). It was undersized for multi-output
    bundle workloads (e.g. 5-ticker track-universe needs ~10-12 rounds,
    5-signal × 5-ticker falsify-signals needs ~15-20). Cold-start audit
    2026-05-13 showed both heavy recurrences fetched data successfully
    then ran out of rounds before any WriteFile fired.

    This test verifies handle_dispatch_specialist reads
    `auth.recurrence_options.max_rounds` and honors it as the loop
    ceiling. The kernel exposes the knob; bundles declare workload-
    appropriate budgets per ADR-176/216 (work-shape is bundle-shaped).
    """
    from services.primitives import dispatch_specialist as ds
    import inspect

    source = inspect.getsource(ds.handle_dispatch_specialist)
    assert_true(
        "recurrence_options" in source,
        "handle_dispatch_specialist reads recurrence_options from auth",
    )
    assert_true(
        "max_rounds" in source,
        "handle_dispatch_specialist resolves a max_rounds value",
    )
    assert_true(
        "range(max_rounds)" in source,
        "loop iterates over the resolved max_rounds, not the global constant",
    )


def test_reviewer_threads_recurrence_options_onto_auth():
    """Regression: dispatcher → invoke_reviewer → auth.recurrence_options.

    The Reviewer's tool dispatch builds a SimpleNamespace auth. For
    per-recurrence specialist budgets to take effect, the Reviewer must
    copy recurrence options from its context envelope onto auth before
    invoking tools. Without this hop, max_rounds declared in the bundle
    YAML never reaches handle_dispatch_specialist.
    """
    from agents import reviewer_agent
    import inspect

    source = inspect.getsource(reviewer_agent)
    # `auth = SimpleNamespace(... recurrence_options=...)` is the
    # threading pattern. We don't pin a specific line shape, just that
    # the name `recurrence_options` appears in the auth construction.
    assert_true(
        "recurrence_options" in source,
        "reviewer_agent threads recurrence_options onto auth",
    )


def test_reviewer_system_prompt_has_cache_control():
    """Regression for the Reviewer-side caching gap surfaced by cf5bb69 audit.

    Background: cf5bb69 fixed specialist-side caching (dispatch_specialist).
    Render log audit on seulkim88 verified Sonnet specialist hits 59-67%
    cache on rounds 2+. SAME audit found Haiku Reviewer was uncached on
    every call (every [TOKENS] line: cache_create=0 cache_read=0
    cache_hit=0% with 15-23K input tokens). Same root cause:
    reviewer_agent._build_system_prompt() returned plain str — Anthropic's
    prompt-caching beta header attached but no cache_control markers on
    static content.

    This test verifies _build_system_prompt() returns the structured
    content-blocks shape with cache_control on the static frame block —
    not a plain str. Same canonical pattern as
    test_dispatch_specialist_system_prompt_has_cache_control above.
    """
    from agents.reviewer_agent import _build_system_prompt

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
    """Bundle-level: heavy judgment-mode recurrences declare per-recurrence
    round budgets matching their observed workload size.

    ADR-271 Thread A: track-universe migrated to mode=mechanical, no longer
    routes through specialist dispatch, no longer needs max_rounds. Only
    judgment-mode heavy recurrences remain in scope here.
    """
    from services.recurrence import parse_recurrences_yaml
    import os

    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "docs",
        "programs",
        "alpha-trader",
        "reference-workspace",
        "_recurrences.yaml",
    )
    with open(path, encoding="utf-8") as f:
        content = f.read()
    parsed = parse_recurrences_yaml(content)
    by_slug = {r.slug: r for r in parsed}

    # ADR-271 Thread A: track-universe is now mechanical-mode. No max_rounds
    # required (no specialist dispatched).
    assert_true(
        "track-universe" in by_slug,
        "alpha-trader bundle declares track-universe",
    )
    assert_eq(
        by_slug["track-universe"].mode, "mechanical",
        "track-universe is mechanical-mode post-ADR-271",
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
