"""Reviewer Audit Trail — appends decisions to /workspace/review/decisions.md
(ADR-194 v2 Phase 2a).

Every approve / reject that flows through ExecuteProposal / RejectProposal
calls `append_decision` here. The entry format is YAML-frontmatter-like
delimited blocks so parsers (future AI Reviewer calibration loop,
ADR-194 Phase 4) can round-trip the log cheaply.

Per FOUNDATIONS v5.1 Axiom 0, decisions.md IS the audit trail. Narrow
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

        ok = _write_sync(client, user_id, content)
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


def _write_sync(client: Any, user_id: str, content: str) -> bool:
    """Upsert decisions.md content."""
    try:
        client.table("workspace_files").upsert(
            {
                "user_id": user_id,
                "path": DECISIONS_PATH,
                "content": content,
                "content_type": "text/markdown",
                "lifecycle": "active",
                "summary": "Reviewer decisions log",
                "tags": ["_decisions", "review", "audit"],
            },
            on_conflict="user_id,path",
        ).execute()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_AUDIT] write failed for user=%s: %s", user_id[:8], exc,
        )
        return False
