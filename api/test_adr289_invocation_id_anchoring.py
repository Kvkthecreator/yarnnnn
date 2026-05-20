"""ADR-289 Phase 1 regression gate — invocation_id substrate anchoring.

ADR-289 D2 re-anchors `metadata.invocation_id` from the dead `agent_runs.id`
link to the canonical `execution_events.id`. D3 commits addressed cycles to
becoming first-class invocations. D4 + D5 propagate the id through the
Reviewer loop and onto every emitted narrative row.

These are source-level static assertions — no live DB. The tests verify the
structural wiring is in place; live behavior validation happens at deploy
time when an addressed cycle produces matching invocation_id stamps across
session_messages and execution_events rows.

Phase 1 scope (BE substrate alignment):

  1. ReviewerOutput TypedDict declares invocation_id.
  2. invoke_reviewer accepts invocation_id as required keyword param.
  3. Reviewer's actions_taken records stamp invocation_id.
  4. surface_reviewer_actions reads action.invocation_id and passes to
     write_narrative_entry.
  5. write_reviewer_message accepts invocation_id and passes through.
  6. record_execution_event accepts caller-supplied id and returns it.
  7. invocation_dispatcher (judgment path) pre-generates the id and stamps
     execution_events + invoke_reviewer call.
  8. routes/feed.py addressed path pre-generates the id, stamps on user
     message metadata, threads to _dispatch_reviewer_turn, and writes
     execution_events at cycle close.
  9. review_proposal_dispatch._run_ai_reviewer threads invocation_id to
     invoke_reviewer + write_reviewer_message sites.
 10. narrative.py docstring documents invocation_id as execution_events.id
     (not agent_runs.id — the dead pre-ADR-289 link).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


def _read(path: str) -> str:
    return (API_DIR / path).read_text(encoding="utf-8")


# -----------------------------------------------------------------------------
# D4 — ReviewerOutput + invoke_reviewer signature
# -----------------------------------------------------------------------------

def test_reviewer_output_typeddict_declares_invocation_id():
    """ReviewerOutput TypedDict exposes invocation_id field per ADR-289 D4."""
    src = _read("agents/reviewer_agent.py")
    # Look for invocation_id field in ReviewerOutput class body
    m = re.search(
        r"class ReviewerOutput\(TypedDict.*?\n.*?invocation_id\s*:\s*str",
        src, re.DOTALL,
    )
    assert m, (
        "ReviewerOutput must declare `invocation_id: str` per ADR-289 D4."
    )


def test_invoke_reviewer_accepts_invocation_id_kwarg():
    """invoke_reviewer signature includes invocation_id as required kwarg."""
    src = _read("agents/reviewer_agent.py")
    # The signature spans several lines; allow any whitespace.
    m = re.search(
        r"async def invoke_reviewer\([^)]*?invocation_id\s*:\s*str[^)]*?\)",
        src, re.DOTALL,
    )
    assert m, (
        "invoke_reviewer must accept `invocation_id: str` per ADR-289 D4."
    )


def test_reviewer_action_records_stamp_invocation_id():
    """Reviewer's actions_taken append site stamps invocation_id per ADR-289 D4."""
    src = _read("agents/reviewer_agent.py")
    # Look for the action_record literal containing invocation_id near the
    # actions_taken.append site.
    m = re.search(
        r"action_record\s*:\s*dict\s*=\s*\{[^}]*?\"invocation_id\"\s*:\s*invocation_id",
        src, re.DOTALL,
    )
    assert m, (
        "Reviewer action_record must include invocation_id per ADR-289 D4."
    )


def test_reviewer_output_dict_stamps_invocation_id():
    """The verdict ReviewerOutput build stamps invocation_id per ADR-289 D4."""
    src = _read("agents/reviewer_agent.py")
    # Final output dict literal contains "invocation_id": invocation_id
    m = re.search(
        r'output\s*:\s*ReviewerOutput\s*=\s*\{[^}]*?"invocation_id"\s*:\s*invocation_id',
        src, re.DOTALL,
    )
    assert m, (
        "Final ReviewerOutput dict must include invocation_id per ADR-289 D4."
    )


# -----------------------------------------------------------------------------
# D5 — surface_reviewer_actions + write_reviewer_message
# -----------------------------------------------------------------------------

def test_surface_reviewer_actions_reads_invocation_id_from_action():
    """surface_reviewer_actions reads invocation_id off each action record."""
    src = _read("services/reviewer_chat_surfacing.py")
    # Must read action.get("invocation_id") AND pass to write_narrative_entry.
    assert 'action.get("invocation_id")' in src, (
        "surface_reviewer_actions must read invocation_id from action record."
    )
    # Find the write_narrative_entry call body and verify invocation_id is passed.
    m = re.search(
        r"write_narrative_entry\([^)]*?invocation_id\s*=\s*action_invocation_id",
        src, re.DOTALL,
    )
    assert m, (
        "surface_reviewer_actions must pass invocation_id to write_narrative_entry."
    )


def test_write_reviewer_message_accepts_invocation_id():
    """write_reviewer_message accepts invocation_id kwarg."""
    src = _read("services/reviewer_chat_surfacing.py")
    m = re.search(
        r"async def write_reviewer_message\([^)]*?invocation_id\s*:\s*Optional\[str\]",
        src, re.DOTALL,
    )
    assert m, (
        "write_reviewer_message must accept invocation_id per ADR-289 D5."
    )


def test_write_reviewer_message_passes_invocation_id_to_narrative():
    """write_reviewer_message passes invocation_id to write_narrative_entry."""
    src = _read("services/reviewer_chat_surfacing.py")
    m = re.search(
        r"write_narrative_entry\([^)]*?invocation_id\s*=\s*invocation_id",
        src, re.DOTALL,
    )
    assert m, (
        "write_reviewer_message must pass invocation_id to write_narrative_entry."
    )


# -----------------------------------------------------------------------------
# D2 — record_execution_event accepts and returns id
# -----------------------------------------------------------------------------

def test_record_execution_event_accepts_id_parameter():
    """record_execution_event accepts caller-supplied UUID per ADR-289 D2."""
    src = _read("services/telemetry.py")
    m = re.search(
        r"def record_execution_event\([^)]*?id\s*:\s*Optional\[str\]",
        src, re.DOTALL,
    )
    assert m, (
        "record_execution_event must accept `id` per ADR-289 D2."
    )


def test_record_execution_event_returns_id():
    """record_execution_event returns the inserted row id per ADR-289 D2."""
    src = _read("services/telemetry.py")
    # Return type annotation
    m = re.search(
        r"def record_execution_event\([^)]*?\)\s*->\s*Optional\[str\]",
        src, re.DOTALL,
    )
    assert m, (
        "record_execution_event must declare `-> Optional[str]` per ADR-289 D2."
    )


# -----------------------------------------------------------------------------
# D3 + D4 — invocation_dispatcher judgment path
# -----------------------------------------------------------------------------

def test_dispatcher_pregenerates_invocation_id():
    """invocation_dispatcher judgment path pre-generates UUID."""
    src = _read("services/invocation_dispatcher.py")
    assert "invocation_id = str(_uuid.uuid4())" in src, (
        "Judgment dispatch must pre-generate invocation_id per ADR-289 D3."
    )


def test_dispatcher_passes_invocation_id_to_invoke_reviewer():
    """Judgment dispatcher passes invocation_id to invoke_reviewer call."""
    src = _read("services/invocation_dispatcher.py")
    m = re.search(
        r"invoke_reviewer\([^)]*?invocation_id\s*=\s*invocation_id",
        src, re.DOTALL,
    )
    assert m, (
        "Judgment dispatcher must pass invocation_id to invoke_reviewer."
    )


def test_dispatcher_stamps_execution_events_with_id():
    """Judgment dispatcher passes id=invocation_id to record_execution_event."""
    src = _read("services/invocation_dispatcher.py")
    # Expect both the success and failure record_execution_event calls
    # to stamp id=invocation_id.
    matches = re.findall(
        r"record_execution_event\([^)]*?id\s*=\s*invocation_id",
        src, re.DOTALL,
    )
    assert len(matches) >= 2, (
        "Judgment dispatcher must stamp id=invocation_id on both success and "
        "failure execution_events writes per ADR-289 D2."
    )


# -----------------------------------------------------------------------------
# D3 — routes/feed.py addressed cycle
# -----------------------------------------------------------------------------

def test_addressed_cycle_pregenerates_invocation_id():
    """routes/feed.py addressed cycle pre-generates invocation_id."""
    src = _read("routes/feed.py")
    # Look inside response_stream for the uuid generation.
    assert "invocation_id = str(_uuid.uuid4())" in src, (
        "Addressed cycle must pre-generate invocation_id per ADR-289 D3."
    )


def test_addressed_cycle_stamps_user_message_metadata():
    """routes/feed.py stamps invocation_id on operator user message."""
    src = _read("routes/feed.py")
    # User message append_message should include invocation_id in metadata.
    m = re.search(
        r'append_message\([^)]*?"user"[^)]*?"invocation_id"\s*:\s*invocation_id',
        src, re.DOTALL,
    )
    assert m, (
        "User message append must stamp invocation_id in metadata per ADR-289 D3."
    )


def test_addressed_cycle_passes_invocation_id_to_dispatcher():
    """response_stream passes invocation_id to _dispatch_reviewer_turn."""
    src = _read("routes/feed.py")
    m = re.search(
        r"_dispatch_reviewer_turn\([^)]*?invocation_id\)",
        src, re.DOTALL,
    )
    assert m, (
        "response_stream must pass invocation_id to _dispatch_reviewer_turn."
    )


def test_addressed_cycle_stamps_system_agent_narrations():
    """System Agent narrations during addressed cycle stamp invocation_id."""
    src = _read("routes/feed.py")
    # Find the append_message calls for system_agent role and verify
    # invocation_id is in the metadata dict.
    matches = re.findall(
        r'append_message\([^)]*?"system_agent"[^)]*?"invocation_id"\s*:\s*invocation_id',
        src, re.DOTALL,
    )
    assert len(matches) >= 2, (
        "Both progress-drain and post-loop drain system_agent narrations must "
        "stamp invocation_id per ADR-289 D3 (expected 2 sites, found %d)." % len(matches)
    )


def test_addressed_cycle_finalizes_execution_events_on_success():
    """Addressed cycle writes execution_events row on success."""
    src = _read("routes/feed.py")
    m = re.search(
        r'record_execution_event\([^)]*?slug="addressed"[^)]*?id=invocation_id[^)]*?status="success"',
        src, re.DOTALL,
    )
    assert m, (
        "Addressed cycle must finalize execution_events on success per ADR-289 D3."
    )


def test_addressed_cycle_finalizes_execution_events_on_failure():
    """Addressed cycle writes execution_events row on failure."""
    src = _read("routes/feed.py")
    m = re.search(
        r'record_execution_event\([^)]*?slug="addressed"[^)]*?id=invocation_id[^)]*?status="failed"',
        src, re.DOTALL,
    )
    assert m, (
        "Addressed cycle must finalize execution_events on failure per ADR-289 D3."
    )


# -----------------------------------------------------------------------------
# D5 — proposal-arrival reactive (review_proposal_dispatch)
# -----------------------------------------------------------------------------

def test_proposal_dispatch_pregenerates_invocation_id():
    """_run_ai_reviewer pre-generates invocation_id."""
    src = _read("services/review_proposal_dispatch.py")
    assert "invocation_id = str(_uuid.uuid4())" in src, (
        "_run_ai_reviewer must pre-generate invocation_id per ADR-289 D2."
    )


def test_proposal_dispatch_passes_invocation_id_to_invoke_reviewer():
    """_run_ai_reviewer passes invocation_id to invoke_reviewer."""
    src = _read("services/review_proposal_dispatch.py")
    m = re.search(
        r"invoke_reviewer\([^)]*?invocation_id\s*=\s*invocation_id",
        src, re.DOTALL,
    )
    assert m, (
        "_run_ai_reviewer must pass invocation_id to invoke_reviewer."
    )


def test_proposal_dispatch_write_reviewer_message_sites_stamp_invocation_id():
    """All write_reviewer_message calls in _run_ai_reviewer stamp invocation_id."""
    src = _read("services/review_proposal_dispatch.py")
    # Count write_reviewer_message calls that pass invocation_id=invocation_id.
    matches = re.findall(
        r"invocation_id\s*=\s*invocation_id",
        src,
    )
    # Should be present at: invoke_reviewer call + advisory write + defer write +
    # _write_observation fallback call + _execute_reviewer_directives call.
    # Plus the `clarify` defer-path write_reviewer_message inside
    # _execute_reviewer_directives. Expect >= 5 stamps.
    assert len(matches) >= 5, (
        "_run_ai_reviewer-area must stamp invocation_id at >=5 write sites "
        "(found %d) per ADR-289 D5." % len(matches)
    )


def test_write_observation_accepts_invocation_id():
    """_write_observation accepts invocation_id kwarg."""
    src = _read("services/review_proposal_dispatch.py")
    m = re.search(
        r"async def _write_observation\([^)]*?invocation_id\s*:\s*Optional\[str\]",
        src, re.DOTALL,
    )
    assert m, (
        "_write_observation must accept invocation_id per ADR-289 D5."
    )


def test_execute_reviewer_directives_accepts_invocation_id():
    """_execute_reviewer_directives accepts invocation_id kwarg."""
    src = _read("services/review_proposal_dispatch.py")
    m = re.search(
        r"async def _execute_reviewer_directives\([^)]*?invocation_id\s*:\s*str\s*\|\s*None",
        src, re.DOTALL,
    )
    assert m, (
        "_execute_reviewer_directives must accept invocation_id per ADR-289 D5."
    )


# -----------------------------------------------------------------------------
# D2 — narrative.py docstring re-anchored
# -----------------------------------------------------------------------------

def test_narrative_docstring_references_execution_events():
    """narrative.py docstring documents invocation_id as execution_events.id."""
    src = _read("services/narrative.py")
    # Either header docstring or write_narrative_entry docstring must
    # name execution_events.id as the canonical link target.
    assert "execution_events.id" in src or "execution_events row" in src, (
        "narrative.py must document invocation_id as execution_events.id "
        "(per ADR-289 D2) — found neither reference."
    )


def test_narrative_docstring_does_not_promise_agent_runs_link():
    """narrative.py docstring no longer claims invocation_id → agent_runs.id."""
    src = _read("services/narrative.py")
    # Pre-ADR-289 the docstring said "links to the agent_runs row" — that
    # claim is dead per ADR-289 D2. Allow legacy mentions only in comments
    # that explain the deprecation; require no bare promise of the link.
    m = re.search(
        r"links\s+to\s+the\s+agent_runs\s+row",
        src,
    )
    assert not m, (
        "narrative.py docstring must not promise invocation_id → agent_runs "
        "link (pre-ADR-289 wording). Re-anchor to execution_events.id."
    )


# -----------------------------------------------------------------------------
# Phase 2a — 3-bucket taxonomy + pulse fix (2026-05-20)
# -----------------------------------------------------------------------------

def test_phase2a_mirror_refresh_frozenset_exists():
    """surface_reviewer_actions exports REVIEWER_MIRROR_REFRESH_TOOLS."""
    src = _read("services/reviewer_chat_surfacing.py")
    assert "REVIEWER_MIRROR_REFRESH_TOOLS = frozenset({" in src, (
        "reviewer_chat_surfacing must define REVIEWER_MIRROR_REFRESH_TOOLS "
        "per ADR-289 Phase 2a (3-bucket taxonomy)."
    )
    # SyncPlatformState is the canonical mirror-refresh tool per ADR-264.
    assert "\"SyncPlatformState\"" in src, (
        "REVIEWER_MIRROR_REFRESH_TOOLS must include SyncPlatformState."
    )


def test_phase2a_is_mirror_refresh_classifier_exists():
    """is_mirror_refresh_action classifier is defined + exported."""
    src = _read("services/reviewer_chat_surfacing.py")
    assert "def is_mirror_refresh_action(" in src, (
        "is_mirror_refresh_action classifier must be defined per ADR-289 Phase 2a."
    )
    assert "def _is_mechanical_fire_invocation(" in src, (
        "_is_mechanical_fire_invocation helper must be defined per ADR-289 Phase 2a."
    )


def test_phase2a_surface_reviewer_actions_calls_classifier():
    """surface_reviewer_actions skips mirror-refresh actions."""
    src = _read("services/reviewer_chat_surfacing.py")
    # The filter call appears in the for-loop body after the cognition skip.
    m = re.search(
        r"if tool in REVIEWER_COGNITION_TOOLS:\s*\n\s*continue\s*\n"
        r"[^\n]*\n(?:[^\n]*\n){0,15}?\s*if is_mirror_refresh_action\(action,\s*client,\s*user_id\):",
        src, re.DOTALL,
    )
    assert m, (
        "surface_reviewer_actions must skip mirror-refresh actions after the "
        "cognition skip per ADR-289 Phase 2a."
    )


def test_phase2a_routes_feed_imports_canonical_filter():
    """routes/feed.py imports the canonical filter sets — Singular Implementation."""
    src = _read("routes/feed.py")
    m = re.search(
        r"from services\.reviewer_chat_surfacing import \(\s*\n"
        r"\s*REVIEWER_COGNITION_TOOLS as _COGNITION_ONLY,\s*\n"
        r"\s*is_mirror_refresh_action,",
        src, re.DOTALL,
    )
    assert m, (
        "routes/feed.py must import the canonical filter sets from "
        "reviewer_chat_surfacing (Singular Implementation per ADR-289 Phase 2a). "
        "The inline _COGNITION_ONLY duplicate must be deleted."
    )
    # Inline duplicate set must be gone.
    inline_duplicate = re.search(
        r"_COGNITION_ONLY\s*=\s*\{\s*\n\s*\"ReadFile\"",
        src, re.DOTALL,
    )
    assert not inline_duplicate, (
        "routes/feed.py must not redefine _COGNITION_ONLY inline — it's now "
        "imported as an alias from reviewer_chat_surfacing per ADR-289 Phase 2a."
    )


def test_phase2a_routes_feed_calls_mirror_refresh_classifier():
    """routes/feed.py live narration sites call is_mirror_refresh_action."""
    src = _read("routes/feed.py")
    # Both narration sites (live drain + post-loop drain) should invoke
    # the classifier on a synthetic action record.
    matches = re.findall(
        r"is_mirror_refresh_action\(_action_synth,\s*auth\.client,\s*auth\.user_id\)",
        src,
    )
    assert len(matches) >= 2, (
        "routes/feed.py must call is_mirror_refresh_action at both narration "
        "sites (live drain + post-loop drain) per ADR-289 Phase 2a — found %d."
        % len(matches)
    )


def test_phase2a_reviewer_agent_emits_input_on_tool_end():
    """reviewer_agent.invoke_reviewer emits 'input' in the tool_end event."""
    src = _read("agents/reviewer_agent.py")
    # The _emit({...}) block for tool_end must include 'input': inp so the
    # live narration site in routes/feed.py can classify mirror-refresh fires.
    m = re.search(
        r'await _emit\(\{[^}]*?"phase":\s*"tool_end"[^}]*?"input":\s*inp',
        src, re.DOTALL,
    )
    assert m, (
        "reviewer_agent.invoke_reviewer tool_end emit must include 'input': inp "
        "per ADR-289 Phase 2a (live narration mirror-refresh classifier needs it)."
    )


def test_phase2a_write_reviewer_message_accepts_pulse():
    """write_reviewer_message accepts optional pulse kwarg."""
    src = _read("services/reviewer_chat_surfacing.py")
    m = re.search(
        r"async def write_reviewer_message\([^)]*?pulse\s*:\s*Optional\[str\]",
        src, re.DOTALL,
    )
    assert m, (
        "write_reviewer_message must accept optional pulse kwarg per ADR-289 "
        "Phase 2a (addressed cycles need pulse='addressed', proposal-arrival "
        "defaults to 'reactive')."
    )


def test_phase2a_addressed_cycle_passes_pulse_addressed():
    """routes/feed.py addressed cycle passes pulse='addressed' to write_reviewer_message."""
    src = _read("routes/feed.py")
    m = re.search(
        r"write_reviewer_message\([^)]*?pulse\s*=\s*\"addressed\"",
        src, re.DOTALL,
    )
    assert m, (
        "Addressed-cycle write_reviewer_message must pass pulse='addressed' "
        "per ADR-289 Phase 2a — fixes the blank-after-send filter bug."
    )


if __name__ == "__main__":
    # Mini in-file runner — same pattern as ADR-288's gate.
    import traceback
    tests = [
        (name, fn) for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL  {name}\n      {e}")
            failed += 1
        except Exception:
            print(f"ERROR {name}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed}/{len(tests)} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
