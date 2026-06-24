"""Reviewer Judgment Lineage — appends entries to /workspace/persona/judgment_log.md
(ADR-194 v2 Phase 2a + ADR-281 §5).

Every approve / reject that flows through ExecuteProposal / RejectProposal
calls `append_decision` here. Every Reviewer-wake that produces a material
outcome (per the §5.D3 5-condition gate) has its lineage entry rendered by
`render_lineage_entry_if_material`. The entry format is YAML-frontmatter-like
delimited blocks so parsers (calibration loop, frontend lineage view) can
round-trip the log cheaply.

Per FOUNDATIONS Axiom 1 (Substrate), judgment_log.md IS the audit trail.
Narrow metadata on action_proposals (reviewer_identity / reviewer_reasoning)
is for UX only — the full record is the filesystem append.

ADR-281 §5.D1: file renamed `decisions.md` → `judgment_log.md`. The role of
the file sharpens — it's the Reviewer's structured lineage of
operation-shaping judgment moments, not a wake-audit log. Routine
stand-downs DO NOT produce entries per the §5.D3 material-outcome gate;
their canonical home is `execution_events` (kernel-side forensic substrate
per ADR-265) + the feed-surface narrative entry (per ADR-258 revised).

ADR-281 §5.D4: `append_recurrence_fire` blanket-write DELETED. It produced
an entry for every recurrence-fire wake whether or not the wake had a
material outcome — exactly the duplication ADR-277 named at the feed-emission
layer, applied at the substrate-write layer. Replaced by the
`render_lineage_entry_if_material` function which evaluates the
ReviewerOutput against the deterministic 5-condition gate.

File convention:
  /workspace/persona/judgment_log.md

Append semantics:
- First write creates the file with a header.
- Subsequent writes append a new delimited block.
- Newest entries appear last (chronological append).

Entry formats:

  --- decision ---                       (proposal-arrival path, append_decision)
  timestamp: 2026-04-19T10:15:03+00:00
  proposal_id: <uuid>
  action_type: trading.submit_order
  decision: approve  | reject  | defer
  reviewer_identity: human:<user_id>  |  ai:<slug>  |  ...
  reversibility: reversible
  outcome: executed | rejected_at_execution | expired
  ---
  <free-form reasoning from the Reviewer>

  --- material-outcome ---               (recurrence-fire path, conditional)
  timestamp: 2026-05-15T07:00:00+00:00
  slug: morning-reflection
  trigger: reactive
  reviewer_identity: ai:reviewer-sonnet-v8
  outcome_kind: propose_action | schedule_create | schedule_update | schedule_archive
              | write_operator_canon | clarify | meta_verdict
  ---
  <free-form Reviewer verdict + reasoning, markdown-allowed>
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from services.workspace_paths import PERSONA_JUDGMENT_LOG_PATH

logger = logging.getLogger(__name__)


#: Canonical filesystem home for the Reviewer's judgment lineage (ADR-281 §5).
#: The constant `JUDGMENT_LOG_PATH` is the full /workspace/-prefixed path used
#: by the DB read/write helpers below. Callers that need the workspace-relative
#: path should import PERSONA_JUDGMENT_LOG_PATH from services.workspace_paths.
JUDGMENT_LOG_PATH = f"/workspace/{PERSONA_JUDGMENT_LOG_PATH}"


Decision = Literal["approve", "reject", "defer"]


# ---------------------------------------------------------------------------
# Material-outcome gate (ADR-281 §5.D3)
# ---------------------------------------------------------------------------
#
# Deterministic, code-evaluated. The kernel renders a lineage entry iff at
# least one of the 5 conditions holds:
#   1. ProposeAction was called (proposal awaiting review)
#   2. Schedule was called with action ∈ {create, update, archive}
#   3. WriteFile was called against an operator-canon substrate path
#   4. Clarify was called (operator-acknowledgment requested — 2026-05-25
#      simplification per docs/evaluations/2026-05-25-042827-clarify-
#      silenced-from-feed/. Pre-2026-05-25 the gate read a clarify_alert
#      tool-input field that doesn't exist on CLARIFY_TOOL — dead code.)
#   5. ReturnVerdict.verdict ∈ {pause_autonomy, narrow, relax, character_note}
#
# Stand-downs with no material outcome leave the wake's existence in
# execution_events + the feed narrative entry, NOT in judgment_log.

# Verdict values that are themselves operation-shaping outcomes (condition 5).
_META_OUTCOME_VERDICTS = frozenset([
    "pause_autonomy",
    "narrow",
    "relax",
    "character_note",
    # ADR-359 D2: a missed occasion (owed work not produced this runtime) is an
    # operation-shaping outcome — surface it, do not let it pass as silent.
    "non_performance",
])

# Schedule actions that count as operation-shaping (condition 2).
_OPERATION_SHAPING_SCHEDULE_ACTIONS = frozenset([
    "create", "update", "archive",
])


def _detect_outcome_kind(reviewer_output: dict) -> str | None:
    """Return the outcome_kind label for the wake's actions_taken,
    or None if no material outcome was produced (the §5.D3 gate).

    The kind label is the substring written into the rendered entry's
    `outcome_kind:` field so future readers can quickly tell what kind of
    material outcome the wake produced.
    """
    if not isinstance(reviewer_output, dict):
        return None

    # Condition 5: meta-level verdict.
    verdict = reviewer_output.get("verdict")
    if isinstance(verdict, str) and verdict in _META_OUTCOME_VERDICTS:
        return f"meta_verdict:{verdict}"

    actions = reviewer_output.get("actions_taken") or []
    if not isinstance(actions, list):
        return None

    # Inspect each tool call.
    proposed = False
    schedule_action = None
    write_to_operator_canon = False
    clarify_alert = False
    for action in actions:
        if not isinstance(action, dict):
            continue
        tool_name = action.get("tool") or action.get("name")
        tool_input = action.get("input") or action.get("args") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}

        # Condition 1: ProposeAction called.
        if tool_name == "ProposeAction":
            proposed = True

        # Condition 2: Schedule with create/update/archive.
        if tool_name == "Schedule":
            action_arg = tool_input.get("action")
            if isinstance(action_arg, str) and action_arg in _OPERATION_SHAPING_SCHEDULE_ACTIONS:
                schedule_action = action_arg

        # Condition 3: WriteFile to an operator-canon path. We detect this
        # heuristically here (looking at the write-result for a lock-policy
        # signal would be more precise but couples too tightly to the
        # write-handler internals). If the write_handler ultimately rejects
        # the write (locked path), then it doesn't count — but if the write
        # succeeded against an operator-canon path (operator unlocked via
        # _locks.yaml or workspace guide overrides), that IS operation-shaping.
        if tool_name == "WriteFile":
            result = action.get("result") or {}
            if isinstance(result, dict) and result.get("success"):
                path = tool_input.get("path") or ""
                # Operator-canon paths have a stable prefix set; this check
                # is intentionally conservative — only matches the
                # universal operator-canon paths to keep the gate
                # deterministic without consulting the workspace guide
                # (which would re-introduce per-wake substrate reads at
                # gate-evaluation time, against Derived Principle 19).
                # Bundle-declared operator-canon paths are still rare to
                # write to (locked by default); when they do get written,
                # the universal-paths check covers the common cases.
                # ADR-320: operator-canon = constitution/ (MANDATE, PRECEDENT) +
                # the persona's reasoning-character files (IDENTITY, principles).
                # governance/ is NOT here — the Reviewer cannot write it at all
                # (topology lock), so a governance write never reaches this gate.
                operator_canon_prefixes = (
                    "constitution/",
                    "/workspace/constitution/",
                    "persona/IDENTITY.md",
                    "persona/principles.md",
                    "/workspace/persona/IDENTITY.md",
                    "/workspace/persona/principles.md",
                )
                if any(path.startswith(p) for p in operator_canon_prefixes):
                    write_to_operator_canon = True

        # Condition 4: Clarify was called. The Reviewer asking the
        # operator for input is operation-shaping — the operator's
        # answer (or non-answer) directly shapes the next cycle. Pre-
        # 2026-05-25 this branch read tool_input.get('clarify_alert')
        # which doesn't exist on the CLARIFY_TOOL schema (registry.py:
        # 127-148) — the gate was structurally unreachable. Fix
        # documented in docs/evaluations/2026-05-25-042827-clarify-
        # silenced-from-feed/findings.md Gap 3. Simplification to
        # presence-based gate matches the operator-acknowledgment
        # rationale: any Clarify is lineage-worthy.
        if tool_name == "Clarify":
            clarify_alert = True

    if proposed:
        return "propose_action"
    if schedule_action:
        return f"schedule_{schedule_action}"
    if write_to_operator_canon:
        return "write_operator_canon"
    if clarify_alert:
        return "clarify"
    return None


async def render_lineage_entry_if_material(
    client: Any,
    user_id: str,
    *,
    reviewer_output: dict,
    slug: str,
    trigger: str,
    reviewer_identity: str,
) -> bool:
    """Evaluate the §5.D3 material-outcome gate; render an entry iff material.

    Called by `services/wake.py` (per ADR-296 v2 D1) after every Reviewer
    wake that escalated through the funnel. Replaces the deleted
    `append_recurrence_fire` blanket-write.

    Returns True iff an entry was rendered (i.e. the wake was material).

    Never raises — lineage failures must not block dispatcher flow.
    """
    try:
        outcome_kind = _detect_outcome_kind(reviewer_output)
        if outcome_kind is None:
            # Routine stand-down — no material outcome. Wake's existence
            # is in execution_events + feed narrative entry. No lineage entry.
            return False

        reasoning = ""
        if isinstance(reviewer_output, dict):
            reasoning = reviewer_output.get("reasoning") or ""

        block = _render_material_outcome_entry(
            slug=slug,
            trigger=trigger,
            reviewer_identity=reviewer_identity,
            outcome_kind=outcome_kind,
            reasoning=reasoning,
        )

        existing = _read_sync(client, user_id)
        if existing is None:
            content = _HEADER + "\n\n" + block
        else:
            content = existing.rstrip() + "\n\n" + block

        ok = _write_material_outcome_sync(
            client,
            user_id,
            content,
            reviewer_identity=reviewer_identity,
            slug=slug,
            trigger=trigger,
            outcome_kind=outcome_kind,
        )
        return ok
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_AUDIT] render_lineage_entry_if_material failed for "
            "user=%s slug=%s: %s",
            user_id[:8] if user_id else "?",
            slug,
            exc,
        )
        return False


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
    """Append a decision entry to the judgment log (proposal-arrival path).

    Creates the file (with a header) on first write. Appends a delimited
    block on subsequent writes. Never raises — audit trail failures must
    not block approval/rejection. Returns True on success.
    """
    try:
        block = _render_decision_entry(
            proposal_id=proposal_id,
            action_type=action_type,
            decision=decision,
            reviewer_identity=reviewer_identity,
            reasoning=reasoning,
            reversibility=reversibility,
            outcome=outcome,
        )

        existing = _read_sync(client, user_id)
        if existing is None:
            content = _HEADER + "\n\n" + block
        else:
            content = existing.rstrip() + "\n\n" + block

        ok = _write_decision_sync(
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
    except Exception as exc:  # noqa: BLE001
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
# Review — Judgment Log

Append-only log of every operation-shaping judgment moment in this workspace.
Newest entries at the bottom. Two entry kinds:

- `--- decision ---` blocks record proposal verdicts (approve / reject /
  defer) from the proposal-arrival reactive path.
- `--- material-outcome ---` blocks record recurrence-fire wakes that
  produced operation-shaping outcomes (ProposeAction, Schedule
  create/update/archive, WriteFile to operator-canon, Clarify alert, or
  meta-level verdict). Routine stand-downs leave no entry here — their
  existence is captured in execution_events + the feed narrative.

Written by the Reviewer layer (ADR-194 v2 + ADR-281 §5). The Reviewer
itself does NOT WriteFile to this path directly — infrastructure renders
entries from the Reviewer's structured ReturnVerdict output (single-writer
contract per ADR-281 §5.D2). See `/workspace/persona/IDENTITY.md` for the
Reviewer's identity and `/workspace/persona/principles.md` for the declared
review framework.
"""


def _render_decision_entry(
    *,
    proposal_id: str,
    action_type: str,
    decision: Decision,
    reviewer_identity: str,
    reasoning: str,
    reversibility: str | None,
    outcome: str | None,
) -> str:
    """Render a single decision block (proposal-arrival path)."""
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


def _render_material_outcome_entry(
    *,
    slug: str,
    trigger: str,
    reviewer_identity: str,
    outcome_kind: str,
    reasoning: str,
) -> str:
    """Render a single material-outcome block (recurrence-fire path)."""
    ts = datetime.now(timezone.utc).isoformat()
    lines = [
        "--- material-outcome ---",
        f"timestamp: {ts}",
        f"slug: {slug}",
        f"trigger: {trigger}",
        f"reviewer_identity: {reviewer_identity}",
        f"outcome_kind: {outcome_kind}",
        "---",
    ]
    if reasoning.strip():
        lines.append(reasoning.strip())
    else:
        lines.append("_(no reasoning supplied)_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# filesystem I/O
# ---------------------------------------------------------------------------


def _read_sync(client: Any, user_id: str) -> str | None:
    """Return current judgment_log.md content or None if absent."""
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", JUDGMENT_LOG_PATH)
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


def _write_decision_sync(
    client: Any,
    user_id: str,
    content: str,
    *,
    reviewer_identity: str,
    proposal_id: str,
    decision: str,
) -> bool:
    """Write judgment_log.md through the Authored Substrate (ADR-209)."""
    try:
        from services.authored_substrate import write_revision

        write_revision(
            client,
            user_id=user_id,
            path=JUDGMENT_LOG_PATH,
            content=content,
            authored_by=f"reviewer:{reviewer_identity}",
            message=f"{decision} proposal {proposal_id[:8] if proposal_id else '?'}",
            summary="Reviewer judgment log",
            tags=["_judgment_log", "review", "audit"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_AUDIT] write failed for user=%s: %s", user_id[:8], exc,
        )
        return False


def _write_material_outcome_sync(
    client: Any,
    user_id: str,
    content: str,
    *,
    reviewer_identity: str,
    slug: str,
    trigger: str,
    outcome_kind: str,
) -> bool:
    """Write judgment_log.md through Authored Substrate for a material-outcome entry."""
    try:
        from services.authored_substrate import write_revision

        write_revision(
            client,
            user_id=user_id,
            path=JUDGMENT_LOG_PATH,
            content=content,
            authored_by=f"reviewer:{reviewer_identity}",
            message=f"material-outcome {slug} ({outcome_kind})",
            summary="Reviewer judgment log",
            tags=["_judgment_log", "review", "audit", "material-outcome"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_AUDIT] material-outcome write failed for user=%s: %s",
            user_id[:8],
            exc,
        )
        return False
