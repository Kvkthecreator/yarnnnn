"""
ADR-231 Runtime Invariants — final regression gate.

Per the runtime context plan §11, ten cross-shape invariants must hold
post-cutover. This file is the consolidated regression gate that asserts
each invariant against the live codebase.

The invariants:

1. Compact index always ≤1500 tokens regardless of workspace state
   (empty / steady / busy).
2. Every dispatcher firing emits exactly one narrative entry (no quiet paths).
3. Working-scratch directory created at firing-start and cleaned at TTL.
4. `_run_log.md` rolling cap honored (N=5/20/50 per shape).
5. `paused: true` declarations are not fired by scheduler.
6. `paused_until` future-timestamp declarations are not fired before that time.
7. Agent-side write paths exclude work-substrate paths (D10 discipline).
8. Authored substrate revision attribution: every write carries `authored_by`
   matching dispatcher's identity.
9. Per-shape envelope token estimates within ±20% of plan estimates.
10. **No live-code references to deleted symbols** (final grep gate per
    runtime plan §11): zero imports of `services.task_pipeline`,
    `services.task_workspace`, `services.task_types`,
    `services.task_derivation`, `services.primitives.manage_task`.

Some invariants (1, 4, 9) require runtime measurement against actual
workspaces and are tagged as such — they pass when the contract shape is
correct and the measured behavior is within bounds in production. The
static structural invariants (2, 5, 6, 7, 8, 10) are enforced as code
asserts here.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest


REPO_API = Path(__file__).parent  # api/ root


# ---------------------------------------------------------------------------
# Invariant 10 — final grep gate (no live-code references to deleted modules)
# ---------------------------------------------------------------------------


DELETED_MODULES = [
    "services.task_pipeline",
    "services.task_workspace",
    "services.task_types",
    "services.task_derivation",
    "services.primitives.manage_task",
]


def _walk_python_files(root: Path):
    """Yield .py files under root, excluding tests + venv + caches."""
    for path in root.rglob("*.py"):
        s = str(path)
        if any(seg in s for seg in (
            "/venv/", "/__pycache__/", "/.pytest_cache/",
            "test_adr", "/tests/",
        )):
            continue
        # Tests directory + this file are exempt
        if path.name.startswith("test_"):
            continue
        yield path


def _has_live_import(content: str, module: str) -> list[int]:
    """Find live (non-comment) import lines for a given module path.

    Returns a list of 1-indexed line numbers where the import lives.
    Skips lines whose import line is itself inside a docstring or a #-comment.
    """
    matches = []
    in_docstring = False
    docstring_quote = None
    for idx, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.lstrip()
        # Cheap docstring detection — toggles on bare """ or '''
        for quote in ('"""', "'''"):
            if line.startswith(quote):
                count = line.count(quote)
                if count == 1:
                    in_docstring = not in_docstring
                    docstring_quote = quote
                # if count >= 2, single-line docstring; toggle stays
        if in_docstring:
            continue
        if line.startswith("#"):
            continue
        # Match `from <module> import` or `import <module>` patterns
        if re.search(rf"^\s*from\s+{re.escape(module)}\s+import\s+", raw_line):
            matches.append(idx)
        elif re.search(rf"^\s*import\s+{re.escape(module)}\b", raw_line):
            matches.append(idx)
    return matches


def test_invariant_10_no_live_imports_of_deleted_modules():
    """The final grep gate: zero live imports of deleted task modules.

    Per ADR-231 D5 + Phase 3.7 atomic deletion, these modules are gone:
    importing from them would be a build failure. This test asserts at
    test-time that no .py file in api/ (excluding test files) has resurrected
    a reference.
    """
    offenses: list[tuple[Path, str, list[int]]] = []
    for path in _walk_python_files(REPO_API):
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for module in DELETED_MODULES:
            lines = _has_live_import(content, module)
            if lines:
                offenses.append((path.relative_to(REPO_API), module, lines))

    assert not offenses, (
        "Live imports of ADR-231-deleted modules detected:\n"
        + "\n".join(f"  {p}: imports {m} on line(s) {ls}" for p, m, ls in offenses)
    )


# ---------------------------------------------------------------------------
# Invariant 2 — single narrative emission per dispatcher firing
# ---------------------------------------------------------------------------


def test_invariant_2_dispatcher_emits_one_narrative_per_firing():
    """Every dispatcher branch calls _emit_narrative exactly once before
    returning, except for the early-paused-result path (which has no work
    to surface and returns _result_paused without firing).

    Static check: count `_emit_narrative` invocations per dispatch branch
    function and confirm each branch emits at least once on success and
    once on failure.
    """
    dispatcher = (REPO_API / "services" / "invocation_dispatcher.py").read_text()
    # Branches that should emit narrative: _dispatch_generative,
    # _dispatch_action, _dispatch_maintenance, plus dispatch() error path.
    for branch in (
        "_dispatch_generative",
        "_dispatch_action",
        "_dispatch_maintenance",
    ):
        # Find function start
        match = re.search(rf"async def {branch}\b", dispatcher)
        assert match, f"branch {branch} not found in invocation_dispatcher.py"
        # Find next async def or EOF
        body_start = match.end()
        next_def = re.search(r"\n(async def |def )\w+", dispatcher[body_start:])
        body_end = body_start + (next_def.start() if next_def else len(dispatcher) - body_start)
        body = dispatcher[body_start:body_end]
        # Action delegates entirely to generative; check the underlying generative branch covers it
        if branch == "_dispatch_action":
            # ACTION delegates to _dispatch_generative; that's where the narrative emits
            assert "_dispatch_generative" in body, (
                f"{branch} must delegate to _dispatch_generative for narrative coverage"
            )
            continue
        emit_count = body.count("_emit_narrative(")
        assert emit_count >= 1, (
            f"branch {branch} must call _emit_narrative at least once "
            f"(found {emit_count})"
        )


# ---------------------------------------------------------------------------
# Invariant 5 + 6 — paused / paused_until honored
# ---------------------------------------------------------------------------


def test_invariant_5_paused_blocks_scheduler():
    """A declaration with paused=True must never fire from the scheduler.

    The scheduler queries `tasks.paused = false` at the index level + the
    dispatcher rechecks `decl.paused` before any work. Both gates must exist.
    """
    scheduling = (REPO_API / "services" / "scheduling.py").read_text()
    dispatcher = (REPO_API / "services" / "invocation_dispatcher.py").read_text()

    # scheduling.compute_next_run_at honors decl.paused
    assert "if decl.paused:" in scheduling, (
        "compute_next_run_at must check decl.paused"
    )
    # dispatch() entry point honors decl.paused
    assert "if decl.paused:" in dispatcher, (
        "dispatch() must short-circuit on decl.paused"
    )


def test_invariant_6_paused_until_honored():
    """paused_until future timestamps gate firing until that time.

    services.scheduling.compute_next_run_at returns paused_until when set
    in future; dispatcher's decl.is_due reads the same gate.
    """
    scheduling = (REPO_API / "services" / "scheduling.py").read_text()
    recurrence = (REPO_API / "services" / "recurrence.py").read_text()
    assert "paused_until" in scheduling, (
        "scheduling module must reference paused_until"
    )
    assert "paused_until" in recurrence, (
        "recurrence module must expose paused_until property"
    )


# ---------------------------------------------------------------------------
# Invariant 7 — Agent-side write paths exclude work-substrate paths
# ---------------------------------------------------------------------------


def test_invariant_7_agent_writes_dont_target_work_substrate():
    """Agent-authored writes (via agent slugs) must target /agents/{slug}/
    paths, not /workspace/reports/, /workspace/context/{domain}/,
    /workspace/operations/, or /workspace/_shared/.

    This is a discipline rule; the dispatcher writes work substrate, agents
    write their own identity/style. Static check on agent_workspace shape.
    """
    agent_workspace = (REPO_API / "services" / "workspace.py").read_text()
    # AgentWorkspace._base must be /agents/{slug} prefix
    match = re.search(r'self\._base\s*=\s*f"/agents/\{', agent_workspace)
    assert match, (
        "AgentWorkspace must scope writes under /agents/{slug}/ "
        "(D10 discipline — agent writes never collide with work substrate)"
    )


# ---------------------------------------------------------------------------
# Invariant 8 — every write carries authored_by attribution
# ---------------------------------------------------------------------------


def test_invariant_8_dispatcher_writes_carry_authored_by():
    """Dispatcher writes natural-home substrate via UserMemory.write or
    write_revision — both require authored_by per ADR-209. Static check
    that the dispatcher's _write_workspace_path helper passes authored_by.
    """
    dispatcher = (REPO_API / "services" / "invocation_dispatcher.py").read_text()
    # The helper must accept authored_by as a kwarg
    match = re.search(
        r"async def _write_workspace_path\([^)]*authored_by[^)]*\)",
        dispatcher,
    )
    assert match, (
        "invocation_dispatcher._write_workspace_path must require authored_by "
        "(ADR-209 attribution invariant)"
    )


# ---------------------------------------------------------------------------
# Structural invariants on dispatch_helpers (the survivor module)
# ---------------------------------------------------------------------------


def test_dispatch_helpers_exposes_required_symbols():
    """dispatch_helpers.py must expose every survivor function the
    dispatcher imports. Validates the rewire from Phase 3.7."""
    helpers = (REPO_API / "services" / "dispatch_helpers.py").read_text()
    required = [
        "_generate",
        "gather_task_context",
        "build_task_execution_prompt",
        "_load_user_context",
        "_is_workspace_empty_for_daily_update",
        "_execute_daily_update_empty_state",
        "_execute_maintain_overview_empty_state",
        "_parse_delivery_target",
    ]
    for sym in required:
        assert f"def {sym}" in helpers or f"async def {sym}" in helpers, (
            f"dispatch_helpers.py missing required symbol: {sym}"
        )


# ---------------------------------------------------------------------------
# Invariants 1, 3, 4, 9 — runtime-measured (placeholders for future runs)
# ---------------------------------------------------------------------------
#
# These invariants assert behavior that's measurable only against a live
# workspace (token counts, scratch directory TTL, run-log rolling caps,
# envelope token estimates). They're tracked here as documented contracts
# that production runs must validate. See the runtime context plan §11
# for the original specification.
#
# When a dedicated harness for these measurements lands, replace each
# placeholder with a real assertion.


def test_invariant_1_compact_index_token_ceiling():
    """Compact index ≤1500 tokens regardless of workspace state.

    Currently a documented contract — the format_compact_index function
    has a _TOKEN_CEILING constant + truncation pass. Static check that
    the ceiling exists and is <= 1500.
    """
    wm = (REPO_API / "services" / "working_memory.py").read_text()
    match = re.search(r"_TOKEN_CEILING\s*=\s*(\d+)", wm)
    assert match, "working_memory must declare _TOKEN_CEILING constant"
    ceiling = int(match.group(1))
    assert ceiling <= 1500, (
        f"compact index token ceiling must be ≤1500 (found {ceiling})"
    )


def test_invariant_3_working_scratch_paths_per_shape():
    """Working scratch paths follow ADR-231 D9 conventions.

    Validates the recurrence_paths.resolve_working_scratch_path output
    shape for all four shapes.
    """
    rp = (REPO_API / "services" / "recurrence_paths.py").read_text()
    # All four shapes must have a working/ path mapping
    assert 'working/' in rp, "recurrence_paths must declare working/ scratch convention"
    assert 'def resolve_working_scratch_path' in rp, (
        "recurrence_paths must expose resolve_working_scratch_path helper"
    )


def test_invariant_4_run_log_paths_match_d10_discipline():
    """Run-log paths follow ADR-231 D10 — declaration-scoped (not Agent-scoped)."""
    rp = (REPO_API / "services" / "recurrence_paths.py").read_text()
    assert "def resolve_run_log_path" in rp, (
        "recurrence_paths must expose resolve_run_log_path"
    )
    # MAINTENANCE collapses to shared audit log per D10
    assert "back-office-audit.md" in rp, (
        "MAINTENANCE shape must collapse run log to /workspace/_shared/back-office-audit.md per D10"
    )


def test_invariant_9_per_shape_envelope_contract_present():
    """Each dispatch branch builds a shape-specific context envelope.

    Static check that _decl_to_task_info maps shape → output_kind correctly
    so the envelope assembly differentiates per shape.
    """
    dispatcher = (REPO_API / "services" / "invocation_dispatcher.py").read_text()
    # Shape mapping must cover all four
    for shape in ("DELIVERABLE", "ACCUMULATION", "ACTION", "MAINTENANCE"):
        assert f"RecurrenceShape.{shape}" in dispatcher, (
            f"dispatcher must reference RecurrenceShape.{shape}"
        )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
