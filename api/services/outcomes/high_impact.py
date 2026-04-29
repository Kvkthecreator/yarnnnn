"""High-Impact Outcome Actuation — ADR-195 v2 Phase 5.

Reconciled outcomes whose magnitude crosses an operator-declared
threshold are surfaced as feedback entries on the originating task's
`feedback.md`. This closes the money-truth → future-behavior loop
per FOUNDATIONS v6.0 Axiom 7 (Recursion): accumulated capital outcomes
feed the next agent execution cycle.

Per ADR-181 (Source-Agnostic Feedback Layer), feedback entries from
system sources carry a `source: system_outcome` tag. Tier 1 (injection)
reads the last N entries into generation prompts; Tier 2 (actuation)
can match entries against `FEEDBACK_ACTUATION_RULES` if a rule exists
for the outcome pattern. Phase 5 is purely a producer — it writes
entries. Whether they actuate entity mutations depends on operator-
declared rules in a future extension.

**Threshold discipline:** the operator declares thresholds in
`/workspace/review/principles.md` under a `high_impact` key per domain.
Default: no threshold → no high-impact entries written (safe default).

**Task resolution:** every outcome with a `proposal_id` can be traced
to its originating `action_proposals.task_slug`. Outcomes without a
proposal_id (direct agent writes — rare today since platform tools
go through the approval loop) are skipped — they have no task home
for a feedback entry.

**Never raises.** Writing feedback entries must not block outcome
reconciliation. Failures log.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from services.outcomes.base import OutcomeCandidate, OutcomeProvider

logger = logging.getLogger(__name__)


#: Key under which per-domain high-impact thresholds live in principles.md.
#: Shape: `high_impact: { <domain>: { threshold_cents: <int> } }` — but we
#: accept a flatter form `<domain>: { high_impact_threshold_cents: <int> }`
#: since the principles parser handles line-based top-level-domain entries.
_HIGH_IMPACT_KEY = "high_impact_threshold_cents"


def detect_high_impact_candidates(
    candidates: list[OutcomeCandidate],
    thresholds_by_domain: dict[str, int],
) -> list[OutcomeCandidate]:
    """Return the subset of candidates whose abs(value_cents) crosses
    the operator-declared threshold for their context_domain.

    Candidates with None value_cents are never high-impact. Candidates
    from domains without a declared threshold are never high-impact
    (safe default).
    """
    high_impact: list[OutcomeCandidate] = []
    for c in candidates:
        value = c.get("outcome_value_cents")
        if value is None:
            continue
        domain = c.get("context_domain") or ""
        threshold = thresholds_by_domain.get(domain)
        if threshold is None or threshold <= 0:
            continue
        if abs(int(value)) >= threshold:
            high_impact.append(c)
    return high_impact


async def write_feedback_entries_for_outcomes(
    client: Any,
    user_id: str,
    provider: OutcomeProvider,
    candidates: list[OutcomeCandidate],
    thresholds_by_domain: dict[str, int],
) -> int:
    """Route each high-impact outcome to its originating task's feedback.md.

    Returns the count of entries written. Never raises.
    """
    try:
        high_impact = detect_high_impact_candidates(candidates, thresholds_by_domain)
        if not high_impact:
            return 0

        # Group by task_slug so we can write each task's entries in one
        # filesystem upsert per task.
        entries_by_task: dict[str, list[str]] = {}
        unattributable = 0
        for c in high_impact:
            task_slug = await _resolve_task_slug(client, user_id, c)
            if not task_slug:
                unattributable += 1
                continue
            entries_by_task.setdefault(task_slug, []).append(
                _render_feedback_entry(c, provider),
            )

        if unattributable:
            logger.info(
                "[HIGH_IMPACT] user=%s %d high-impact outcome(s) without resolvable "
                "task_slug — skipped (no feedback.md target)",
                user_id[:8], unattributable,
            )

        total_written = 0
        for task_slug, entries in entries_by_task.items():
            ok = await _append_entries_to_task_feedback(
                client, user_id, task_slug, entries,
            )
            if ok:
                total_written += len(entries)
                logger.info(
                    "[HIGH_IMPACT] user=%s task=%s wrote %d system-outcome entries",
                    user_id[:8], task_slug, len(entries),
                )

        return total_written
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[HIGH_IMPACT] write_feedback_entries_for_outcomes failed for user=%s: %s",
            user_id[:8], exc,
        )
        return 0


# ---------------------------------------------------------------------------
# Principles reading: extract thresholds
# ---------------------------------------------------------------------------


def load_high_impact_thresholds(client: Any, user_id: str) -> dict[str, int]:
    """Extract per-domain high-impact thresholds from principles.md.

    Uses `review_policy.load_principles` — principles.md holds
    `high_impact_threshold_cents` per domain per ADR-211 D2 (this is a
    principle about what the operator considers high-impact, not an
    operational autonomy gate). After the ADR-211 principles-vs-modes
    split, auto-approve thresholds moved to modes.md; high-impact
    thresholds stayed in principles.md.

    Returns `{domain: threshold_cents}` for domains that declared a
    positive threshold. Empty dict = no high-impact writes happen.
    """
    try:
        from services.review_policy import load_principles
        policies = load_principles(client, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[HIGH_IMPACT] failed to load principles for user=%s: %s",
            user_id[:8], exc,
        )
        return {}

    thresholds: dict[str, int] = {}
    for domain, policy in policies.items():
        raw = policy.get(_HIGH_IMPACT_KEY)
        try:
            threshold = int(raw) if raw is not None else 0
        except (TypeError, ValueError):
            threshold = 0
        if threshold > 0:
            thresholds[domain] = threshold
    return thresholds


# ---------------------------------------------------------------------------
# Task resolution: proposal_id → action_proposals.task_slug
# ---------------------------------------------------------------------------


async def _resolve_task_slug(
    client: Any, user_id: str, candidate: OutcomeCandidate,
) -> str | None:
    """Resolve the task_slug that produced this outcome.

    Primary path: candidate.proposal_id → action_proposals.task_slug
    (since ADR-193's proposal schema, the creator passes task_slug on
    every ProposeAction call when known).

    Fallback: None — direct platform-tool calls without a proposal
    have no task home. Those outcomes are still recorded in
    _performance.md; they just don't produce a feedback entry.
    """
    proposal_id = candidate.get("proposal_id")
    if not proposal_id:
        return None

    try:
        result = (
            client.table("action_proposals")
            .select("task_slug")
            .eq("id", proposal_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[HIGH_IMPACT] proposal lookup failed for %s: %s",
            proposal_id[:8], exc,
        )
        return None

    rows = result.data or []
    if not rows:
        return None
    return rows[0].get("task_slug") or None


# ---------------------------------------------------------------------------
# Entry rendering
# ---------------------------------------------------------------------------


def _render_feedback_entry(
    candidate: OutcomeCandidate,
    provider: OutcomeProvider,
) -> str:
    """Render a single system-outcome feedback entry (ADR-181 format)."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    action_type = candidate.get("action_type") or "unknown"
    value = candidate.get("outcome_value_cents")
    currency = candidate.get("outcome_currency") or "USD"
    label = candidate.get("outcome_label") or "outcome"
    domain = candidate.get("context_domain") or "unknown"
    executed_at = candidate.get("executed_at")
    if isinstance(executed_at, datetime):
        executed_at_str = executed_at.isoformat(timespec="seconds")
    else:
        executed_at_str = str(executed_at) if executed_at else "unknown"

    value_str = _format_cents(value, currency)
    severity = _severity_for_value(value)

    lines = [
        f"## System Outcome ({now}, source: system_outcome)",
        f"- Domain: `{domain}` · Action: `{action_type}` · Executed: {executed_at_str}",
        f"- Outcome: **{label}** · Realized: **{value_str}** · Confidence: {candidate.get('reconciliation_confidence', 'medium')}",
        f"- Reconciled by: `{provider.provider_name}`",
        f"- Severity: {severity} · Thresholds declared in `/workspace/review/principles.md`",
    ]
    # Include action inputs for agent-readable context
    inputs = candidate.get("action_inputs") or {}
    if inputs:
        key_pairs = [f"{k}={v}" for k, v in inputs.items() if v is not None][:5]
        if key_pairs:
            lines.append(f"- Inputs: {', '.join(key_pairs)}")
    notes = candidate.get("reconciliation_notes")
    if notes:
        lines.append(f"- Notes: {notes}")
    return "\n".join(lines) + "\n"


def _severity_for_value(cents: int | None) -> str:
    """Crude severity tier from absolute magnitude.

    The threshold check gates whether an entry is written at all; this
    tier is a secondary signal for agent/human readers scanning
    feedback.md. Not load-bearing — operator can override by editing
    their principles.md threshold.
    """
    if cents is None:
        return "low"
    abs_cents = abs(int(cents))
    if abs_cents >= 1_000_000:  # $10,000+
        return "high"
    if abs_cents >= 100_000:    # $1,000+
        return "medium"
    return "low"


def _format_cents(cents: int | None, currency: str) -> str:
    if cents is None:
        return "n/a"
    sign = "-" if cents < 0 else ""
    abs_dollars = abs(cents) / 100
    return f"{sign}${abs_dollars:,.2f} {currency}"


# ---------------------------------------------------------------------------
# Filesystem writes to /tasks/{slug}/feedback.md
# ---------------------------------------------------------------------------


async def _append_entries_to_task_feedback(
    client: Any, user_id: str, task_slug: str, new_entries: list[str],
) -> bool:
    """Prepend new entries to the task's feedback.md (newest-first convention).

    Matches the pattern used by task_pipeline's system-verification
    writes (see `_post_run_domain_scan` in task_pipeline.py). Uses
    TaskWorkspace so paths resolve correctly.

    Returns True on success. Never raises.
    """
    try:
        # ADR-231 Phase 3.6.b: route through natural-home feedback path via
        # services.recurrence_paths.
        from services.recurrence_paths import resolve_paths_for_slug
        from services.workspace import UserMemory
        from services.feedback_distillation import _MAX_FEEDBACK_ENTRIES

        paths = resolve_paths_for_slug(client, user_id, task_slug)
        if paths is None or paths.feedback_path is None:
            logger.warning(
                "[HIGH_IMPACT] no feedback path for slug=%s; system-outcome entries dropped",
                task_slug,
            )
            return False

        relative = (
            paths.feedback_path[len("/workspace/"):]
            if paths.feedback_path.startswith("/workspace/") else paths.feedback_path
        )
        um = UserMemory(client, user_id)
        existing = await um.read(relative) or ""

        header = (
            "# Feedback\n"
            "<!-- Source-agnostic feedback layer. Newest first. ADR-181 + ADR-231 D2. -->\n\n"
        )

        all_entries = re.split(r"(?=^## )", existing, flags=re.MULTILINE)
        all_entries = [
            e.strip() for e in all_entries
            if e.strip() and e.strip().startswith("## ")
        ]
        combined = [e.strip() for e in new_entries] + all_entries
        combined = combined[:_MAX_FEEDBACK_ENTRIES]

        content = header + "\n\n".join(combined) + "\n"
        await um.write(
            relative,
            content,
            summary=f"ADR-195 Phase 5: system-outcome entries ({len(new_entries)})",
            authored_by="system:high-impact-outcome",
            message=f"system-outcome feedback for {task_slug}",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[HIGH_IMPACT] append-to-feedback failed for user=%s task=%s: %s",
            user_id[:8], task_slug, exc,
        )
        return False
