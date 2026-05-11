"""Reviewer Audit Trail — appends decisions to /workspace/review/decisions.md
(ADR-194 v2 Phase 2a).

Every approve / reject that flows through ExecuteProposal / RejectProposal
calls `append_decision` here. The entry format is YAML-frontmatter-like
delimited blocks so parsers (future AI Reviewer calibration loop,
ADR-194 Phase 4) can round-trip the log cheaply.

Per FOUNDATIONS v6.0 Axiom 1 (Substrate), decisions.md IS the audit trail. Narrow
metadata on action_proposals (reviewer_identity / reviewer_reasoning) is
for UX only — the full record is the filesystem append.

File convention:
  /workspace/review/decisions.md

Append semantics:
- First write creates the file with a header.
- Subsequent writes append a new `--- decision ---` block.
- Newest entries appear last (chronological append), same pattern as
  other append-only logs in YARNNN (e.g., _tracker.md per ADR-158 is
  regenerated, but append-only logs like contribution briefs + the
  soon-to-exist decisions.md append forward).

Entry format:
  --- decision ---
  timestamp: 2026-04-19T10:15:03+00:00
  proposal_id: <uuid>
  action_type: trading.submit_order
  decision: approve  | reject  | defer
  reviewer_identity: human:<user_id>  |  ai:<slug>  |  impersonated:<...>
  reversibility: reversible
  outcome: executed | rejected_at_execution | expired
  ---
  <free-form reasoning from the Reviewer, markdown-allowed>

Recurrence-fire entry (added 2026-05-11 per FOUNDATIONS v8.4 Axiom 1
fourth sub-clause — substrate is the bus the Loop runs over). When a
`judgment`-mode recurrence fires (cron or nested FireInvocation),
the resulting Reviewer output is persisted here so a later Reviewer
read-from-substrate can recover what was decided. Without this,
nested-Reviewer reasoning would live only in the dispatcher's tool-
result dict (substrate-as-bus violation):

  --- recurrence-fire ---
  timestamp: 2026-05-11T07:00:00+00:00
  slug: morning-reflection
  trigger: reactive
  reviewer_identity: ai:reviewer-haiku-v1  |  reviewer:simons  |  ...
  duration_ms: 4321
  actions_count: 2
  proposals_count: 1
  ---
  <free-form Reviewer verdict + evidence_summary, markdown-allowed>
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)


#: Canonical filesystem home for the Reviewer's audit trail.
DECISIONS_PATH = "/workspace/review/decisions.md"


Decision = Literal["approve", "reject", "defer"]


async def append_decision(
    client: Any,
    user_id: str,
    *,
    proposal_id: str,
    action_type: str,
    decision: Decision,
    reviewer_identity: str,
    reasoning: str = "",
    reversibility: str | None = None,
    outcome: str | None = None,
) -> bool:
    """Append a decision entry to /workspace/review/decisions.md.

    Creates the file (with a header) on first write. Appends a delimited
    block on subsequent writes. Never raises — audit trail failures must
    not block approval/rejection. Returns True on success.
    """
    try:
        block = _render_entry(
            proposal_id=proposal_id,
            action_type=action_type,
            decision=decision,
            reviewer_identity=reviewer_identity,
            reasoning=reasoning,
            reversibility=reversibility,
            outcome=outcome,
        )

        # Read existing content (if any)
        existing = _read_sync(client, user_id)

        if existing is None:
            # First write — seed with header
            content = _HEADER + "\n\n" + block
        else:
            # Append with a blank-line separator for readability
            content = existing.rstrip() + "\n\n" + block

        ok = _write_sync(
            client,
            user_id,
            content,
            reviewer_identity=reviewer_identity,
            proposal_id=proposal_id,
            decision=decision,
        )
        if not ok:
            logger.warning(
                "[REVIEWER_AUDIT] upsert failed for user=%s proposal=%s",
                user_id[:8],
                proposal_id[:8] if proposal_id else "?",
            )
        return ok
    except Exception as exc:  # noqa: BLE001 — audit trail must never break flow
        logger.warning(
            "[REVIEWER_AUDIT] append_decision failed for user=%s proposal=%s: %s",
            user_id[:8],
            proposal_id[:8] if proposal_id else "?",
            exc,
        )
        return False


async def append_recurrence_fire(
    client: Any,
    user_id: str,
    *,
    slug: str,
    trigger: str,
    reviewer_identity: str,
    reasoning: str = "",
    duration_ms: int | None = None,
    actions_count: int = 0,
    proposals_count: int = 0,
) -> bool:
    """Append a recurrence-fire entry to /workspace/review/decisions.md.

    Per FOUNDATIONS v8.4 Axiom 1 fourth sub-clause (substrate is the bus
    the runtime Loop runs over): when a `judgment`-mode recurrence fires
    via the dispatcher (whether cron-triggered or nested via FireInvocation
    from another Reviewer turn), the resulting Reviewer output must land
    on substrate. Otherwise the Reviewer's reasoning lives only in the
    dispatcher's tool-result dict — a parallel control-flow channel that
    violates the substrate-as-bus invariant.

    Same substrate file as proposal-arrival decisions (singular implementation
    — one decisions.md, two entry kinds). Distinct entry header
    (`--- recurrence-fire ---`) preserves parser-level differentiation.

    Never raises — audit trail failures must not block the dispatcher.
    Returns True on successful substrate write.
    """
    try:
        block = _render_recurrence_fire_entry(
            slug=slug,
            trigger=trigger,
            reviewer_identity=reviewer_identity,
            reasoning=reasoning,
            duration_ms=duration_ms,
            actions_count=actions_count,
            proposals_count=proposals_count,
        )

        existing = _read_sync(client, user_id)
        if existing is None:
            content = _HEADER + "\n\n" + block
        else:
            content = existing.rstrip() + "\n\n" + block

        ok = _write_recurrence_fire_sync(
            client,
            user_id,
            content,
            reviewer_identity=reviewer_identity,
            slug=slug,
            trigger=trigger,
        )
        if not ok:
            logger.warning(
                "[REVIEWER_AUDIT] recurrence-fire upsert failed for user=%s slug=%s",
                user_id[:8],
                slug,
            )
        return ok
    except Exception as exc:  # noqa: BLE001 — audit trail must never break flow
        logger.warning(
            "[REVIEWER_AUDIT] append_recurrence_fire failed for user=%s slug=%s: %s",
            user_id[:8],
            slug,
            exc,
        )
        return False


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


_HEADER = """\
# Review — Decisions Log

Append-only log of every review decision made in this workspace. Newest
entries at the bottom. Each entry is a `--- decision ---` block with
machine-readable fields followed by the Reviewer's reasoning.

Written by the Reviewer layer (ADR-194 v2). See `/workspace/review/IDENTITY.md`
for the Reviewer's identity and `/workspace/review/principles.md` for the
declared review framework.
"""


def _render_entry(
    *,
    proposal_id: str,
    action_type: str,
    decision: Decision,
    reviewer_identity: str,
    reasoning: str,
    reversibility: str | None,
    outcome: str | None,
) -> str:
    """Render a single decision block."""
    ts = datetime.now(timezone.utc).isoformat()
    lines = [
        "--- decision ---",
        f"timestamp: {ts}",
        f"proposal_id: {proposal_id}",
        f"action_type: {action_type}",
        f"decision: {decision}",
        f"reviewer_identity: {reviewer_identity}",
    ]
    if reversibility:
        lines.append(f"reversibility: {reversibility}")
    if outcome:
        lines.append(f"outcome: {outcome}")
    lines.append("---")
    if reasoning.strip():
        lines.append(reasoning.strip())
    else:
        lines.append("_(no reasoning supplied)_")
    return "\n".join(lines)


def _render_recurrence_fire_entry(
    *,
    slug: str,
    trigger: str,
    reviewer_identity: str,
    reasoning: str,
    duration_ms: int | None,
    actions_count: int,
    proposals_count: int,
) -> str:
    """Render a single recurrence-fire block."""
    ts = datetime.now(timezone.utc).isoformat()
    lines = [
        "--- recurrence-fire ---",
        f"timestamp: {ts}",
        f"slug: {slug}",
        f"trigger: {trigger}",
        f"reviewer_identity: {reviewer_identity}",
    ]
    if duration_ms is not None:
        lines.append(f"duration_ms: {duration_ms}")
    lines.append(f"actions_count: {actions_count}")
    lines.append(f"proposals_count: {proposals_count}")
    lines.append("---")
    if reasoning.strip():
        lines.append(reasoning.strip())
    else:
        lines.append("_(no verdict reasoning supplied)_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# filesystem I/O (direct workspace_files access — same pattern as risk_gate)
# ---------------------------------------------------------------------------


def _read_sync(client: Any, user_id: str) -> str | None:
    """Return current decisions.md content or None if absent."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", DECISIONS_PATH)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_AUDIT] read failed for user=%s: %s", user_id[:8], exc,
        )
        return None
    rows = result.data or []
    if not rows:
        return None
    return rows[0].get("content") or ""


def _write_sync(
    client: Any,
    user_id: str,
    content: str,
    *,
    reviewer_identity: str,
    proposal_id: str,
    decision: str,
) -> bool:
    """Write decisions.md through the Authored Substrate (ADR-209).

    authored_by carries the reviewer identity: `reviewer:<identity>`.
    This preserves structural author attribution in the revision chain
    while the in-file block retains reasoning + full decision context.
    The revision-chain author becomes the machine-indexable source of
    "who decided what" — the in-file block is the human-readable
    reasoning accompanying it.
    """
    try:
        from services.authored_substrate import write_revision

        write_revision(
            client,
            user_id=user_id,
            path=DECISIONS_PATH,
            content=content,
            authored_by=f"reviewer:{reviewer_identity}",
            message=f"{decision} proposal {proposal_id[:8] if proposal_id else '?'}",
            summary="Reviewer decisions log",
            tags=["_decisions", "review", "audit"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_AUDIT] write failed for user=%s: %s", user_id[:8], exc,
        )
        return False


def _write_recurrence_fire_sync(
    client: Any,
    user_id: str,
    content: str,
    *,
    reviewer_identity: str,
    slug: str,
    trigger: str,
) -> bool:
    """Write decisions.md through the Authored Substrate (ADR-209) for a
    recurrence-fire entry. Same substrate path as decisions, distinct
    revision message identifying the entry kind.
    """
    try:
        from services.authored_substrate import write_revision

        write_revision(
            client,
            user_id=user_id,
            path=DECISIONS_PATH,
            content=content,
            authored_by=f"reviewer:{reviewer_identity}",
            message=f"recurrence-fire {slug} ({trigger})",
            summary="Reviewer decisions log",
            tags=["_decisions", "review", "audit", "recurrence-fire"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_AUDIT] recurrence-fire write failed for user=%s: %s",
            user_id[:8],
            exc,
        )
        return False
