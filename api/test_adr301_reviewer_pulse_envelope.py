"""Regression gate for ADR-301 — Reviewer Pulse Envelope.

The Reviewer's wake envelope must include two new kernel-universal entries
(`_schedule_index.md` + `_recent_execution.md`) that mechanically mirror
the workspace's scheduling index + recent execution_events. The persona
frame must instruct the Reviewer how to use them ("Pulse Discipline"
section). The scheduler tick must invoke the kernel mirrors per-tick.

Closes the schedule-hallucination class documented in
docs/evaluations/2026-05-24-045348-reviewer-schedule-self-misdiagnosis/.

Run:
    python -m api.test_adr301_reviewer_pulse_envelope
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


_PASS: list[str] = []
_FAIL: list[tuple[str, str]] = []


def _ok(name: str) -> None:
    _PASS.append(name)
    print(f"  ✓ {name}")


def _bad(name: str, reason: str) -> None:
    _FAIL.append((name, reason))
    print(f"  ✗ {name}\n      {reason}")


# ---------------------------------------------------------------------------
# 1. Path constants exist
# ---------------------------------------------------------------------------

def test_path_constants() -> None:
    print("\n[1] Path constants — workspace_paths.py")
    try:
        from services.workspace_paths import (
            SYSTEM_SCHEDULE_INDEX_PATH,
            SYSTEM_RECENT_EXECUTION_PATH,
        )
    except ImportError as e:
        _bad("workspace_paths imports", str(e))
        return
    if SYSTEM_SCHEDULE_INDEX_PATH == "system/_schedule_index.md":
        _ok("SYSTEM_SCHEDULE_INDEX_PATH = system/_schedule_index.md")
    else:
        _bad(
            "SYSTEM_SCHEDULE_INDEX_PATH value",
            f"got {SYSTEM_SCHEDULE_INDEX_PATH!r}",
        )
    if SYSTEM_RECENT_EXECUTION_PATH == "system/_recent_execution.md":
        _ok("SYSTEM_RECENT_EXECUTION_PATH = system/_recent_execution.md")
    else:
        _bad(
            "SYSTEM_RECENT_EXECUTION_PATH value",
            f"got {SYSTEM_RECENT_EXECUTION_PATH!r}",
        )


# ---------------------------------------------------------------------------
# 2. Primitives exist and are registered
# ---------------------------------------------------------------------------

def test_primitives_exist() -> None:
    print("\n[2] Primitives — MirrorScheduleIndex + MirrorRecentExecution")
    try:
        from services.primitives.mirror_schedule_index import (
            handle_mirror_schedule_index,
        )
        from services.primitives.mirror_recent_execution import (
            handle_mirror_recent_execution,
        )
    except ImportError as e:
        _bad("primitive module imports", str(e))
        return
    if inspect.iscoroutinefunction(handle_mirror_schedule_index):
        _ok("handle_mirror_schedule_index is async")
    else:
        _bad("handle_mirror_schedule_index async", "not a coroutine function")
    if inspect.iscoroutinefunction(handle_mirror_recent_execution):
        _ok("handle_mirror_recent_execution is async")
    else:
        _bad("handle_mirror_recent_execution async", "not a coroutine function")


def test_primitives_registered() -> None:
    print("\n[3] Primitives registered in HANDLERS")
    try:
        from services.primitives.registry import HANDLERS
    except ImportError as e:
        _bad("registry imports", str(e))
        return
    if "MirrorScheduleIndex" in HANDLERS:
        _ok("MirrorScheduleIndex in HANDLERS")
    else:
        _bad("MirrorScheduleIndex in HANDLERS", "key absent")
    if "MirrorRecentExecution" in HANDLERS:
        _ok("MirrorRecentExecution in HANDLERS")
    else:
        _bad("MirrorRecentExecution in HANDLERS", "key absent")


# ---------------------------------------------------------------------------
# 3. Primitives NOT in LLM tool surfaces (kernel maintenance only)
# ---------------------------------------------------------------------------

def test_primitives_not_in_llm_surfaces() -> None:
    print("\n[4] Primitives NOT exposed to LLM (kernel maintenance only)")
    try:
        from services.primitives.registry import (
            CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, REVIEWER_PRIMITIVES,
        )
    except ImportError as e:
        _bad("primitive surface imports", str(e))
        return
    surfaces = {
        "CHAT_PRIMITIVES": CHAT_PRIMITIVES,
        "HEADLESS_PRIMITIVES": HEADLESS_PRIMITIVES,
        "REVIEWER_PRIMITIVES": REVIEWER_PRIMITIVES,
    }
    for surface_name, surface in surfaces.items():
        # Surfaces are lists of tool dicts with a "name" field
        names = {
            tool.get("name") for tool in surface
            if isinstance(tool, dict)
        }
        for prim in ("MirrorScheduleIndex", "MirrorRecentExecution"):
            if prim in names:
                _bad(
                    f"{prim} NOT in {surface_name}",
                    f"found in {surface_name} — should be kernel-only",
                )
            else:
                _ok(f"{prim} not in {surface_name}")


# ---------------------------------------------------------------------------
# 4. Envelope helper includes the new keys
# ---------------------------------------------------------------------------

def test_envelope_includes_new_keys() -> None:
    print("\n[5] Envelope helper declares schedule_index_md + recent_execution_md")
    try:
        from services.reviewer_envelope import _UNIVERSAL_ENVELOPE_DECLS
    except ImportError as e:
        _bad("envelope helper import", str(e))
        return
    keys = {key for key, _ in _UNIVERSAL_ENVELOPE_DECLS}
    if "schedule_index_md" in keys:
        _ok("schedule_index_md in _UNIVERSAL_ENVELOPE_DECLS")
    else:
        _bad(
            "schedule_index_md in _UNIVERSAL_ENVELOPE_DECLS",
            f"keys present: {sorted(keys)}",
        )
    if "recent_execution_md" in keys:
        _ok("recent_execution_md in _UNIVERSAL_ENVELOPE_DECLS")
    else:
        _bad(
            "recent_execution_md in _UNIVERSAL_ENVELOPE_DECLS",
            f"keys present: {sorted(keys)}",
        )


# ---------------------------------------------------------------------------
# 5. Operating Context block consolidated into envelope helper (ADR-301 D5)
# ---------------------------------------------------------------------------

def test_operating_context_consolidated() -> None:
    print("\n[6] build_operating_context_block lives in reviewer_envelope (ADR-301 D5)")
    try:
        from services.reviewer_envelope import build_operating_context_block as src
    except ImportError as e:
        _bad("envelope helper exports build_operating_context_block", str(e))
        return
    if callable(src):
        _ok("services.reviewer_envelope.build_operating_context_block exists")
    else:
        _bad("envelope helper symbol callable", "not callable")

    # Re-export shim preserved for ADR-274 contract
    try:
        from agents.reviewer_agent import build_operating_context_block as shim
    except ImportError as e:
        _bad("agents.reviewer_agent re-export shim", str(e))
        return
    if shim is src:
        _ok("agents.reviewer_agent.build_operating_context_block is the same function (re-export)")
    else:
        _bad(
            "re-export identity",
            "agents.reviewer_agent.build_operating_context_block is a parallel impl, not re-export",
        )


# ---------------------------------------------------------------------------
# 6. ReviewerContext TypedDict declares new fields
# ---------------------------------------------------------------------------

def test_reviewer_context_fields() -> None:
    print("\n[7] ReviewerContext declares schedule_index_md + recent_execution_md")
    try:
        from agents.reviewer_agent import ReviewerContext
    except ImportError as e:
        _bad("ReviewerContext import", str(e))
        return
    annotations = getattr(ReviewerContext, "__annotations__", {})
    for field in ("schedule_index_md", "recent_execution_md"):
        if field in annotations:
            _ok(f"ReviewerContext.{field} declared")
        else:
            _bad(
                f"ReviewerContext.{field} declared",
                f"annotations present: {sorted(annotations)}",
            )


# ---------------------------------------------------------------------------
# 7. _build_user_message reads new envelope keys
# ---------------------------------------------------------------------------

def test_build_user_message_reads_new_keys() -> None:
    print("\n[8] _build_user_message renders schedule_index + recent_execution sections")
    try:
        import agents.reviewer_agent as ra
    except ImportError as e:
        _bad("agents.reviewer_agent import", str(e))
        return
    src = inspect.getsource(ra._build_user_message)
    if 'ctx.get("schedule_index_md")' in src:
        _ok("_build_user_message reads ctx['schedule_index_md']")
    else:
        _bad(
            "_build_user_message reads schedule_index_md",
            "ctx.get('schedule_index_md') not found in function source",
        )
    if 'ctx.get("recent_execution_md")' in src:
        _ok("_build_user_message reads ctx['recent_execution_md']")
    else:
        _bad(
            "_build_user_message reads recent_execution_md",
            "ctx.get('recent_execution_md') not found in function source",
        )


# ---------------------------------------------------------------------------
# 8. Persona frame contains Pulse Discipline section
# ---------------------------------------------------------------------------

def test_persona_frame_pulse_discipline() -> None:
    """Post-ADR-306 collapse: Pulse Discipline is substrate pedagogy (ablation
    §3 row 8 — `pulse_discipline` DELETE-REDUNDANT) and relocates from the
    persona frame to `_workspace_guide.md` (ADR-281's home, Phase C). The
    Reviewer reads the guide every wake; the discipline (read pulse files
    before reasoning about cadence) is preserved, only its home moved.

    Hardened to a real `assert` (the prior `_ok`/`_bad`+try/except shape
    false-passed once `_PERSONA_FRAME` was deleted — pytest collected the
    ImportError branch as a pass).
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    for bundle in ("alpha-trader", "alpha-author"):
        guide = (
            repo_root
            / "docs" / "programs" / bundle / "reference-workspace"
            / "_workspace_guide.md"
        ).read_text(encoding="utf-8")
        assert "Pulse Discipline (ADR-301)" in guide, (
            f"{bundle} _workspace_guide.md must carry the 'Pulse Discipline "
            "(ADR-301)' section (relocated from the persona frame per ADR-306 D3)"
        )
        assert "_schedule_index.md" in guide, (
            f"{bundle} _workspace_guide.md pulse section must name _schedule_index.md"
        )
        assert "_recent_execution.md" in guide, (
            f"{bundle} _workspace_guide.md pulse section must name _recent_execution.md"
        )


# ---------------------------------------------------------------------------
# 9. Scheduler tick invokes kernel mirrors (ADR-301 D4)
# ---------------------------------------------------------------------------

def test_scheduler_invokes_kernel_mirrors() -> None:
    print("\n[10] unified_scheduler maintenance phase invokes kernel mirrors")
    # Read source as text to avoid importing the full module (which pulls
    # sentry_sdk + other runtime deps not always present in the local venv).
    sched_path = ROOT / "jobs" / "unified_scheduler.py"
    if not sched_path.exists():
        _bad("unified_scheduler.py exists", f"not found at {sched_path}")
        return
    src = sched_path.read_text()
    if "mirror_schedule_index_for_all_users" in src:
        _ok("unified_scheduler imports mirror_schedule_index_for_all_users")
    else:
        _bad(
            "unified_scheduler imports mirror_schedule_index_for_all_users",
            "not found in module source",
        )
    if "mirror_recent_execution_for_all_users" in src:
        _ok("unified_scheduler imports mirror_recent_execution_for_all_users")
    else:
        _bad(
            "unified_scheduler imports mirror_recent_execution_for_all_users",
            "not found in module source",
        )
    if "from services.kernel_mirrors import" in src:
        _ok("unified_scheduler imports from services.kernel_mirrors")
    else:
        _bad(
            "unified_scheduler imports from services.kernel_mirrors",
            "import statement not found",
        )


# ---------------------------------------------------------------------------
# 10. kernel_mirrors helpers exist
# ---------------------------------------------------------------------------

def test_kernel_mirrors_helpers() -> None:
    print("\n[11] services.kernel_mirrors exposes per-workspace iteration helpers")
    try:
        from services.kernel_mirrors import (
            mirror_schedule_index_for_all_users,
            mirror_recent_execution_for_all_users,
        )
    except ImportError as e:
        _bad("services.kernel_mirrors import", str(e))
        return
    if inspect.iscoroutinefunction(mirror_schedule_index_for_all_users):
        _ok("mirror_schedule_index_for_all_users is async")
    else:
        _bad(
            "mirror_schedule_index_for_all_users async",
            "not a coroutine function",
        )
    if inspect.iscoroutinefunction(mirror_recent_execution_for_all_users):
        _ok("mirror_recent_execution_for_all_users is async")
    else:
        _bad(
            "mirror_recent_execution_for_all_users async",
            "not a coroutine function",
        )


# ---------------------------------------------------------------------------
# 11. (RETIRED by ADR-327) Cleanup 2 tested Pace.min_interval_seconds + the
# pace-driven drainer throttle — both DELETED by ADR-327 (pace retires;
# the drainer is lane-agnostic, cost bounded by the window budget). Test
# removed rather than patched: it validated removed behavior, and conflating
# budget assertions into the ADR-301 pulse gate would mix two ADRs.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 12. ADR-301 ADR doc exists
# ---------------------------------------------------------------------------

def test_adr_doc_exists() -> None:
    print("\n[13] ADR-301 doc exists in docs/adr/")
    adr_path = ROOT.parent / "docs" / "adr" / "ADR-301-reviewer-pulse-envelope.md"
    if adr_path.exists():
        _ok(f"{adr_path.name} exists")
    else:
        _bad("ADR-301 doc exists", f"not found at {adr_path}")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("ADR-301 — Reviewer Pulse Envelope: Regression Gate")
    print("=" * 70)

    test_path_constants()
    test_primitives_exist()
    test_primitives_registered()
    test_primitives_not_in_llm_surfaces()
    test_envelope_includes_new_keys()
    test_operating_context_consolidated()
    test_reviewer_context_fields()
    test_build_user_message_reads_new_keys()
    test_persona_frame_pulse_discipline()
    test_scheduler_invokes_kernel_mirrors()
    test_kernel_mirrors_helpers()
    # test_pace_min_interval_singular retired by ADR-327 (pace deleted)
    test_adr_doc_exists()

    print("\n" + "=" * 70)
    print(f"PASS: {len(_PASS)}  FAIL: {len(_FAIL)}")
    print("=" * 70)
    if _FAIL:
        print("\nFailures:")
        for name, reason in _FAIL:
            print(f"  - {name}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
