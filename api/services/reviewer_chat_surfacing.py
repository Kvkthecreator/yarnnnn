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

# 2026-05-25: Clarify removed per docs/evaluations/2026-05-25-042827-
# clarify-silenced-from-feed/findings.md. Clarify is the structural
# opposite of cognition — its sole purpose is operator-facing
# communication with a side effect (operator's attention). ADR-247
# line 139 classifies it as "Ask operator for input." ADR-289's 3-bucket
# taxonomy comment never named Clarify; it was misclassified by the
# original frozenset construction. The fix surfaces Clarify with
# role='reviewer' (persona attribution, not System Agent narration);
# see narrate_reviewer_action's Clarify branch + the role-aware emission
# path in surface_reviewer_actions + wake.py::stream_addressed_wake.
REVIEWER_COGNITION_TOOLS = frozenset({
    "ReadFile", "ListFiles", "SearchFiles", "ListRevisions",
    "ReadRevision", "DiffRevisions", "GetSystemState", "SearchEntities",
    "LookupEntity", "list_integrations", "WebSearch", "QueryKnowledge",
    "DiscoverAgents", "ReadAgentFile", "ListEntities",
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


# ADR-303 D3 (2026-05-26) — visibility-first failure-surfacing invert.
#
# Pre-this commit, ALL failed Reviewer actions were filtered out of
# narrative substrate (the unguarded `success=True` gate at
# surface_reviewer_actions:408 + _fold_key:307). The operator could not
# see the model's failed-WriteFile attempts, failed ProposeAction
# submissions, failed substrate refreshes — even though those failures
# carry operator-actionable information (e.g., "model attempted write
# to locked path; consider relaxing the lock").
#
# ADR-303 D3 inverts: visibility-first default; explicit denylist for
# known transient noise. Surfaces a `reviewer_action_blocked` narrative
# entry (new event-kind) for failed actions whose failure_reason is
# operator-relevant. The denylist is intentionally narrow — operator-
# relevant failure reasons NEVER enter the denylist by design.
#
# Aligned with Claude Code's first-principles position
# (docs/analysis/src_claudeCC/query.ts:140 — every tool failure surfaces
# with is_error: true, no allowlist filter). See
# docs/analysis/claude-code-prompt-discipline-comparison-2026-05-26.md §4.
SILENCE_FAILURE_REASONS: frozenset[str] = frozenset({
    # Transient infrastructure noise; not operator-actionable.
    "rate_limited",
    "transient_network",
    # Self-superseded — a same-tool same-args success followed in cycle.
    # Currently no upstream code stamps this reason; reserved for the
    # _fold_same_path_writes pass to identify when implemented (separate
    # commit). Listed here for completeness of the denylist contract.
    "retried_successfully_in_cycle",
})


def should_surface_failed_action(action: dict) -> bool:
    """ADR-303 D3 visibility-first default. Returns True if the failed
    action carries operator-actionable information that should reach
    the feed. Returns False ONLY for explicit known-noise failure
    reasons. Unknown reasons default to True (visibility-first)."""
    if not isinstance(action, dict):
        return False
    reason = (action.get("failure_reason") or "").strip()
    if not reason:
        # No failure reason captured — default to surface (visibility-first).
        # The narrative entry will explain the action failed without a
        # specific reason; operator can decide if it warrants follow-up.
        return True
    return reason not in SILENCE_FAILURE_REASONS


def narrate_reviewer_action_blocked(
    tool: str,
    summary: str = "",
    *,
    failure_reason: Optional[str] = None,
    inp: Optional[dict] = None,
) -> str:
    """Compose a System Agent narration line for a FAILED Reviewer action.

    ADR-303 D3 + D6: dispatcher-attributed `reviewer_action_blocked`
    event. Honest narration: names the tool, names the failure reason if
    captured, includes the path/target if extractable from input. The
    operator reads this and decides whether to relax a lock, fix a
    schema mismatch, connect a capability, etc.
    """
    # ADR-365 (register follows consumer): operator-facing — plain English.
    # The reason is kept (the operator may need it to act — e.g. unlock a
    # file), but the machine framing ("attempted X target=… blocked") is not.
    reason_part = f" — {failure_reason}" if failure_reason else ""
    summary_part = f" ({summary})" if summary else ""
    # Extract path/target from input if useful — common across WriteFile,
    # ReadFile, Schedule, ProposeAction (each has different input shape).
    target_part = ""
    if isinstance(inp, dict):
        for key in ("path", "slug", "target", "to", "name"):
            val = inp.get(key)
            if isinstance(val, str) and val:
                target_part = f" ({val})"
                break
    return (
        f"Couldn't complete an action{target_part}"
        f"{reason_part}.{summary_part}"
    )


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


def narrate_reviewer_action(tool: str, summary: str = "", *, folded_count: int = 1) -> str:
    """Compose a System Agent narration line for a Reviewer-directed action.

    The narration is honest: it names the tool, attributes the direction to
    the Reviewer, and includes the action summary if available. Used by all
    four trigger paths so the chat conversation reads consistently regardless
    of which trigger fired the Reviewer.

    folded_count > 1 indicates the action represents N consecutive same-path
    same-tool writes folded into one narration line (closes Pattern 2 of
    docs/evaluations/2026-05-21-005856-wake-duplication-audit/). Substrate
    retains every revision per ADR-209; only the feed-surface noise is
    collapsed.
    """
    # ADR-365 (register follows consumer): these lines are operator-facing —
    # plain English, no internal vocabulary ("substrate", "on its direction").
    summary_part = f" {summary}" if summary else ""
    count_part = f" ({folded_count} updates)" if folded_count > 1 else ""
    # ADR-296 v2 D3: FireInvocation case removed — Reviewer no longer
    # commissions unit-of-work fires; cadence is authored via Schedule.
    if tool == "ProposeAction":
        return f"Submitted a proposal for review.{summary_part}{count_part}"
    if tool == "WriteFile":
        return f"Saved a working note.{summary_part}{count_part}"
    # 2026-05-25 Clarify branch: the Reviewer IS the asker. Render the
    # question bare (no "Executed Clarify..." prefix). Caller writes the
    # row with role='reviewer' so the FE renders it in the Reviewer
    # persona bubble (ADR-247 three-party model + ADR-258 D1).
    if tool == "Clarify":
        return summary or "Asked you a question."
    return f"Took an action ({tool}).{summary_part}{count_part}"


def _fold_same_path_writes(
    actions_taken: list,
    client: Any,
    user_id: str,
) -> list:
    """Fold consecutive emit-eligible actions sharing (tool, path) into one.

    "Emit-eligible" = the subset that would have produced narration entries
    (excludes REVIEWER_COGNITION_TOOLS + REVIEWER_MIRROR_REFRESH_TOOLS,
    failed actions). The fold operates on the emit-eligible sequence —
    cognition + mirror-refresh actions are transparently skipped and do
    NOT break adjacency for fold purposes.

    Returns a NEW list in original order with consecutive same-(tool, path)
    runs collapsed. The LAST action in each run is retained (representing
    final substrate state); intermediate actions are dropped. Each surviving
    action carries `_folded_count` indicating the run length (1 = no fold).

    Path extraction: action["input"]["path"] for the tools we narrate
    (WriteFile, ManageTask, etc. all carry path; Schedule's path is
    `/workspace/_recurrences.yaml` derived from the slug, but Schedule's
    fold scope is governed by slug rather than path — handled in Commit C).

    Used by surface_reviewer_actions to close the iterative-refinement
    feed-noise pattern surfaced by docs/evaluations/2026-05-21-005856-
    wake-duplication-audit/findings.md.
    """
    if not actions_taken:
        return []

    folded: list = []

    # Helper: extract the fold key for an action. Same-key consecutive runs
    # collapse. Returns None for actions that should never be folded
    # (cognition, mirror-refresh, missing path, OR failed actions filtered
    # by ADR-303 D3 denylist).
    #
    # ADR-303 D3 (2026-05-26): failed actions can also fold (consecutive
    # same-path same-tool failures collapse into one narration line) but
    # the fold key carries a "failed" discriminator so a success-then-
    # failure sequence doesn't merge. Failures filtered by the denylist
    # (SILENCE_FAILURE_REASONS) return None — no narration, no folding.
    def _fold_key(action: Any) -> Optional[tuple]:
        if not isinstance(action, dict):
            return None
        success = action.get("success", True)
        if not success and not should_surface_failed_action(action):
            return None  # denylisted-noise failure — silenced
        tool = action.get("tool", "")
        if tool in REVIEWER_COGNITION_TOOLS:
            return None
        if is_mirror_refresh_action(action, client, user_id):
            return None
        # Only fold tools whose summary collapses to identical text when
        # path is the only discriminator. WriteFile is the canonical case.
        # Schedule has a slug discriminator; folding by path would mask
        # distinct recurrences. ProposeAction never folds.
        if tool != "WriteFile":
            return None
        inp = action.get("input") or {}
        if not isinstance(inp, dict):
            return None
        path = inp.get("path")
        if not path:
            return None
        # Discriminate success vs failure folds so the operator sees
        # "Wrote 5 revisions to X" and "Reviewer attempted X but blocked"
        # as separate narration lines, not merged.
        return (tool, path, "success" if success else "failed")

    for action in actions_taken:
        key = _fold_key(action)
        # Look at the previous folded entry to check fold eligibility.
        # We fold strictly when the previous emit-eligible entry shares
        # the same key. Cognition/mirror-refresh actions in actions_taken
        # don't reach `folded` (they're filtered downstream in
        # surface_reviewer_actions) so adjacency in `folded` matches
        # adjacency among emit-eligible actions.
        if (
            key is not None
            and folded
            and isinstance(folded[-1], dict)
            and _fold_key(folded[-1]) == key
        ):
            # Same-key run continues — replace the prior entry with this one
            # (preserve final state) + bump the count.
            prior_count = folded[-1].get("_folded_count", 1)
            # Shallow copy so we don't mutate the caller's action dict.
            merged = dict(action)
            merged["_folded_count"] = prior_count + 1
            folded[-1] = merged
        else:
            # New key or non-foldable action — append as-is. Ensure
            # _folded_count is set to 1 for foldable actions so the
            # narration template can read it uniformly.
            if key is not None:
                action = dict(action)
                action["_folded_count"] = 1
            folded.append(action)

    return folded


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

    # Pre-fold: collapse consecutive emit-eligible actions that share
    # (tool, path) into a single representative action with a count.
    # Closes Pattern 2 of docs/evaluations/2026-05-21-005856-wake-
    # duplication-audit/findings.md — the Reviewer's tool-use loop
    # iterates on the same file across multiple rounds (legitimate LLM
    # refinement behavior), but the per-write narration emits one feed
    # line per revision, producing visual duplication. Substrate is
    # honest (ADR-209 retains every revision); the feed surfaces
    # judgment not every keystroke.
    #
    # Fold scope: strictly consecutive among the emit-eligible subset
    # (cognition + mirror-refresh actions are silenced first and don't
    # break adjacency). The fold preserves the LAST action's invocation_id
    # + summary (the final substrate state) and exposes the fold count
    # via `_folded_count` on the action dict so the narration template
    # can render "Wrote N revisions to ..." instead of N separate lines.
    folded_actions = _fold_same_path_writes(actions_taken, client, user_id)

    written = 0
    for action in folded_actions:
        if not isinstance(action, dict):
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
        # ADR-303 D3 (2026-05-26) visibility-first invert: failed actions
        # surface UNLESS the failure_reason is in SILENCE_FAILURE_REASONS
        # (known transient noise). The prior `success=True` filter was the
        # success-bias that hid operator-relevant constraint hits like
        # WriteFile-refused-by-lock — see
        # docs/evaluations/2026-05-26-152500-failed-action-substrate-blindspot/
        # §Finding-1. Aligned with Claude Code's tool_result is_error
        # always-surface pattern (query.ts:140).
        success = action.get("success", True)
        if not success and not should_surface_failed_action(action):
            continue  # denylisted-noise failure — silenced
        summary = action.get("summary", "")
        folded_count = action.get("_folded_count", 1)
        # Dispatch to success-narration or blocked-narration based on
        # action outcome. Blocked narration carries failure_reason + the
        # action input so the operator can see what was attempted and why
        # it was refused (operator-actionable diagnostic).
        if success:
            body = narrate_reviewer_action(tool, summary, folded_count=folded_count)
        else:
            body = narrate_reviewer_action_blocked(
                tool,
                summary,
                failure_reason=action.get("failure_reason"),
                inp=action.get("input"),
            )
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
        # ADR-303 D3 (2026-05-26): event-kind metadata for failed actions
        # so the FE can render a distinct visual treatment for blocked
        # actions (warning-shaped, not action-shaped). `event_kind` is
        # also the canonical hook for future operator-side filtering
        # (e.g., a "show me only blocked actions" cockpit filter).
        if not success:
            meta["event_kind"] = "reviewer_action_blocked"
            failure_reason = action.get("failure_reason")
            if failure_reason:
                meta["failure_reason"] = failure_reason
        proposal_id = action.get("proposal_id")
        if tool == "ProposeAction" and proposal_id:
            meta["proposal_id"] = proposal_id
        # 2026-05-25 (clarify-silenced-from-feed): per-tool role +
        # extra_metadata for Clarify. The Reviewer IS the asker — the row
        # belongs in the Reviewer persona bubble (role='reviewer' per
        # ADR-247 + ADR-258 D1), not System Agent narration. Structured
        # question + options stamped on metadata so a future FE
        # response-affordance can render inline buttons without re-parsing
        # the body text.
        # ADR-352: only a Clarify the ask-gate ALLOWED (success) surfaces a
        # question + options to the operator. A DENIED Clarify (autonomous, no
        # structural_gap) must NOT leak its enumerated question as if it had
        # been asked — it renders as a blocked action (narrate_reviewer_action_
        # blocked above) and the seat acts instead. Without this guard the
        # operator sees an A/B question the gate actually refused.
        if tool == "Clarify" and success:
            row_role = "reviewer"
            clarify_input = action.get("input") or {}
            if isinstance(clarify_input, dict):
                cq = clarify_input.get("question")
                co = clarify_input.get("options")
                if cq:
                    meta["clarify_question"] = cq
                if isinstance(co, list) and co:
                    meta["clarify_options"] = list(co)
        else:
            row_role = "system_agent"
        # ADR-289 D5: read invocation_id off the action record (Reviewer
        # stamps it on every action_record per ADR-289 D4) and pass through
        # to the narrative envelope. FE groups rows sharing invocation_id
        # into one invocation card on the Feed surface.
        action_invocation_id = action.get("invocation_id")
        try:
            # weight=material — both System Agent narration and Reviewer
            # Clarify questions are full chat-bubble visual weight.
            write_narrative_entry(
                client,
                session_id,
                role=row_role,
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
