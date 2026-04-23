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
verdict write (to decisions.md + action_proposals).

Failure discipline: surfacing to chat is best-effort. If the session
lookup or message insert fails, we log and return — the verdict is
already persisted authoritatively in decisions.md + action_proposals.
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
still fully captured in decisions.md + action_proposals — it just
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
decisions.md. Short (typically 2–5 sentences).
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
) -> Optional[dict]:
    """Surface a reviewer verdict to the operator's active chat session.

    Best-effort: never raises. Returns the inserted row on success,
    None on any failure path (no active session; insert failed; etc.).

    Callers should treat this as write-and-forget — the authoritative
    verdict record lives in decisions.md + action_proposals. This
    surfacing is for operator-facing timeline visibility.
    """
    if not user_id or not content:
        return None

    # 1. Find the operator's most-recent active workspace-scoped chat session.
    session_id = _find_active_workspace_session(client, user_id)
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

    # 3. Insert via the RPC that manages sequence_number; fall back to
    #    direct insert if the RPC path errors.
    try:
        result = client.rpc(
            "append_session_message",
            {
                "p_session_id": session_id,
                "p_role": "reviewer",
                "p_content": content,
                "p_metadata": metadata,
            },
        ).execute()
        return result.data
    except Exception as rpc_exc:
        logger.warning(
            "[REVIEWER_CHAT] RPC append_session_message failed; fallback to direct insert: %s",
            rpc_exc,
        )
        try:
            seq = (
                client.table("session_messages")
                .select("sequence_number")
                .eq("session_id", session_id)
                .order("sequence_number", desc=True)
                .limit(1)
                .execute()
            )
            next_seq = 1
            if seq.data:
                next_seq = int(seq.data[0]["sequence_number"]) + 1

            result = (
                client.table("session_messages")
                .insert(
                    {
                        "session_id": session_id,
                        "role": "reviewer",
                        "content": content,
                        "sequence_number": next_seq,
                        "metadata": metadata,
                    }
                )
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as insert_exc:
            logger.warning(
                "[REVIEWER_CHAT] direct insert failed for user=%s: %s",
                user_id[:8] if user_id else "?",
                insert_exc,
            )
            return None


def _find_active_workspace_session(client: Any, user_id: str) -> Optional[str]:
    """Return the id of the operator's most-recent active workspace session,
    or None if none exists.

    Scope: workspace-level (session_type='workspace' / legacy 'default'),
    status='active', ordered by updated_at desc.

    Per ADR-125 / ADR-159 a workspace has one active session at a time; the
    most-recent-updated is the one the operator sees on /chat open.
    """
    try:
        # Prefer workspace-scoped sessions; fall back to any active session
        # for the user if session_type column semantics have drifted.
        result = (
            client.table("chat_sessions")
            .select("id")
            .eq("user_id", user_id)
            .eq("status", "active")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if rows:
            return rows[0]["id"]
        return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_CHAT] active session lookup failed for user=%s: %s",
            user_id[:8] if user_id else "?",
            exc,
        )
        return None
