"""Regression gate for Reviewer Clarify Feed surfacing (2026-05-25).

When the Reviewer calls Clarify(question=..., options=...), the question
must reach the operator's Feed surface with role='reviewer' attribution
(persona bubble, not System Agent narration) and structured
clarify_question + clarify_options metadata for future FE affordances.

Closes the silenced-Clarify class documented in
docs/evaluations/2026-05-25-042827-clarify-silenced-from-feed/findings.md
(15/15 Reviewer Clarify wakes over 7 days produced zero session_messages
rows; operators had no signal that the Reviewer was asking for input).

Six surfaces verified:
  1. Clarify NOT in REVIEWER_COGNITION_TOOLS
  2. narrate_reviewer_action renders Clarify bare (no prefix)
  3. _summarize_result returns the question (+ options) instead of "ok"
  4. agent_narration event carries role + clarify_question + clarify_options
  5. surface_reviewer_actions writes Clarify with role='reviewer' + metadata
  6. reviewer_audit.py _detect_outcome_kind returns 'clarify' for any
     Clarify call (dead clarify_alert input-flag gate removed)

Run:
    python -m api.test_clarify_surfacing
"""

from __future__ import annotations

import asyncio
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
# Gap 1 — Clarify removed from REVIEWER_COGNITION_TOOLS
# ---------------------------------------------------------------------------

def test_clarify_not_in_cognition() -> None:
    print("\n[1] Clarify NOT in REVIEWER_COGNITION_TOOLS")
    try:
        from services.reviewer_chat_surfacing import REVIEWER_COGNITION_TOOLS
    except ImportError as e:
        _bad("import REVIEWER_COGNITION_TOOLS", str(e))
        return
    if "Clarify" in REVIEWER_COGNITION_TOOLS:
        _bad(
            "Clarify removed from REVIEWER_COGNITION_TOOLS",
            "still present — fix not applied",
        )
    else:
        _ok("Clarify is not in REVIEWER_COGNITION_TOOLS")
    # Sanity: other cognition tools still present
    for name in ("ReadFile", "ListFiles", "SearchFiles"):
        if name in REVIEWER_COGNITION_TOOLS:
            _ok(f"{name} still in REVIEWER_COGNITION_TOOLS (regression check)")
        else:
            _bad(
                f"regression: {name} should still be cognition",
                "missing from frozenset",
            )


# ---------------------------------------------------------------------------
# Gap 2 — narrate_reviewer_action Clarify branch
# ---------------------------------------------------------------------------

def test_narrate_clarify_branch() -> None:
    print("\n[2] narrate_reviewer_action renders Clarify bare (no prefix)")
    try:
        from services.reviewer_chat_surfacing import narrate_reviewer_action
    except ImportError as e:
        _bad("import narrate_reviewer_action", str(e))
        return
    out = narrate_reviewer_action("Clarify", "Did signal-eval fire today?")
    if out == "Did signal-eval fire today?":
        _ok("Clarify with question returns question bare")
    else:
        _bad(
            "Clarify with question returns question bare",
            f"got {out!r}",
        )
    out_empty = narrate_reviewer_action("Clarify", "")
    if "asked" in out_empty.lower() or "clarif" in out_empty.lower():
        _ok(f"Clarify with empty summary falls back to readable default ({out_empty!r})")
    else:
        _bad(
            "Clarify with empty summary falls back to readable default",
            f"got {out_empty!r}",
        )
    # Regression: non-Clarify tools still get prefix
    pa = narrate_reviewer_action("ProposeAction", "proposal_id=abc123...")
    if pa.startswith("Proposal submitted on Reviewer's direction"):
        _ok("ProposeAction still uses System Agent narration shape (regression)")
    else:
        _bad(
            "ProposeAction regression",
            f"got {pa!r}",
        )


# ---------------------------------------------------------------------------
# Gap 3 — _summarize_result Clarify branch
# ---------------------------------------------------------------------------

def test_summarize_clarify_branch() -> None:
    print("\n[3] _summarize_result extracts question (+ options) from Clarify result")
    try:
        from agents.reviewer_agent import _summarize_result
    except ImportError as e:
        _bad("import _summarize_result", str(e))
        return
    # Question only
    s1 = _summarize_result({
        "success": True,
        "question": "Approve closing the SPY position?",
        "options": [],
    })
    if s1 == "Approve closing the SPY position?":
        _ok("question-only result returns naked question")
    else:
        _bad(
            "question-only result",
            f"got {s1!r}",
        )
    # Question + options
    s2 = _summarize_result({
        "success": True,
        "question": "Stop trading Signal-1?",
        "options": ["yes", "no", "let me think"],
    })
    if "Stop trading Signal-1?" in s2 and "yes, no, let me think" in s2:
        _ok("question + options rendered together")
    else:
        _bad(
            "question + options rendering",
            f"got {s2!r}",
        )
    # Regression: ProposeAction result unchanged
    s3 = _summarize_result({
        "success": True,
        "proposal_id": "abc12345-...",
    })
    if "proposal_id=abc12345" in s3:
        _ok("ProposeAction summary regression preserved")
    else:
        _bad(
            "ProposeAction regression",
            f"got {s3!r}",
        )
    # Regression: failed result unchanged
    s4 = _summarize_result({"success": False, "error": "balance_exhausted"})
    if "error:" in s4 and "balance_exhausted" in s4:
        _ok("failure summary regression preserved")
    else:
        _bad("failure summary regression", f"got {s4!r}")


# ---------------------------------------------------------------------------
# Gap 4 — agent_narration event carries role + structured payload (addressed path)
# ---------------------------------------------------------------------------

def test_agent_narration_event_role_propagation() -> None:
    print("\n[4] wake.py::stream_addressed_wake yields role + clarify_question on agent_narration")
    src = (ROOT / "services" / "wake.py").read_text()
    # Both occurrences (drain block + post-drain block) updated
    role_assignments = src.count('row_role = "reviewer" if tool_name == "Clarify" else "system_agent"')
    if role_assignments >= 1:
        _ok(f"per-tool row_role assignment present ({role_assignments} site(s))")
    else:
        _bad(
            "per-tool row_role assignment",
            "expected `row_role = \"reviewer\" if tool_name == \"Clarify\" ...` in wake.py",
        )
    if '"role": row_role' in src:
        _ok("agent_narration event carries 'role' key")
    else:
        _bad("agent_narration carries 'role'", "expected '\"role\": row_role' in wake.py")
    if 'event_out["clarify_question"]' in src:
        _ok("agent_narration carries clarify_question when present")
    else:
        _bad("agent_narration carries clarify_question", "missing branch in wake.py")
    if 'event_out["clarify_options"]' in src:
        _ok("agent_narration carries clarify_options when present")
    else:
        _bad("agent_narration carries clarify_options", "missing branch in wake.py")


# ---------------------------------------------------------------------------
# Gap 5 — routes/feed.py honors event.role instead of hardcoding
# ---------------------------------------------------------------------------

def test_feed_route_honors_event_role() -> None:
    print("\n[5] routes/feed.py reads event['role'] instead of hardcoding 'system_agent'")
    src = (ROOT / "routes" / "feed.py").read_text()
    # Scope to the agent_narration handler block. The execution-router
    # path (_dispatch_execution_turn at ~line 1121) legitimately uses
    # role='system_agent' for deterministic-route narration and is
    # unrelated to Reviewer Clarify surfacing. We only care that the
    # agent_narration branch under elif etype == "agent_narration"
    # uses row_role (event-driven) instead of hardcoding.
    nar_idx = src.find('elif etype == "agent_narration":')
    if nar_idx == -1:
        _bad("locate agent_narration handler in feed.py", "block not found")
    else:
        # Examine the agent_narration block. Slice large enough to include
        # both the role assignment AND the append_message call ~25 lines
        # below it (each call is ~60-80 chars × ~25 lines + metadata dict).
        block = src[nar_idx:nar_idx + 2400]
        if 'append_message(auth.client, session_id, "system_agent", narration' in block:
            _bad(
                "agent_narration handler no longer hardcodes 'system_agent'",
                "stale hardcoded role still in the agent_narration branch — replace with row_role from event",
            )
        else:
            _ok("agent_narration handler no longer hardcodes 'system_agent'")
        if "append_message(auth.client, session_id, row_role, narration" in block:
            _ok("agent_narration handler calls append_message(..., row_role, ...)")
        else:
            _bad(
                "agent_narration handler uses row_role",
                "expected `append_message(auth.client, session_id, row_role, narration, ...)`",
            )
    if 'event.get("role", "system_agent")' in src:
        _ok("feed.py reads event.get('role', 'system_agent')")
    else:
        _bad(
            "feed.py reads event.role",
            "expected `event.get(\"role\", \"system_agent\")` in agent_narration handler",
        )
    if 'meta_out["clarify_question"]' in src:
        _ok("feed.py propagates clarify_question into metadata")
    else:
        _bad(
            "feed.py propagates clarify_question",
            "expected `meta_out[\"clarify_question\"]` in agent_narration handler",
        )


# ---------------------------------------------------------------------------
# Gap 6 — surface_reviewer_actions writes Clarify as role='reviewer'
# ---------------------------------------------------------------------------

def test_surface_reviewer_actions_clarify_role() -> None:
    print("\n[6] surface_reviewer_actions writes Clarify with role='reviewer' + metadata")

    # Capture write_narrative_entry calls
    captured_calls: list[dict] = []

    def fake_write(client, session_id, *, role, summary, body, pulse, weight,
                   invocation_id=None, extra_metadata=None, **kw):
        captured_calls.append({
            "role": role, "summary": summary, "body": body,
            "extra_metadata": dict(extra_metadata or {}),
        })
        return {"id": "fake-row-id"}

    def fake_find_session(client, user_id):
        return "fake-session-id"

    # Monkey-patch
    import services.narrative as nv
    orig_write = nv.write_narrative_entry
    orig_find = nv.find_active_workspace_session
    nv.write_narrative_entry = fake_write
    nv.find_active_workspace_session = fake_find_session

    try:
        from services.reviewer_chat_surfacing import surface_reviewer_actions

        actions = [
            {
                "tool": "Clarify",
                "input": {
                    "question": "Should I retire Signal-1?",
                    "options": ["yes", "no", "wait"],
                },
                "success": True,
                "summary": "Should I retire Signal-1? [yes, no, wait]",
                "invocation_id": "inv-1",
            }
        ]
        written = asyncio.run(surface_reviewer_actions(
            client=None, user_id="user-1", actions_taken=actions,
        ))
        if written != 1:
            _bad("Clarify writes exactly 1 narrative entry", f"written={written}")
            return
        _ok("Clarify writes exactly 1 narrative entry")
        if not captured_calls:
            _bad("captured a write call", "captured_calls is empty")
            return
        call = captured_calls[-1]
        if call["role"] == "reviewer":
            _ok("Clarify row uses role='reviewer' (persona bubble)")
        else:
            _bad("Clarify row uses role='reviewer'", f"got role={call['role']!r}")
        if "Should I retire Signal-1?" in (call["body"] or ""):
            _ok("Clarify row body contains the question")
        else:
            _bad("Clarify row body contains the question", f"got body={call['body']!r}")
        em = call["extra_metadata"]
        if em.get("clarify_question") == "Should I retire Signal-1?":
            _ok("clarify_question stamped on metadata")
        else:
            _bad(
                "clarify_question stamped on metadata",
                f"got extra_metadata={em!r}",
            )
        if em.get("clarify_options") == ["yes", "no", "wait"]:
            _ok("clarify_options stamped on metadata")
        else:
            _bad(
                "clarify_options stamped on metadata",
                f"got extra_metadata.clarify_options={em.get('clarify_options')!r}",
            )

        # Regression: non-Clarify action still uses system_agent role
        captured_calls.clear()
        actions_wf = [{
            "tool": "WriteFile",
            "input": {"path": "/workspace/review/notes.md"},
            "success": True,
            "summary": "path=/workspace/review/notes.md",
            "invocation_id": "inv-2",
        }]
        asyncio.run(surface_reviewer_actions(
            client=None, user_id="user-1", actions_taken=actions_wf,
        ))
        if captured_calls and captured_calls[-1]["role"] == "system_agent":
            _ok("WriteFile regression: still uses role='system_agent'")
        else:
            _bad(
                "WriteFile regression",
                f"captured role={captured_calls[-1]['role'] if captured_calls else 'none'!r}",
            )
    finally:
        nv.write_narrative_entry = orig_write
        nv.find_active_workspace_session = orig_find


# ---------------------------------------------------------------------------
# Gap 7 — reviewer_audit.py _detect_outcome_kind 'clarify' presence gate
# ---------------------------------------------------------------------------

def test_reviewer_audit_clarify_lineage_gate() -> None:
    print("\n[7] reviewer_audit.py _detect_outcome_kind returns 'clarify' on any Clarify call")
    try:
        from services.reviewer_audit import _detect_outcome_kind
    except ImportError as e:
        _bad("import _detect_outcome_kind", str(e))
        return
    # Bare Clarify (no input flag — pre-fix this would have returned None)
    kind = _detect_outcome_kind({
        "verdict": "stand_down",
        "actions_taken": [
            {"tool": "ReadFile", "input": {"path": "/workspace/X.md"}},
            {"tool": "Clarify", "input": {"question": "Approve close?"}},
        ],
    })
    if kind == "clarify":
        _ok("any Clarify call → outcome_kind='clarify' (presence gate)")
    else:
        _bad(
            "Clarify presence gate",
            f"got kind={kind!r} — expected 'clarify'",
        )
    # Cognition-only stand-down still produces None
    kind_none = _detect_outcome_kind({
        "verdict": "stand_down",
        "actions_taken": [
            {"tool": "ReadFile", "input": {"path": "/workspace/X.md"}},
            {"tool": "ListFiles", "input": {"prefix": "/workspace/"}},
        ],
    })
    if kind_none is None:
        _ok("cognition-only stand-down still returns None (regression)")
    else:
        _bad(
            "cognition-only regression",
            f"got kind={kind_none!r} — expected None",
        )
    # ProposeAction outranks Clarify (priority preserved)
    kind_priority = _detect_outcome_kind({
        "actions_taken": [
            {"tool": "Clarify", "input": {"question": "X?"}},
            {"tool": "ProposeAction", "input": {}},
        ],
    })
    if kind_priority == "propose_action":
        _ok("ProposeAction priority preserved over Clarify (regression)")
    else:
        _bad(
            "outcome-kind priority regression",
            f"got {kind_priority!r}",
        )
    # Dead clarify_alert input-flag check should be gone from source
    src = (ROOT / "services" / "reviewer_audit.py").read_text()
    if 'tool_input.get("clarify_alert")' in src:
        _bad(
            "dead clarify_alert input-flag check removed",
            "stale tool_input.get('clarify_alert') still present in source",
        )
    else:
        _ok("dead clarify_alert input-flag check removed from source")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("Reviewer Clarify Feed Surfacing — Regression Gate (2026-05-25)")
    print("=" * 70)

    test_clarify_not_in_cognition()
    test_narrate_clarify_branch()
    test_summarize_clarify_branch()
    test_agent_narration_event_role_propagation()
    test_feed_route_honors_event_role()
    test_surface_reviewer_actions_clarify_role()
    test_reviewer_audit_clarify_lineage_gate()

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
