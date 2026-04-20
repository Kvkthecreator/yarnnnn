"""Review Proposal Dispatch — ADR-194 v2 Phase 2b.

Reactive handler for proposal creation events. Fires from
`handle_propose_action` after `action_proposals` row insert, before the
handler returns. Per FOUNDATIONS v6.0 Axiom 4 (Trigger — reactive
sub-shape), this is an event handler, not a scheduled task.

**Current scope (Phase 2b): seat-defer observation.**
The Reviewer seat defers to human for every new proposal. The dispatcher
writes an observation entry to `/workspace/review/decisions.md` noting:
  - A proposal was created
  - The Reviewer layer observes it
  - The seat defers to human (existing ProposalCard UX)

This gives the audit trail a "proposal observed" event that predates
the approve/reject entry, and gives the human operator a legible
Stream surface (ADR-198 archetype) of Reviewer activity even when no
AI reasoning has run.

**Phase 3 extension (not in scope here):**
Phase 3 replaces the seat-defer observation with an AI Reviewer agent
invocation. The AI reads `/workspace/review/principles.md`, the
proposal's context domains, and `_performance.md` to reason in
capital-EV terms. When the decision is auto-approve or auto-reject
under declared thresholds, the dispatcher calls
`handle_execute_proposal` or `handle_reject_proposal` with
`reviewer_identity="ai:<slug>"`. When the decision is defer, the seat
falls through to human (current Phase 2b behavior).

**Never raises.** Dispatch failures degrade gracefully — the proposal
remains pending, the operator can still act via ProposalCard.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from services.reviewer_audit import append_decision

logger = logging.getLogger(__name__)


#: Reviewer identity used when the seat defers to human review.
#: The format namespace is `reviewer-layer:<event>` — distinct from the
#: approve/reject identities (`human:<user_id>` / `ai:<slug>`) so a
#: log reader can tell "this is the layer observing" vs "this is a
#: filled seat deciding."
_REVIEWER_OBSERVATION_IDENTITY = "reviewer-layer:observed"


async def on_proposal_created(
    client: Any,
    user_id: str,
    proposal_id: str,
    proposal_row: dict,
) -> None:
    """Handle the reactive event of a new proposal being created.

    Args:
        client: Supabase client (service or user — either works for
            the filesystem append since user RLS allows
            workspace_files upsert on own paths).
        user_id: The proposal's owning user.
        proposal_id: UUID of the newly created proposal.
        proposal_row: The row dict as returned from the INSERT (for
            action_type, reversibility, etc — avoids a re-SELECT).

    Returns None. Never raises — dispatch failure is logged.
    """
    try:
        action_type = proposal_row.get("action_type") or "unknown"
        reversibility = proposal_row.get("reversibility")
        expires_at = proposal_row.get("expires_at")
        rationale = (proposal_row.get("rationale") or "").strip()

        # Phase 2b: seat defers to human. Reasoning captures the
        # proposal's declared rationale + what the Reviewer *would*
        # need to reason in EV terms when Phase 3 ships.
        reasoning_lines = [
            "Reviewer layer observed proposal creation.",
            f"Seat defers to human (Phase 2b — AI Reviewer not yet active).",
            "",
        ]
        if rationale:
            reasoning_lines.append(f"Proposal rationale (from YARNNN / caller):")
            reasoning_lines.append(f"> {rationale}")
            reasoning_lines.append("")
        if expires_at:
            reasoning_lines.append(f"Proposal expires: {expires_at}")

        ok = await append_decision(
            client, user_id,
            proposal_id=proposal_id,
            action_type=action_type,
            decision="defer",
            reviewer_identity=_REVIEWER_OBSERVATION_IDENTITY,
            reasoning="\n".join(reasoning_lines),
            reversibility=reversibility,
            outcome="pending_human",
        )
        if ok:
            logger.info(
                "[REVIEW_DISPATCH] observed proposal=%s user=%s action=%s — "
                "seat defers to human",
                proposal_id[:8],
                user_id[:8],
                action_type,
            )
        else:
            logger.warning(
                "[REVIEW_DISPATCH] append_decision returned False for proposal=%s user=%s",
                proposal_id[:8],
                user_id[:8],
            )
    except Exception as exc:  # noqa: BLE001 — must not block proposal creation
        logger.warning(
            "[REVIEW_DISPATCH] on_proposal_created failed for proposal=%s user=%s: %s",
            proposal_id[:8] if proposal_id else "?",
            user_id[:8] if user_id else "?",
            exc,
        )
