"""Reflection Writer — ADR-218 Commit 4.

Applies the structured verdict from `reviewer_agent.run_reflection()` to
the Reviewer's substrate. Single responsibility: validate + write, with
every mutation landing as an ADR-209 revision authored by the current
Reviewer occupant.

Called by `services.back_office.reviewer_reflection.run()` after
reflection-mode LLM returns a verdict. Never raises — failures log and
return a "writeback_applied: False" summary so the back-office task
still produces a clean output record. Operator can always retry by
waiting for the next reflection cycle.

Scope ceiling (enforced here, not trusted from the model):
  - Proposals may only target `principles.md` or `IDENTITY.md`.
    Anything else is rejected with a logged warning.
  - Proposals that would empty the file to <50 characters are rejected
    (weak heuristic against accidental mass-deletion from model error).
  - Mandate-preservation sanity check: proposed new_content must not
    contain the literal phrase "overrides mandate" or any clause that
    appears to widen autonomy; this is a weak string-match heuristic,
    not a semantic check. Stronger checks are out of scope for V1 —
    operator revert path via ADR-209 revision chain is the final
    safety floor.

Writes:
  - Each approved proposal → `write_revision` on target file.
  - Always append a reflections.md entry via `write_revision` on
    `/workspace/review/reflections.md` (append-only per
    persona-reflection.md §2).
  - Material verdicts (overall != "no_change") → chat notification
    via `write_reviewer_message` (ADR-212 pattern).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, TypedDict

from services.authored_substrate import write_revision
from services.workspace_paths import (
    REVIEW_IDENTITY_PATH,
    REVIEW_PRINCIPLES_PATH,
    SHARED_AUTONOMY_PATH,
    SHARED_MANDATE_PATH,
)

logger = logging.getLogger(__name__)


# Scope ceiling — files reflection is allowed to modify. Everything else
# is rejected at validation time with a logged warning.
_ALLOWED_TARGET_FILES = {
    "principles.md": REVIEW_PRINCIPLES_PATH,
    "IDENTITY.md": REVIEW_IDENTITY_PATH,
}

# Minimum content length after validation — catches accidental
# mass-deletion from model error. Operator can still author a short
# file directly; this only catches reflection-mode model errors.
_MIN_CONTENT_LENGTH = 50

# Path for the append-only reflection log.
_REFLECTIONS_PATH = "review/reflections.md"

# Reviewer occupant identity string used as authored_by. Matches the
# identity that renders verdicts in review_proposal_dispatch so the
# revision chain attribution is legible. Sourced from reviewer_agent
# lazily to avoid circular import at module load.


class ApplySummary(TypedDict):
    """Return shape of apply_reflection_writes — back-office task puts
    this under `structured.write_summary`."""
    writeback_applied: bool
    proposals_total: int
    proposals_applied: int
    proposals_rejected: int
    reflections_md_appended: bool
    chat_notified: bool
    rejections: list[dict]  # each entry: {target_file, reason}


async def apply_reflection_writes(
    client: Any,
    user_id: str,
    verdict: dict,
    started_at: datetime,
) -> ApplySummary:
    """Apply a reflection verdict.

    `verdict` is the dict returned by `reviewer_agent.run_reflection()`
    (same shape as ReflectionVerdict TypedDict). Writer:
      1. Validates each proposal against scope ceiling + content-length
         + mandate-preservation heuristics.
      2. Writes valid proposals via `write_revision` (ADR-209 chain).
      3. Appends a reflections.md entry regardless of whether any
         proposals applied (the reflection itself is worth logging —
         no_change verdicts with substantive reasoning are valuable
         audit artifacts).
      4. Publishes a chat notification when the overall verdict is
         material (not no_change).

    Returns a summary the back-office task puts under
    `structured.write_summary`.

    Never raises. Partial-failure (some proposals write, others
    reject, reflections.md fails) still returns a summary — operator
    audits via the task output folder.
    """
    from agents.reviewer_agent import REVIEWER_MODEL_IDENTITY

    summary: ApplySummary = {
        "writeback_applied": False,
        "proposals_total": 0,
        "proposals_applied": 0,
        "proposals_rejected": 0,
        "reflections_md_appended": False,
        "chat_notified": False,
        "rejections": [],
    }

    overall = (verdict.get("overall") or "no_change").strip()
    reasoning = (verdict.get("reasoning") or "").strip()
    evidence_summary = (verdict.get("evidence_summary") or "").strip()
    proposals = verdict.get("proposals") or []
    summary["proposals_total"] = len(proposals)

    # Read MANDATE + AUTONOMY for the mandate-preservation sanity check.
    # Not found → skip the check; treat as permissive.
    mandate_md = _read_file_sync(client, user_id, SHARED_MANDATE_PATH)
    autonomy_md = _read_file_sync(client, user_id, SHARED_AUTONOMY_PATH)

    authored_by = f"reviewer:{REVIEWER_MODEL_IDENTITY}"

    # --- 1. Apply each proposal (skip + log invalid ones) ---
    applied_proposals: list[dict] = []
    for p in proposals:
        ok, reason = _validate_proposal(p, mandate_md=mandate_md, autonomy_md=autonomy_md)
        if not ok:
            summary["proposals_rejected"] += 1
            summary["rejections"].append(
                {"target_file": p.get("target_file", ""), "reason": reason}
            )
            logger.warning(
                "[REFLECTION_WRITER] rejected proposal user=%s target=%s reason=%s",
                user_id[:8],
                p.get("target_file", "?"),
                reason,
            )
            continue

        target_rel = _ALLOWED_TARGET_FILES[p["target_file"]]
        message = _compose_revision_message(p, overall)
        try:
            revision_id = write_revision(
                client,
                user_id=user_id,
                path=target_rel,
                content=p["new_content"],
                authored_by=authored_by,
                message=message,
                summary=f"Reflection {overall}: {p.get('target_file', '?')}",
            )
            summary["proposals_applied"] += 1
            applied_proposals.append({
                "target_file": p["target_file"],
                "change_type": p.get("change_type", "?"),
                "revision_id": revision_id,
            })
        except Exception as exc:  # noqa: BLE001
            summary["proposals_rejected"] += 1
            summary["rejections"].append(
                {"target_file": p["target_file"], "reason": f"write failed: {exc}"}
            )
            logger.warning(
                "[REFLECTION_WRITER] write failed user=%s target=%s: %s",
                user_id[:8], p["target_file"], exc,
            )

    # --- 2. Append reflections.md entry (always, even for no_change) ---
    try:
        entry = _render_reflections_entry(
            started_at=started_at,
            overall=overall,
            reasoning=reasoning,
            evidence_summary=evidence_summary,
            proposals_applied=applied_proposals,
            proposals_rejected=summary["rejections"],
            reviewer_identity=REVIEWER_MODEL_IDENTITY,
        )
        existing = _read_file_sync(client, user_id, _REFLECTIONS_PATH)
        new_content = _append_to_reflections_md(existing, entry)
        write_revision(
            client,
            user_id=user_id,
            path=_REFLECTIONS_PATH,
            content=new_content,
            authored_by=authored_by,
            message=f"Reflection {overall}: {len(applied_proposals)} applied, {len(summary['rejections'])} rejected",
            summary="Reflection entry appended",
        )
        summary["reflections_md_appended"] = True
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REFLECTION_WRITER] reflections.md append failed for user=%s: %s",
            user_id[:8], exc,
        )

    # --- 3. Chat notification for material verdicts ---
    if overall != "no_change":
        try:
            from services.reviewer_chat_surfacing import write_reviewer_message
            notification = _render_chat_notification(
                overall=overall,
                reasoning=reasoning,
                proposals_applied=applied_proposals,
                proposals_rejected=summary["rejections"],
            )
            await write_reviewer_message(
                client, user_id,
                content=notification,
                verdict=f"reflection:{overall}",
                occupant=REVIEWER_MODEL_IDENTITY,
            )
            summary["chat_notified"] = True
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[REFLECTION_WRITER] chat notification failed for user=%s: %s",
                user_id[:8], exc,
            )

    summary["writeback_applied"] = (
        summary["proposals_applied"] > 0
        or summary["reflections_md_appended"]
    )
    return summary


# ---------------------------------------------------------------------------
# Proposal validation
# ---------------------------------------------------------------------------

# Weak heuristics for "this proposal looks like it's trying to widen
# delegation." Not semantically rigorous — string matches on phrases
# that should not appear in a framework-narrowing reflection. Operator
# revert via ADR-209 revision chain is the definitive safety.
_FORBIDDEN_PHRASES = (
    "overrides mandate",
    "override mandate",
    "overrides autonomy",
    "override autonomy",
    "can auto-approve regardless",
    "approve without evidence",
    "bypass autonomy",
    "widens delegation",
)


def _validate_proposal(
    p: dict,
    *,
    mandate_md: str,
    autonomy_md: str,
) -> tuple[bool, str]:
    """Return (valid, reason). Valid == safe to apply.

    Checks (ordered):
      1. target_file is in the scope ceiling (principles.md or
         IDENTITY.md).
      2. change_type is a known value.
      3. new_content meets _MIN_CONTENT_LENGTH (guards accidental
         mass-deletion).
      4. new_content doesn't contain any _FORBIDDEN_PHRASES (weak
         heuristic for delegation-widening attempts).
    """
    target_file = (p.get("target_file") or "").strip()
    if not target_file:
        return False, "empty target_file"
    if target_file not in _ALLOWED_TARGET_FILES:
        return False, f"target_file '{target_file}' outside scope ceiling (only principles.md / IDENTITY.md allowed)"

    change_type = (p.get("change_type") or "").strip()
    if change_type not in ("narrow", "relax", "character_note", "no_change"):
        return False, f"invalid change_type '{change_type}'"
    if change_type == "no_change":
        # No-op proposal — shouldn't happen with valid model output but
        # coerce to skip rather than write an empty revision.
        return False, "change_type=no_change means no-op; skipping"

    new_content = p.get("new_content") or ""
    if len(new_content.strip()) < _MIN_CONTENT_LENGTH:
        return False, (
            f"new_content is only {len(new_content.strip())} chars — "
            f"below {_MIN_CONTENT_LENGTH}-char minimum "
            "(guards against accidental mass-deletion)"
        )

    lowered = new_content.lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in lowered:
            return False, f"new_content contains forbidden phrase '{phrase}' (weak delegation-widening heuristic)"

    # Mandate + autonomy are not parsed semantically here; we only
    # reject obvious contradiction patterns above. The Reviewer prompt
    # explicitly tells the persona not to propose mandate-contradicting
    # changes; the revision chain is the audit + revert path.
    _ = mandate_md  # Reserved for future semantic checks.
    _ = autonomy_md

    return True, "valid"


# ---------------------------------------------------------------------------
# Reflections.md rendering + append
# ---------------------------------------------------------------------------

def _render_reflections_entry(
    *,
    started_at: datetime,
    overall: str,
    reasoning: str,
    evidence_summary: str,
    proposals_applied: list[dict],
    proposals_rejected: list[dict],
    reviewer_identity: str,
) -> str:
    """Render one entry for reflections.md. Format is substrate-stable
    so future reflection runs can parse the `timestamp:` line to detect
    the last-reflection timestamp."""
    parts: list[str] = []
    parts.append("--- reflection ---")
    parts.append(f"timestamp: {started_at.isoformat(timespec='seconds')}")
    parts.append(f"reviewer_identity: {reviewer_identity}")
    parts.append(f"overall: {overall}")
    parts.append("")

    if reasoning:
        parts.append("## Reasoning")
        parts.append("")
        parts.append(reasoning)
        parts.append("")

    if evidence_summary:
        parts.append("## Evidence")
        parts.append("")
        parts.append(evidence_summary)
        parts.append("")

    if proposals_applied:
        parts.append("## Proposals applied")
        parts.append("")
        for ap in proposals_applied:
            parts.append(
                f"- **{ap.get('change_type', '?')}** on `{ap.get('target_file', '?')}` "
                f"(revision `{ap.get('revision_id', '?')[:8]}…`)"
            )
        parts.append("")

    if proposals_rejected:
        parts.append("## Proposals rejected (validation)")
        parts.append("")
        for rej in proposals_rejected:
            parts.append(
                f"- `{rej.get('target_file', '?')}`: {rej.get('reason', '?')}"
            )
        parts.append("")

    parts.append("---")
    parts.append("")
    return "\n".join(parts)


def _append_to_reflections_md(existing: str, entry: str) -> str:
    """Append a new entry to reflections.md, preserving the file header
    if present. Entries are newest-last (chronological order) — matches
    decisions.md convention."""
    header = (
        "# Reviewer Reflections\n\n"
        "Append-only log of the Reviewer's reflection cycles (ADR-218). "
        "Each entry is written by `services/reflection_writer.py` when "
        "the back-office reflection task completes.\n\n"
    )
    if not existing or not existing.strip():
        return header + entry
    # Ensure separator between existing and new entry
    if existing.endswith("\n\n"):
        return existing + entry
    if existing.endswith("\n"):
        return existing + "\n" + entry
    return existing + "\n\n" + entry


# ---------------------------------------------------------------------------
# Chat notification rendering
# ---------------------------------------------------------------------------

def _render_chat_notification(
    *,
    overall: str,
    reasoning: str,
    proposals_applied: list[dict],
    proposals_rejected: list[dict],
) -> str:
    """Build the role='reviewer' chat message body for a material
    reflection verdict. Short — matches ADR-212 verdict-notification
    brevity; full detail lives in reflections.md."""
    lines: list[str] = []
    lines.append(f"**Reviewer reflected — verdict: {overall}**")
    lines.append("")
    if reasoning:
        # Trim to ~2 sentences or ~300 chars for chat readability
        trimmed = reasoning[:300]
        if len(reasoning) > 300:
            trimmed += "…"
        lines.append(trimmed)
        lines.append("")
    if proposals_applied:
        changed = [
            f"`{ap.get('target_file', '?')}` ({ap.get('change_type', '?')})"
            for ap in proposals_applied
        ]
        lines.append(f"Applied: {', '.join(changed)}")
    if proposals_rejected:
        lines.append(f"Rejected {len(proposals_rejected)} proposal(s) at validation.")
    lines.append("")
    lines.append("_Full reasoning + evidence in `/workspace/review/reflections.md`._")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Revision message composition
# ---------------------------------------------------------------------------

def _compose_revision_message(p: dict, overall: str) -> str:
    """Compose the ADR-209 revision message for a single proposal
    write. Operator-readable, evidence-cited."""
    change_type = p.get("change_type", "?")
    reasoning = (p.get("reasoning") or "").strip()
    evidence = (p.get("evidence") or "").strip()
    parts = [f"Reviewer reflection ({overall}, {change_type}):"]
    if reasoning:
        parts.append(reasoning)
    if evidence:
        parts.append(f"Evidence: {evidence}")
    return " ".join(parts)[:500]  # keep revision messages concise


# ---------------------------------------------------------------------------
# Substrate read helper (sync — write_revision is sync too)
# ---------------------------------------------------------------------------

def _read_file_sync(client: Any, user_id: str, path: str) -> str:
    """Read a workspace_files row's content synchronously. Empty string
    on any failure. Matches the path-convention tolerance elsewhere in
    the codebase — accepts both /workspace/-prefixed and bare paths."""
    full_path = path if path.startswith("/workspace/") else f"/workspace/{path.lstrip('/')}"
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", full_path)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REFLECTION_WRITER] read failed path=%s user=%s: %s",
            full_path, user_id[:8], exc,
        )
        return ""
    rows = result.data or []
    if not rows:
        return ""
    return rows[0].get("content") or ""
