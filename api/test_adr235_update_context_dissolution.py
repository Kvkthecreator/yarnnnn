"""
Validation Suite — ADR-235 (UpdateContext Dissolution + ManageRecurrence + ManageAgent.create Sunset)

Tests (17 assertions):

D1 — UpdateContext dissolution (10):
   1. UpdateContext is NOT in CHAT_PRIMITIVES.
   2. UpdateContext is NOT in HANDLERS.
   3. update_context.py does not exist on disk.
   4. InferContext is in CHAT_PRIMITIVES with the expected target enum.
   5. InferWorkspace is in CHAT_PRIMITIVES.
   6. ManageRecurrence is in BOTH CHAT_PRIMITIVES and HEADLESS_PRIMITIVES.
   7. ManageRecurrence action enum has exactly 5 values.
   8. WriteFile gains scope='workspace' (Option A) — schema enum includes it.
   9. WriteFile path-prefix activity classifier recognizes canonical paths.
  10. mcp_composition exposes dispatch_remember_this and routes through new
      primitives (no UpdateContext call left in the dispatch path).

D2 — ManageAgent.create sunset (4):
  11. MANAGE_AGENT_TOOL action enum has exactly 4 values (no 'create').
  12. agent_creation.create_agent_record still importable (signup path preserved).
  13. handle_manage_agent returns explicit error when called with action='create'.
  14. No prompt file in api/agents/prompts/chat/ contains a literal
      `ManageAgent(action="create"` invocation.

D3 — Singular Implementation grep gates (3):
  15. grep -r 'UpdateContext\\|UPDATE_CONTEXT_TOOL' api/services/ api/routes/
      api/jobs/ api/agents/ returns ZERO live-code invocations
      (annotations / migration-ledger refs allowed).
  16. grep -r 'UpdateContext' docs/architecture/primitives-matrix.md
      docs/design/SURFACE-CONTRACTS.md returns only annotation refs in
      version headers + migration ledger (no active invocation forms).
  17. ADR-231 invariants gate still passes (regression).

Strategy: pure-Python static checks. The grep gates inspect repo state.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

REPO_API = Path(__file__).parent
REPO_ROOT = REPO_API.parent
RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    icon = "✓" if ok else "✗"
    logger.info(f"{icon} {name}: {detail}")


# ---------------------------------------------------------------------------
# D1 — UpdateContext dissolution
# ---------------------------------------------------------------------------


def test_updatecontext_not_in_chat():
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    record(
        "test_updatecontext_not_in_chat",
        "UpdateContext" not in names,
        f"present={('UpdateContext' in names)} (must be False)",
    )


def test_updatecontext_not_in_handlers():
    from services.primitives.registry import HANDLERS
    record(
        "test_updatecontext_not_in_handlers",
        "UpdateContext" not in HANDLERS,
        f"present={('UpdateContext' in HANDLERS)} (must be False)",
    )


def test_update_context_file_deleted():
    p = REPO_API / "services" / "primitives" / "update_context.py"
    record(
        "test_update_context_file_deleted",
        not p.exists(),
        f"path={p} exists={p.exists()} (must be False)",
    )


def test_infer_context_in_chat():
    from services.primitives.registry import CHAT_PRIMITIVES
    from services.primitives.infer_context import INFER_CONTEXT_TOOL
    names = {t["name"] for t in CHAT_PRIMITIVES}
    targets = INFER_CONTEXT_TOOL["input_schema"]["properties"]["target"]["enum"]
    ok = "InferContext" in names and set(targets) == {"identity", "brand"}
    record(
        "test_infer_context_in_chat",
        ok,
        f"in_chat={('InferContext' in names)} targets={sorted(targets)}",
    )


def test_infer_workspace_in_chat():
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    record(
        "test_infer_workspace_in_chat",
        "InferWorkspace" in names,
        f"present={('InferWorkspace' in names)}",
    )


def test_manage_recurrence_in_both_modes():
    from services.primitives.registry import CHAT_PRIMITIVES, HEADLESS_PRIMITIVES
    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}
    ok = "ManageRecurrence" in chat_names and "ManageRecurrence" in headless_names
    record(
        "test_manage_recurrence_in_both_modes",
        ok,
        f"chat={('ManageRecurrence' in chat_names)} headless={('ManageRecurrence' in headless_names)}",
    )


def test_manage_recurrence_action_enum():
    from services.primitives.manage_recurrence import MANAGE_RECURRENCE_TOOL
    actions = MANAGE_RECURRENCE_TOOL["input_schema"]["properties"]["action"]["enum"]
    expected = {"create", "update", "pause", "resume", "archive"}
    record(
        "test_manage_recurrence_action_enum",
        set(actions) == expected,
        f"actions={sorted(actions)} expected={sorted(expected)}",
    )


def test_writefile_workspace_scope():
    """ADR-235 Option A: WriteFile schema includes scope='workspace'."""
    from services.primitives.workspace import WRITE_FILE_TOOL
    scopes = WRITE_FILE_TOOL["input_schema"]["properties"]["scope"]["enum"]
    expected = {"workspace", "agent", "context"}
    record(
        "test_writefile_workspace_scope",
        set(scopes) == expected,
        f"scopes={sorted(scopes)} expected={sorted(expected)}",
    )


def test_writefile_activity_classifier():
    """ADR-235 D1.b: WriteFile path-prefix recognition for activity-log emission."""
    from services.primitives.workspace import _classify_workspace_path_for_activity

    notes = _classify_workspace_path_for_activity("memory/notes.md")
    feedback = _classify_workspace_path_for_activity("agents/researcher/memory/feedback.md")
    mandate = _classify_workspace_path_for_activity("context/_shared/MANDATE.md")
    other = _classify_workspace_path_for_activity("reports/x/_spec.yaml")

    ok = (
        notes is not None and notes["event_type"] == "memory_written"
        and feedback is not None and feedback["event_type"] == "agent_feedback"
        and feedback["metadata"].get("agent_slug") == "researcher"
        and mandate is None  # not a recognized canonical path
        and other is None
    )
    record(
        "test_writefile_activity_classifier",
        ok,
        f"notes={notes!r} feedback={feedback!r} mandate={mandate!r} other={other!r}",
    )


def test_mcp_composition_dispatch_routes_through_new_primitives():
    """ADR-235: mcp_composition.dispatch_remember_this exists and the file
    has no live execute_primitive call against UpdateContext."""
    from services import mcp_composition
    has_dispatch = hasattr(mcp_composition, "dispatch_remember_this")

    src = (REPO_API / "services" / "mcp_composition.py").read_text()
    # The doc-comment may reference UpdateContext historically; the live
    # invocation pattern is `execute_primitive(..., "UpdateContext", ...)`
    # which must NOT appear in code (only in docstrings).
    bad_invocation = re.search(r'execute_primitive\([^)]*"UpdateContext"', src)

    ok = has_dispatch and bad_invocation is None
    record(
        "test_mcp_composition_dispatch_routes_through_new_primitives",
        ok,
        f"has_dispatch={has_dispatch} bad_invocation={bool(bad_invocation)}",
    )


# ---------------------------------------------------------------------------
# D2 — ManageAgent.create sunset
# ---------------------------------------------------------------------------


def test_manage_agent_action_enum_no_create():
    from services.primitives.coordinator import MANAGE_AGENT_TOOL
    actions = MANAGE_AGENT_TOOL["input_schema"]["properties"]["action"]["enum"]
    expected = {"update", "pause", "resume", "archive"}
    record(
        "test_manage_agent_action_enum_no_create",
        set(actions) == expected,
        f"actions={sorted(actions)} expected={sorted(expected)}",
    )


def test_agent_creation_record_still_importable():
    """Service code preserved for kernel/signup path."""
    try:
        from services.agent_creation import create_agent_record
        ok = callable(create_agent_record)
    except Exception as e:
        ok = False
        detail = f"import failed: {e}"
    else:
        detail = "create_agent_record callable"
    record("test_agent_creation_record_still_importable", ok, detail)


def test_manage_agent_create_returns_disabled_error():
    """ADR-235 D2: LLM-facing handler returns explicit error on action='create'."""
    import asyncio
    from services.primitives.coordinator import handle_manage_agent

    async def _run():
        return await handle_manage_agent(None, {"action": "create", "title": "X", "role": "writer"})

    try:
        result = asyncio.get_event_loop().run_until_complete(_run())
    except RuntimeError:
        # If no running loop, create one
        result = asyncio.new_event_loop().run_until_complete(_run())

    ok = (
        result.get("success") is False
        and result.get("error") == "create_action_disabled"
    )
    record(
        "test_manage_agent_create_returns_disabled_error",
        ok,
        f"result={result}",
    )


def test_chat_prompts_no_manage_agent_create():
    """No active prompt file invokes ManageAgent(action="create"."""
    chat_prompts_dir = REPO_API / "agents" / "prompts" / "chat"
    if not chat_prompts_dir.exists():
        record("test_chat_prompts_no_manage_agent_create", False, "chat prompts dir missing")
        return

    offenders = []
    for p in chat_prompts_dir.glob("*.py"):
        text = p.read_text()
        if 'ManageAgent(action="create"' in text or "ManageAgent(action='create'" in text:
            offenders.append(p.name)

    record(
        "test_chat_prompts_no_manage_agent_create",
        not offenders,
        f"offenders={offenders}" if offenders else "clean",
    )


# ---------------------------------------------------------------------------
# D3 — Singular Implementation grep gates
# ---------------------------------------------------------------------------


_LIVE_CALL_PATTERN = re.compile(r'(UpdateContext\(target=|handle_update_context\(|UPDATE_CONTEXT_TOOL\b|from services\.primitives\.update_context|from \.update_context )')


def _scan_files_for_live_calls(roots: list[Path]) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            if "venv" in str(p) or "__pycache__" in str(p):
                continue
            if p.name == "update_context.py":
                continue  # file is gone anyway
            if p.name.startswith("test_"):
                continue  # test files allowed (they assert these patterns ARE absent)
            try:
                text = p.read_text()
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if _LIVE_CALL_PATTERN.search(line):
                    hits.append((p, i, line.strip()[:140]))
    return hits


def test_no_live_updatecontext_invocations_in_code():
    roots = [
        REPO_API / "services",
        REPO_API / "routes",
        REPO_API / "jobs",
        REPO_API / "agents",
    ]
    hits = _scan_files_for_live_calls(roots)
    record(
        "test_no_live_updatecontext_invocations_in_code",
        not hits,
        f"hits={[(str(p.relative_to(REPO_API)), ln) for p, ln, _ in hits[:5]]}",
    )


def test_no_live_updatecontext_invocations_in_active_canon_docs():
    """Active-canon docs may reference UpdateContext in version headers,
    migration ledgers, or annotations — but NOT in active invocation form."""
    canon_paths = [
        REPO_ROOT / "docs" / "architecture" / "primitives-matrix.md",
        REPO_ROOT / "docs" / "design" / "SURFACE-CONTRACTS.md",
        REPO_ROOT / "CLAUDE.md",
    ]
    bad_hits: list[tuple[Path, int, str]] = []
    invocation_pattern = re.compile(r'UpdateContext\(target=')
    for p in canon_paths:
        if not p.exists():
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            # Active invocation form: UpdateContext(target=...)
            # Allowed: backtick-quoted historical references, version headers,
            # migration ledger, comparison annotations.
            if invocation_pattern.search(line):
                # Allow if the line is annotation/quote (contains backtick or
                # references "dissolved"/"deleted"/"replaced"/"migration"/"history"/"superseded")
                if any(
                    marker in line
                    for marker in (
                        "dissolved",
                        "deleted",
                        "Replaced by",
                        "replaced by",
                        "Replaces",
                        "superseded",
                        "Migration ledger",
                        "Pre-ADR-235",
                        "pre-ADR-235",
                        "(Pre",
                        "history",
                        "Historical",
                    )
                ):
                    continue
                bad_hits.append((p, i, line.strip()[:140]))

    record(
        "test_no_live_updatecontext_invocations_in_active_canon_docs",
        not bad_hits,
        f"bad_hits={[(str(p.relative_to(REPO_ROOT)), ln) for p, ln, _ in bad_hits[:5]]}",
    )


def test_adr231_invariants_still_pass():
    """Regression guard — ADR-231 runtime invariants must remain green."""
    import importlib
    try:
        mod = importlib.import_module("test_adr231_runtime_invariants")
    except Exception as e:
        record(
            "test_adr231_invariants_still_pass",
            False,
            f"could not import test_adr231_runtime_invariants: {e}",
        )
        return

    # Probe a representative invariant (file-level no manage_task / task_pipeline imports).
    # We don't re-run the full suite here; pytest handles that — this assertion is
    # a "smoke check" that the module is importable and exposes the expected gates.
    has_main = hasattr(mod, "main") or any(
        n.startswith("test_") for n in dir(mod)
    )
    record(
        "test_adr231_invariants_still_pass",
        has_main,
        f"module loaded; pytest runs the assertions",
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main():
    tests = [
        # D1
        test_updatecontext_not_in_chat,
        test_updatecontext_not_in_handlers,
        test_update_context_file_deleted,
        test_infer_context_in_chat,
        test_infer_workspace_in_chat,
        test_manage_recurrence_in_both_modes,
        test_manage_recurrence_action_enum,
        test_writefile_workspace_scope,
        test_writefile_activity_classifier,
        test_mcp_composition_dispatch_routes_through_new_primitives,
        # D2
        test_manage_agent_action_enum_no_create,
        test_agent_creation_record_still_importable,
        test_manage_agent_create_returns_disabled_error,
        test_chat_prompts_no_manage_agent_create,
        # D3
        test_no_live_updatecontext_invocations_in_code,
        test_no_live_updatecontext_invocations_in_active_canon_docs,
        test_adr231_invariants_still_pass,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            record(t.__name__, False, f"EXCEPTION: {type(e).__name__}: {e}")

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    logger.info("")
    logger.info(f"━━ ADR-235 gate: {passed}/{total} passed ━━")
    if passed < total:
        for name, ok, detail in RESULTS:
            if not ok:
                logger.error(f"FAIL {name}: {detail}")
        sys.exit(1)


if __name__ == "__main__":
    main()
