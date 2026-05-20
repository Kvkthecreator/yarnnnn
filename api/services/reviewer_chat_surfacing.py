"""Reviewer → chat unified surfacing (ADR-212 / 2026-04-23 post-flip).

Under the sharp LAYER-MAPPING, the Reviewer is an Agent. Verdicts are the
Reviewer Agent's output. To give operators a unified timeline of their
workspace's activity — rather than forcing them to context-switch to
/review — every verdict also surfaces as a `role='reviewer'` message in
the operator's active chat session.

Migration 160 widened the session_messages.role CHECK constraint to
include 'reviewer'. Without that migration, inserts from this module
would fail the constraint.

## Single write path

`write_reviewer_message(client, user_id, *, content, metadata)` is the
sole entry point. Callers (propose_action.handle_execute_proposal,
propose_action.handle_reject_proposal, review_proposal_dispatch for
AI-defer + observe-only paths) call this helper after their primary
verdict write (to judgment_log.md + action_proposals).

Failure discipline: surfacing to chat is best-effort. If the session
lookup or message insert fails, we log and return — the verdict is
already persisted authoritatively in judgment_log.md + action_proposals.
The chat surfacing is the *second read path* for human visibility;
losing it doesn't lose the verdict.

## Which session?

Rule: write to the operator's most-recently-updated active workspace-
scoped chat session. If the operator hasn't chatted in 4+ hours
(inactivity rotation per ADR-067 / ADR-159), the current-active
session becomes a fresh one on their next /chat open — and the
verdict card appears there alongside YARNNN's welcome-back.

If no active session exists (operator hasn't chatted at all today),
we do NOT force-create a session. Creating empty sessions just to
hold unattended verdicts pollutes the session list. The verdict is
still fully captured in judgment_log.md + action_proposals — it just
won't appear in /chat retrospectively if they never chat today.
This is acceptable; /review is the authoritative audit trail.

## Metadata shape

The `role='reviewer'` message carries metadata the frontend uses for
rendering:

    {
        "proposal_id": "<uuid>",           # link back to /review
        "verdict": "approve|reject|defer|observation",
        "occupant": "<reviewer_identity>", # e.g. "human:<uid>", "ai:reviewer-sonnet-v1"
        "action_type": "<task_action>",    # e.g. "trading.submit_order_paper"
        "task_slug": "<slug>",             # if known
    }

Content is the reviewer's reasoning — the same text persisted to
judgment_log.md. Short (typically 2–5 sentences).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def write_reviewer_message(
    client: Any,
    user_id: str,
    *,
    content: str,
    proposal_id: Optional[str] = None,
    verdict: Optional[str] = None,
    occupant: Optional[str] = None,
    action_type: Optional[str] = None,
    task_slug: Optional[str] = None,
    invocation_id: Optional[str] = None,
    pulse: Optional[str] = None,
) -> Optional[dict]:
    """Surface a reviewer verdict to the operator's active chat session.

    Best-effort: never raises. Returns the inserted row on success,
    None on any failure path (no active session; insert failed; etc.).

    Callers should treat this as write-and-forget — the authoritative
    verdict record lives in judgment_log.md + action_proposals. This
    surfacing is for operator-facing timeline visibility.
    """
    if not user_id or not content:
        return None

    # 1. Find the operator's most-recent active workspace-scoped chat session.
    # Helper lives in services.narrative (promoted ADR-219 Commit 3 — every
    # autonomous-narrative-entry caller uses the same session resolver).
    from services.narrative import find_active_workspace_session

    session_id = find_active_workspace_session(client, user_id)
    if not session_id:
        logger.debug(
            "[REVIEWER_CHAT] no active session for user=%s; skipping surfacing",
            user_id[:8] if user_id else "?",
        )
        return None

    # 2. Build metadata payload.
    metadata: dict = {}
    if proposal_id:
        metadata["proposal_id"] = proposal_id
    if verdict:
        metadata["verdict"] = verdict
    if occupant:
        metadata["occupant"] = occupant
    if action_type:
        metadata["action_type"] = action_type
    if task_slug:
        metadata["task_slug"] = task_slug

    # 3. Emit one narrative entry. Per ADR-219 Commit 2 the single write
    #    path is services.narrative.write_narrative_entry; that helper
    #    handles the RPC + direct-insert fallback in one place.
    try:
        from services.narrative import write_narrative_entry

        # ADR-289 Phase 2a (2026-05-20): pulse defaults to 'reactive' for
        # backward-compat with proposal-arrival callers (review_proposal_dispatch);
        # the addressed-cycle caller in routes/feed.py passes pulse='addressed'
        # so the Reviewer's reply correctly classifies as part of the operator's
        # conversation. Pre-Phase-2a the pulse was hardcoded 'reactive' which
        # made the Reviewer's addressed-cycle reply fall outside
        # filterAddressedMessages — operator saw their question and a blank
        # panel (the reply got filtered).
        resolved_pulse = pulse or "reactive"
        verdict_label = (verdict or "decision").upper()
        if task_slug:
            summary = f"Reviewer {verdict_label} — {task_slug}"
        else:
            summary = f"Reviewer {verdict_label}"

        return write_narrative_entry(
            client,
            session_id,
            role="reviewer",
            summary=summary,
            body=content,
            pulse=resolved_pulse,
            weight="material",
            task_slug=task_slug,
            invocation_id=invocation_id,
            extra_metadata=metadata,
        )
    except Exception as exc:
        logger.warning(
            "[REVIEWER_CHAT] narrative write failed for user=%s: %s",
            user_id[:8] if user_id else "?",
            exc,
        )
        return None


# Active-session resolver moved to services.narrative.find_active_workspace_session
# (ADR-219 Commit 3 — promoted as the canonical helper for autonomous
# narrative entries; reviewer_chat_surfacing was its only caller).


# ---------------------------------------------------------------------------
# ADR-258 (revised 2026-05-08): Per-action System Agent narration helper
# ---------------------------------------------------------------------------
# Shared between chat.py (addressed trigger), invocation_dispatcher.py
# (heartbeat trigger), review_proposal_dispatch.py (proposal trigger), and
# back_office/reviewer_reflection.py (reflection trigger). All four trigger
# paths emit the same shape: Reviewer bubble + zero-or-more System Agent
# narration bubbles, one per consequential successful action.

REVIEWER_COGNITION_TOOLS = frozenset({
    "ReadFile", "ListFiles", "SearchFiles", "ListRevisions",
    "ReadRevision", "DiffRevisions", "GetSystemState", "SearchEntities",
    "LookupEntity", "list_integrations", "WebSearch", "QueryKnowledge",
    "DiscoverAgents", "ReadAgentFile", "ListEntities", "Clarify",
})

# ADR-289 Phase 2a (2026-05-20) + ADR-296 v2 D3 (2026-05-20): 3-bucket
# taxonomy for Reviewer action narration. Extends ADR-277's emission-at-
# source policy to Reviewer-directed mechanical-mirror tool calls.
#
# Pre-Phase-2a the binary taxonomy was cognition vs. consequential. The
# consequential bucket conflated two different shapes:
#   - Judgment-bearing actions (ProposeAction, WriteFile to operator
#     substrate, Schedule create/update/archive) → operator-relevant
#   - Substrate-mirror refresh (SyncPlatformState — the Reviewer's
#     mid-loop substrate refresh per ADR-264) → low operator-relevance
#     plumbing the Reviewer fires to get fresh state
#
# The 3-bucket taxonomy:
#   - REVIEWER_COGNITION_TOOLS    → silent (pure reads, no side-effect)
#   - REVIEWER_MIRROR_REFRESH_TOOLS → silent (side-effect but mechanical-
#                                     mirror substrate canonicalization,
#                                     not judgment)
#   - everything else              → emit System Agent narration
#
# ADR-296 v2 D3 narrowing: the FireInvocation branch of this classifier
# dissolved when FireInvocation left REVIEWER_PRIMITIVES. The Reviewer
# no longer commissions mechanical-mirror fires by name; mechanical
# mirrors run on their own cron-tick wake source schedule. Only the
# SyncPlatformState mid-loop override case remains.
REVIEWER_MIRROR_REFRESH_TOOLS = frozenset({
    "SyncPlatformState",
})


def is_mirror_refresh_action(action: dict, client: Any, user_id: str) -> bool:
    """Phase 2a 3-bucket taxonomy classifier — should this action be
    surfaced as a narrative entry, or is it substrate-mirror refresh
    that the operator doesn't need to see? Returns True to SKIP.

    Per ADR-296 v2 D3 the single path to True is `tool in
    REVIEWER_MIRROR_REFRESH_TOOLS` (today: SyncPlatformState). The
    pre-ADR-296 FireInvocation-of-mechanical-recurrence branch dissolved
    when FireInvocation left the Reviewer's tool surface.

    `client` and `user_id` arguments retained for signature stability
    across feed.py call sites; reserved for future re-introduction of
    recurrence-dependent classification logic.
    """
    del client, user_id  # currently unused; reserved
    return action.get("tool", "") in REVIEWER_MIRROR_REFRESH_TOOLS


def narrate_reviewer_action(tool: str, summary: str = "") -> str:
    """Compose a System Agent narration line for a Reviewer-directed action.

    The narration is honest: it names the tool, attributes the direction to
    the Reviewer, and includes the action summary if available. Used by all
    four trigger paths so the chat conversation reads consistently regardless
    of which trigger fired the Reviewer.
    """
    summary_part = f" {summary}" if summary else ""
    # ADR-296 v2 D3: FireInvocation case removed — Reviewer no longer
    # commissions unit-of-work fires; cadence is authored via Schedule.
    if tool == "ProposeAction":
        return f"Proposal submitted on Reviewer's direction.{summary_part}"
    if tool == "WriteFile":
        return f"Wrote to Reviewer substrate on its direction.{summary_part}"
    return f"Executed `{tool}` on Reviewer's direction.{summary_part}"


async def surface_reviewer_actions(
    client: Any,
    user_id: str,
    *,
    actions_taken: list,
) -> int:
    """Best-effort: surface each consequential successful Reviewer action as
    a System Agent narrative entry to the operator's active workspace session.

    Used by triggers that don't have a live SSE stream (heartbeat, proposal,
    reflection). The addressed trigger uses chat.py's per-event narration
    instead so the operator sees actions in real time.

    Returns the number of narration entries written. Never raises.
    """
    if not user_id or not actions_taken:
        return 0

    from services.narrative import find_active_workspace_session, write_narrative_entry

    session_id = find_active_workspace_session(client, user_id)
    if not session_id:
        return 0

    written = 0
    for action in actions_taken:
        if not isinstance(action, dict):
            continue
        if not action.get("success", True):
            continue
        tool = action.get("tool", "?")
        if tool in REVIEWER_COGNITION_TOOLS:
            continue
        # ADR-289 Phase 2a + ADR-296 v2 D3: mirror-refresh actions
        # (SyncPlatformState — the Reviewer's mid-loop substrate refresh
        # override case per ADR-264) carry no operator-relevant judgment —
        # substrate-canonicalization plumbing. Extends ADR-277's emission-
        # at-source policy. The pre-ADR-296 FireInvocation-of-mechanical
        # branch dissolved when FireInvocation left REVIEWER_PRIMITIVES.
        if is_mirror_refresh_action(action, client, user_id):
            continue
        summary = action.get("summary", "")
        body = narrate_reviewer_action(tool, summary)
        # Audit-pass-2 DD-4: when the action is ProposeAction, embed
        # the proposal_id in extra_metadata so the FE renders an inline
        # ProposalCard chip on this narration entry instead of plain
        # text. Closes the supervisory mental-thread gap (heartbeat /
        # reflection / cron-fired proposals previously had no clickable
        # affordance on the feed; operator had to navigate to cockpit
        # to find them).
        meta: dict = {
            "tools_used": [tool],
            "reviewer_directed": True,
        }
        proposal_id = action.get("proposal_id")
        if tool == "ProposeAction" and proposal_id:
            meta["proposal_id"] = proposal_id
        # ADR-289 D5: read invocation_id off the action record (Reviewer
        # stamps it on every action_record per ADR-289 D4) and pass through
        # to the narrative envelope. FE groups rows sharing invocation_id
        # into one invocation card on the Feed surface.
        action_invocation_id = action.get("invocation_id")
        try:
            # weight=material — System Agent is a participant in the
            # conversation, full chat-bubble visual weight.
            write_narrative_entry(
                client,
                session_id,
                role="system_agent",
                summary=body[:200],
                body=body,
                pulse="reactive",
                weight="material",
                invocation_id=action_invocation_id,
                extra_metadata=meta,
            )
            written += 1
        except Exception as exc:
            logger.warning(
                "[REVIEWER_CHAT] action narration failed for tool=%s: %s",
                tool, exc,
            )
    return written
