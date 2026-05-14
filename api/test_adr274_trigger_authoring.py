"""Regression gate for ADR-274 / FOUNDATIONS v8.5 Axiom 4 amendment.

Trigger authoring is an Identity-layer responsibility. The Schedule
primitive must fail fast on missing `authored_by`. Reviewer wakes must
carry an Operating Context block. All three runtime Schedule callers
(Reviewer dispatch, YARNNN tool_executor, execution_router pause/resume)
must inject `authored_by` correctly.

Run:
    python -m api.test_adr274_trigger_authoring
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import sys
from pathlib import Path


# Path bootstrap (mirrors other ADR gates)
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
# 1. Schedule primitive fail-fast on missing authored_by
# ---------------------------------------------------------------------------

def test_schedule_fails_fast_on_missing_authored_by() -> None:
    from services.primitives.schedule import handle_schedule

    class _Auth:
        user_id = "00000000-0000-0000-0000-000000000000"
        client = None

    # Missing entirely
    result = asyncio.run(handle_schedule(_Auth(), {"action": "create", "slug": "x"}))
    if result.get("success") is False and result.get("error") == "missing_authored_by":
        _ok("Schedule rejects missing authored_by with error='missing_authored_by'")
    else:
        _bad(
            "Schedule rejects missing authored_by",
            f"Expected success=False + error=missing_authored_by, got {result!r}",
        )

    # Empty string
    result = asyncio.run(
        handle_schedule(_Auth(), {"action": "create", "slug": "x", "authored_by": ""})
    )
    if result.get("success") is False and result.get("error") == "missing_authored_by":
        _ok("Schedule rejects empty-string authored_by")
    else:
        _bad(
            "Schedule rejects empty-string authored_by",
            f"Expected success=False + error=missing_authored_by, got {result!r}",
        )

    # Whitespace-only
    result = asyncio.run(
        handle_schedule(_Auth(), {"action": "create", "slug": "x", "authored_by": "   "})
    )
    if result.get("success") is False and result.get("error") == "missing_authored_by":
        _ok("Schedule rejects whitespace-only authored_by")
    else:
        _bad(
            "Schedule rejects whitespace-only authored_by",
            f"Expected success=False + error=missing_authored_by, got {result!r}",
        )

    # Non-string
    result = asyncio.run(
        handle_schedule(_Auth(), {"action": "create", "slug": "x", "authored_by": 42})
    )
    if result.get("success") is False and result.get("error") == "missing_authored_by":
        _ok("Schedule rejects non-string authored_by")
    else:
        _bad(
            "Schedule rejects non-string authored_by",
            f"Expected success=False + error=missing_authored_by, got {result!r}",
        )


# ---------------------------------------------------------------------------
# 2. Operating Context block helper exists + returns Axiom-4-shaped content
# ---------------------------------------------------------------------------

def test_operating_context_block_helper() -> None:
    from agents.reviewer_agent import build_operating_context_block

    sig = inspect.signature(build_operating_context_block)
    if list(sig.parameters.keys()) == ["client", "user_id"]:
        _ok("build_operating_context_block(client, user_id) signature")
    else:
        _bad(
            "build_operating_context_block signature",
            f"Expected (client, user_id), got {list(sig.parameters.keys())}",
        )

    # Helper must be defensive — None client + None user_id still produces a
    # block (it gracefully degrades; market/tenure fields are best-effort).
    block = build_operating_context_block(client=None, user_id="00000000-0000-0000-0000-000000000000")
    if "Operating Context" in block and "Axiom 4 v8.5" in block:
        _ok("Operating Context block contains Axiom-4-versioned header")
    else:
        _bad(
            "Operating Context block header",
            f"Expected 'Operating Context' + 'Axiom 4 v8.5' in:\n{block!r}",
        )

    if "**Now**:" in block and "**Operator timezone**:" in block:
        _ok("Operating Context block contains Now + timezone fields")
    else:
        _bad("Operating Context fields", f"Missing required fields in:\n{block!r}")


# ---------------------------------------------------------------------------
# 3. Reviewer persona frame includes cadence-authoring discipline section
# ---------------------------------------------------------------------------

def test_reviewer_persona_includes_cadence_authoring() -> None:
    from agents.reviewer_agent import _PERSONA_FRAME

    needles = [
        "operating cadence is yours to author",
        "FOUNDATIONS v8.5 Axiom 4",
        "Derived Principle 18",
        "ADR-274",
        "Schedule(action=",
        "scaffolds",
        "bundle-fork",
        "ListRevisions",
        "Operating Context",
    ]
    missing = [n for n in needles if n not in _PERSONA_FRAME]
    if not missing:
        _ok("Reviewer persona frame names cadence-authoring discipline (9 markers)")
    else:
        _bad(
            "Reviewer persona cadence-authoring section",
            f"Missing markers: {missing!r}",
        )


# ---------------------------------------------------------------------------
# 4. ReviewerContext TypedDict carries operating_context_block
# ---------------------------------------------------------------------------

def test_reviewer_context_has_operating_context_field() -> None:
    from agents.reviewer_agent import ReviewerContext

    annotations = getattr(ReviewerContext, "__annotations__", {})
    if "operating_context_block" in annotations:
        _ok("ReviewerContext.operating_context_block field declared")
    else:
        _bad(
            "ReviewerContext field",
            f"operating_context_block missing from annotations: "
            f"{list(annotations.keys())}",
        )


# ---------------------------------------------------------------------------
# 5. _build_user_message injects the operating context block
# ---------------------------------------------------------------------------

def test_build_user_message_injects_operating_context() -> None:
    import agents.reviewer_agent as mod
    src = inspect.getsource(mod._build_user_message)
    if 'ctx.get("operating_context_block")' in src:
        _ok("_build_user_message reads ctx['operating_context_block']")
    else:
        _bad(
            "_build_user_message wiring",
            "Expected ctx.get('operating_context_block') in body",
        )


# ---------------------------------------------------------------------------
# 6. Reviewer dispatch loop auto-tags Schedule calls with reviewer identity
# ---------------------------------------------------------------------------

def test_reviewer_dispatch_injects_reviewer_authored_by() -> None:
    import agents.reviewer_agent as mod
    src = inspect.getsource(mod)
    needle = 'name == "Schedule"'
    inj = '"authored_by": f"reviewer:{REVIEWER_MODEL_IDENTITY}"'
    # We accept the substring even within an f-string assignment shape
    inj_alt = 'authored_by": f"reviewer:'
    if needle in src and (inj in src or inj_alt in src):
        _ok("Reviewer dispatch loop injects reviewer-authored authored_by on Schedule")
    else:
        _bad(
            "Reviewer dispatch Schedule injection",
            f'Expected `name == "Schedule"` + reviewer authored_by pattern',
        )


# ---------------------------------------------------------------------------
# 7. YARNNN tool_executor injects authored_by="operator" for Schedule
# ---------------------------------------------------------------------------

def test_yarnnn_tool_executor_injects_operator_authored_by() -> None:
    src = (ROOT / "agents" / "yarnnn.py").read_text()
    if 'tool_name == "Schedule"' in src and '"authored_by": "operator"' in src:
        _ok("YARNNN tool_executor injects authored_by='operator' for Schedule")
    else:
        _bad(
            "YARNNN tool_executor injection",
            'Expected tool_name == "Schedule" + "authored_by": "operator"',
        )


# ---------------------------------------------------------------------------
# 8. execution_router pause/resume pass authored_by="operator"
# ---------------------------------------------------------------------------

def test_execution_router_pause_resume_authored_by() -> None:
    src = (ROOT / "services" / "execution_router.py").read_text()
    pause_ok = '"action": "pause"' in src and '"authored_by": "operator"' in src
    resume_ok = '"action": "resume"' in src
    if pause_ok and resume_ok:
        # Check both pause + resume each carry authored_by
        n = src.count('"authored_by": "operator"')
        if n >= 2:
            _ok(f"execution_router pause+resume both pass authored_by='operator' (count={n})")
        else:
            _bad(
                "execution_router authored_by",
                f"Expected ≥2 'authored_by': 'operator' occurrences, found {n}",
            )
    else:
        _bad("execution_router authored_by", "Missing pause/resume + authored_by markers")


# ---------------------------------------------------------------------------
# 9. invocation_dispatcher wires operating_context_block on recurrence fires
# ---------------------------------------------------------------------------

def test_invocation_dispatcher_wires_operating_context() -> None:
    src = (ROOT / "services" / "invocation_dispatcher.py").read_text()
    if (
        "build_operating_context_block" in src
        and '"operating_context_block": operating_context' in src
    ):
        _ok("invocation_dispatcher imports + wires operating_context_block")
    else:
        _bad(
            "invocation_dispatcher wiring",
            "Expected build_operating_context_block import + context-bag assignment",
        )


# ---------------------------------------------------------------------------
# 10. routes/feed.py wires operating_context_block on addressed turns
# ---------------------------------------------------------------------------

def test_feed_route_wires_operating_context() -> None:
    src = (ROOT / "routes" / "feed.py").read_text()
    if (
        "build_operating_context_block" in src
        and '"operating_context_block": operating_context' in src
    ):
        _ok("routes/feed.py imports + wires operating_context_block")
    else:
        _bad(
            "routes/feed.py wiring",
            "Expected build_operating_context_block import + context-bag assignment",
        )


# ---------------------------------------------------------------------------
# 11. All known Schedule callers either inject or pass authored_by
# ---------------------------------------------------------------------------

def test_all_schedule_callers_provide_authored_by() -> None:
    """Sweep grep: every call site of handle_schedule must either pass
    authored_by literally or be reached via an injecting layer. This is
    a static check against well-known files."""
    import re

    callers = {
        "services/execution_router.py": True,  # pause/resume literal
        "routes/recurrences.py": True,         # patch routes literal
        "scripts/oneshot/cleanup_orphan_recurrences.py": True,
        "agents/yarnnn.py": True,              # tool_executor injection
        "agents/reviewer_agent.py": True,      # dispatch injection
    }
    fails: list[str] = []
    for rel in callers:
        p = ROOT / rel
        if not p.exists():
            fails.append(f"{rel} missing on disk")
            continue
        text = p.read_text()
        if "authored_by" not in text:
            fails.append(f"{rel} no authored_by reference")
    if not fails:
        _ok("All known Schedule callers reference authored_by")
    else:
        _bad("Schedule caller sweep", "; ".join(fails))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    print("ADR-274 / FOUNDATIONS v8.5 — Trigger authoring is Identity-layer responsibility\n")

    test_schedule_fails_fast_on_missing_authored_by()
    test_operating_context_block_helper()
    test_reviewer_persona_includes_cadence_authoring()
    test_reviewer_context_has_operating_context_field()
    test_build_user_message_injects_operating_context()
    test_reviewer_dispatch_injects_reviewer_authored_by()
    test_yarnnn_tool_executor_injects_operator_authored_by()
    test_execution_router_pause_resume_authored_by()
    test_invocation_dispatcher_wires_operating_context()
    test_feed_route_wires_operating_context()
    test_all_schedule_callers_provide_authored_by()

    total = len(_PASS) + len(_FAIL)
    print(f"\n{len(_PASS)}/{total} pass")
    if _FAIL:
        print("\nFAILURES:")
        for name, reason in _FAIL:
            print(f"  • {name}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
