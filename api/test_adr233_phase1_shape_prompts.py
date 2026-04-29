"""
Validation Suite — ADR-233 Phase 1 (Shape-aware headless prompt profiles)

Tests (12 assertions):
  Resolver / module structure (4):
   1. PROFILE_KEYS contains all 5 expected profile keys
   2. build_prompt("headless/deliverable") returns a string containing DELIVERABLE_POSTURE lead
   3. build_prompt("headless/accumulation") returns a string containing ACCUMULATION_POSTURE lead
   4. build_prompt("headless/action") returns a string containing ACTION_POSTURE lead
   5. build_prompt("chat/workspace", with_tools=True) returns a list of content blocks (regression guard)
   6. build_prompt("chat/entity", with_tools=True) returns a list of content blocks (regression guard)
   7. build_prompt("unknown/profile") raises ValueError

  Cache layout (3):
   8. Headless static block contains posture FIRST, then HEADLESS_BASE_BLOCK
   9. Cached system block in build_task_execution_prompt is the posture+base text
  10. Posture appears in the cached block (cache_control=ephemeral) and not in the dynamic block

  Singular-implementation discipline (3):
  11. build_task_execution_prompt no longer accepts `task_mode` parameter
  12. dispatch_helpers contains zero references to `task_mode == "goal"` (deleted branch)
  13. Live api/ code (excluding ADRs, CHANGELOG, broken legacy tests) has zero `yarnnn_prompts` imports

Strategy: pure-Python static + behavioral checks. No DB.

Usage:
    cd api && python test_adr233_phase1_shape_prompts.py
"""

from __future__ import annotations

import inspect
import logging
import re
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REPO_API = Path(__file__).parent
RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


# ---------------------------------------------------------------------------
# Resolver / module structure
# ---------------------------------------------------------------------------


def test_profile_keys_registry():
    from agents.prompts import PROFILE_KEYS
    expected = {
        "chat/workspace",
        "chat/entity",
        "headless/deliverable",
        "headless/accumulation",
        "headless/action",
    }
    actual = set(PROFILE_KEYS)
    record(
        "test_profile_keys_registry",
        actual == expected,
        f"expected={sorted(expected)} got={sorted(actual)}",
    )


def test_headless_deliverable_posture():
    from agents.prompts import build_prompt
    text = build_prompt("headless/deliverable")
    ok = isinstance(text, str) and "recurring deliverable" in text.lower() and "DELIVERABLE invocation" in text
    record("test_headless_deliverable_posture", ok, f"len={len(text) if isinstance(text, str) else 'n/a'}")


def test_headless_accumulation_posture():
    from agents.prompts import build_prompt
    text = build_prompt("headless/accumulation")
    ok = (
        isinstance(text, str)
        and "ACCUMULATION invocation" in text
        and "additive" in text.lower()
    )
    record("test_headless_accumulation_posture", ok, f"len={len(text) if isinstance(text, str) else 'n/a'}")


def test_headless_action_posture():
    from agents.prompts import build_prompt
    text = build_prompt("headless/action")
    ok = (
        isinstance(text, str)
        and "ACTION invocation" in text
        and "Reviewer" in text
    )
    record("test_headless_action_posture", ok, f"len={len(text) if isinstance(text, str) else 'n/a'}")


def test_chat_workspace_returns_blocks():
    from agents.prompts import build_prompt
    blocks = build_prompt("chat/workspace", with_tools=True)
    ok = isinstance(blocks, list) and len(blocks) >= 1 and "text" in blocks[0]
    record("test_chat_workspace_returns_blocks", ok, f"type={type(blocks).__name__} count={len(blocks) if isinstance(blocks, list) else 'n/a'}")


def test_chat_entity_returns_blocks():
    from agents.prompts import build_prompt
    blocks = build_prompt("chat/entity", with_tools=True)
    ok = isinstance(blocks, list) and len(blocks) >= 1 and "text" in blocks[0]
    record("test_chat_entity_returns_blocks", ok, f"type={type(blocks).__name__} count={len(blocks) if isinstance(blocks, list) else 'n/a'}")


def test_unknown_profile_raises():
    from agents.prompts import build_prompt
    try:
        build_prompt("unknown/profile")
        record("test_unknown_profile_raises", False, "expected ValueError, got success")
    except ValueError as e:
        record("test_unknown_profile_raises", True, f"raised ValueError: {str(e)[:60]}")
    except Exception as e:
        record("test_unknown_profile_raises", False, f"raised {type(e).__name__} not ValueError")


# ---------------------------------------------------------------------------
# Cache layout
# ---------------------------------------------------------------------------


def test_headless_block_posture_before_base():
    from agents.prompts import build_prompt, HEADLESS_BASE_BLOCK
    text = build_prompt("headless/deliverable")
    posture_idx = text.find("DELIVERABLE invocation")
    base_idx = text.find(HEADLESS_BASE_BLOCK[:80])  # match start of base block
    ok = posture_idx >= 0 and base_idx >= 0 and posture_idx < base_idx
    record(
        "test_headless_block_posture_before_base",
        ok,
        f"posture_idx={posture_idx} base_idx={base_idx}",
    )


def test_build_task_execution_prompt_cache_split():
    from services.dispatch_helpers import build_task_execution_prompt
    task_info = {"title": "T", "objective": {"deliverable": "x"}, "success_criteria": []}
    agent = {"role": "writer"}
    sb, _ = build_task_execution_prompt(
        task_info=task_info,
        agent=agent,
        agent_instructions="Be concise.",
        context="(no context)",
        shape="DELIVERABLE",
    )
    ok_count = isinstance(sb, list) and len(sb) >= 1
    cached = sb[0] if ok_count else {}
    has_cache = bool(cached.get("cache_control", {}).get("type") == "ephemeral")
    cached_text = cached.get("text", "")
    has_posture = "DELIVERABLE invocation" in cached_text
    has_base = "Workspace Conventions" in cached_text
    ok = ok_count and has_cache and has_posture and has_base
    record(
        "test_build_task_execution_prompt_cache_split",
        ok,
        f"blocks={len(sb) if isinstance(sb, list) else 'n/a'} cache={has_cache} posture={has_posture} base={has_base}",
    )


def test_posture_in_cached_block_not_dynamic():
    from services.dispatch_helpers import build_task_execution_prompt
    task_info = {"title": "T", "objective": {}, "success_criteria": []}
    agent = {"role": "writer"}
    sb, _ = build_task_execution_prompt(
        task_info=task_info,
        agent=agent,
        agent_instructions="X",
        context="(none)",
        shape="ACCUMULATION",
        deliverable_spec="# Deliverable Specification\nTest spec.",
    )
    cached = sb[0]["text"] if sb and "cache_control" in sb[0] else ""
    dynamic = sb[1]["text"] if len(sb) > 1 and "cache_control" not in sb[1] else ""
    posture_in_cached = "ACCUMULATION invocation" in cached
    posture_in_dynamic = "ACCUMULATION invocation" in dynamic
    ok = posture_in_cached and not posture_in_dynamic
    record(
        "test_posture_in_cached_block_not_dynamic",
        ok,
        f"in_cached={posture_in_cached} in_dynamic={posture_in_dynamic}",
    )


# ---------------------------------------------------------------------------
# Singular-implementation discipline
# ---------------------------------------------------------------------------


def test_build_task_execution_prompt_no_task_mode_param():
    from services.dispatch_helpers import build_task_execution_prompt
    sig = inspect.signature(build_task_execution_prompt)
    params = list(sig.parameters.keys())
    ok = "task_mode" not in params and "shape" in params
    record(
        "test_build_task_execution_prompt_no_task_mode_param",
        ok,
        f"task_mode in params={('task_mode' in params)} shape in params={('shape' in params)}",
    )


def test_no_goal_mode_branch_in_dispatch_helpers():
    src = (REPO_API / "services" / "dispatch_helpers.py").read_text()
    # The deleted branch was: `if task_mode == "goal" and prior_output:`
    bad = re.search(r"task_mode\s*==\s*[\"']goal[\"']", src)
    ok = bad is None
    record(
        "test_no_goal_mode_branch_in_dispatch_helpers",
        ok,
        f"match={'present' if bad else 'absent'}",
    )


def test_no_yarnnn_prompts_in_live_code():
    """Grep gate: live api/ code must not import or reference yarnnn_prompts.

    Excluded paths (allowed historical references):
      - api/prompts/CHANGELOG.md (historical entries preserved verbatim)
      - api/test_structural_overhaul.py, api/test_recent_commits.py,
        api/test_adr143_methodology_feedback.py — broken legacy tests with
        imports from services.task_pipeline (deleted by ADR-231) and from
        yarnnn_prompts.tools (deleted by ADR-231 Phase 3.7). Already-dead
        code; documenting cleanup deferred.
      - Comment lines that mention 'yarnnn_prompts' as a directory rename
        reference (ADR-189 / ADR-233 narrative).
    """
    proc = subprocess.run(
        ["grep", "-rn", "yarnnn_prompts", str(REPO_API)],
        capture_output=True, text=True,
    )
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    # Filter exclusions
    def excluded(line: str) -> bool:
        if "/prompts/CHANGELOG.md:" in line:
            return True
        if "/test_structural_overhaul.py:" in line:
            return True
        if "/test_recent_commits.py:" in line:
            return True
        if "/test_adr143" in line:
            return True
        # The gate's own file references the banned string in its docstring
        # + exclusion logic + assertion message — self-reference is fine.
        if "/test_adr233_phase1_shape_prompts.py:" in line:
            return True
        # Build / cache artifacts that might capture the banned string from
        # test names or stale serialized state. Not live source code.
        if "/.pytest_cache/" in line:
            return True
        if "/__pycache__/" in line:
            return True
        if line.endswith(".pyc"):
            return True
        # ADR-189 + ADR-233 doc-narrative mentions in module docstrings
        if "ADR-189" in line or "ADR-233" in line:
            return True
        # Reference to the rename in a comment
        if "formerly yarnnn_prompts" in line:
            return True
        return False

    live_hits = [ln for ln in lines if not excluded(ln)]
    ok = len(live_hits) == 0
    detail = f"live hits: {len(live_hits)}"
    if live_hits:
        detail += f" — first: {live_hits[0][:120]}"
    record("test_no_yarnnn_prompts_in_live_code", ok, detail)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main():
    tests = [
        test_profile_keys_registry,
        test_headless_deliverable_posture,
        test_headless_accumulation_posture,
        test_headless_action_posture,
        test_chat_workspace_returns_blocks,
        test_chat_entity_returns_blocks,
        test_unknown_profile_raises,
        test_headless_block_posture_before_base,
        test_build_task_execution_prompt_cache_split,
        test_posture_in_cached_block_not_dynamic,
        test_build_task_execution_prompt_no_task_mode_param,
        test_no_goal_mode_branch_in_dispatch_helpers,
        test_no_yarnnn_prompts_in_live_code,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            record(t.__name__, False, f"EXCEPTION: {type(e).__name__}: {e}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    logger.info("")
    logger.info(f"━━ ADR-233 Phase 1 gate: {passed}/{total} passed ━━")
    if passed < total:
        for name, ok, detail in RESULTS:
            if not ok:
                logger.error(f"FAIL {name}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
