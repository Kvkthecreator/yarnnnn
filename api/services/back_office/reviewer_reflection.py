"""Back Office: Reviewer Reflection — ADR-218 + persona-reflection.md.

On cadence, the Reviewer persona reads its own substrate (IDENTITY +
principles + PRECEDENT + MANDATE + AUTONOMY + recent decisions +
per-domain _performance.md) and produces a structured reflection
verdict about whether its framework warrants change.

This is the persona-sided analog to `back-office-reviewer-calibration`
(which rebuilds outcome-tally windows — zero LLM, deterministic) and
to `ManageTask(action="evaluate")` (which evaluates a task output
against its DELIVERABLE — one LLM call, structured verdict). The
shape is deliberately identical: substrate read → single LLM call →
structured verdict → write-back to the relevant file.

**No DSL, no operator-authored metric triggers.** The persona itself
is the judgment that notices its own drift. Task-assessment pattern
applied to persona substrate.

Scope ceiling per persona-reflection.md §4:
  - Reviewer's own directory (/workspace/review/) is the reflection
    target. MANDATE + AUTONOMY + PRECEDENT + context domains + seat-
    state files are untouchable.
  - This module in Commit 2 only READS substrate + returns the
    structured verdict. Phase B/C write-back lands in ADR-218 Commit 3
    (reflection-mode prompt + forced tool call structured output) +
    Commit 4 (reflection_writer applies revisions + chat notification).

Invocation gate (not a trigger DSL — just a cost-saving floor):
  - Hard minimum: at least one new decision since last reflection
    (nothing to reflect on otherwise).
  - Soft rate limit: at most one reflection per 24h regardless of
    activity (prevents reactive loops).

The persona is expected to return `no_change` the common case —
invocation cost is cheap (Haiku) vs the thesis value (persona-as-
accumulator closes the autonomous loop).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from services.workspace_paths import (
    REVIEW_DECISIONS_PATH,
    REVIEW_IDENTITY_PATH,
    REVIEW_PRINCIPLES_PATH,
    SHARED_MANDATE_PATH,
    SHARED_AUTONOMY_PATH,
    SHARED_PRECEDENT_PATH,
)

logger = logging.getLogger(__name__)


# Cost-conscious — Haiku for reflection-assessment, matching the
# EVALUATE_MODEL choice in ManageTask._handle_evaluate.
REFLECTION_MODEL = "claude-haiku-4-5-20251001"

# Invocation gate: don't bother invoking if nothing has happened or if
# we just reflected. These are not triggers — they are cost floors.
_MIN_NEW_DECISIONS = 1
_MIN_HOURS_BETWEEN_REFLECTIONS = 24

# ADR-218 Commit 4: `reflection_writer.apply_reflection_writes` is live.
# When the gate passes AND reflection-mode returns a valid verdict, the
# writer validates each proposal against scope ceiling + mandate-
# preservation heuristics, applies valid ones via ADR-209
# `write_revision(authored_by="reviewer:{occupant}")`, appends the
# reflection entry to `/workspace/review/reflections.md`, and
# publishes a role='reviewer' chat notification via the ADR-212
# reviewer_chat_surfacing pattern when the verdict is material
# (not `no_change`).
_APPLY_WRITEBACK = True


REFLECTIONS_PATH = "review/reflections.md"


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Run a reflection cycle. Same shape as other back-office executors.

    Returns the standard back-office executor shape:
      {
          "content": "<markdown report>",
          "structured": {
              "invoked": bool,                  # did we actually call Haiku
              "reason": str,                    # why invoked or skipped
              "verdict": "no_change" | "narrow" | "relax" | "character_note" | None,
              "proposals": list[dict] | None,   # structured changes from reflection-mode
              "reasoning": str,                 # persona voice, from verdict
              "evidence_summary": str,          # substrate citations, from verdict
              "evidence_snapshot": dict,        # zero-LLM metric snapshot for the report
              "writeback_applied": bool,
              "write_summary": dict | None,     # reflection_writer outcome (Commit 4)
          },
      }
    """
    started_at = datetime.now(timezone.utc)
    structured: dict = {
        "invoked": False,
        "reason": "",
        "verdict": None,
        "proposals": None,
        "reasoning": "",
        "evidence_summary": "",
        "evidence_snapshot": {},
        "writeback_applied": False,
        "write_summary": None,
    }

    try:
        # --- 1. Substrate read (zero LLM) ---
        from services.back_office.reviewer_calibration import (
            _read_decisions,
            _read_domain_outcome_totals,
        )
        decisions = await _read_decisions(client, user_id)
        outcome_totals = await _read_domain_outcome_totals(client, user_id)
        last_reflection_at = await _read_last_reflection_ts(client, user_id)

        new_decisions = _decisions_since(decisions, last_reflection_at)
        hours_since_last = _hours_since(last_reflection_at, started_at)

        structured["evidence_snapshot"] = {
            "total_decisions": len(decisions),
            "new_decisions_since_last_reflection": len(new_decisions),
            "hours_since_last_reflection": (
                round(hours_since_last, 1) if hours_since_last is not None else None
            ),
            "domains_with_performance_md": [
                d for d, v in outcome_totals.items()
                if v.get("has_performance_md")
            ],
        }

        # --- 2. Invocation gate (not a trigger — just cost floors) ---
        if len(new_decisions) < _MIN_NEW_DECISIONS:
            structured["reason"] = (
                f"skipped: {len(new_decisions)} new decisions since last reflection "
                f"(minimum {_MIN_NEW_DECISIONS})"
            )
            return _shape_result(started_at, structured)

        if hours_since_last is not None and hours_since_last < _MIN_HOURS_BETWEEN_REFLECTIONS:
            structured["reason"] = (
                f"skipped: {hours_since_last:.1f}h since last reflection "
                f"(minimum {_MIN_HOURS_BETWEEN_REFLECTIONS}h)"
            )
            return _shape_result(started_at, structured)

        # --- 3. Gather full substrate for the persona ---
        identity_md = await _read_file(client, user_id, REVIEW_IDENTITY_PATH) or ""
        principles_md = await _read_file(client, user_id, REVIEW_PRINCIPLES_PATH) or ""
        precedent_md = await _read_file(client, user_id, SHARED_PRECEDENT_PATH) or ""
        mandate_md = await _read_file(client, user_id, SHARED_MANDATE_PATH) or ""
        autonomy_md = await _read_file(client, user_id, SHARED_AUTONOMY_PATH) or ""

        # Compact decisions view — last ~30 entries is plenty for Haiku
        recent_decisions_md = _format_recent_decisions(decisions, limit=30)
        performance_md_summary = _format_performance_summary(outcome_totals)

        # --- 4. Invoke reflection-mode LLM (ADR-218 Commit 3) ---
        # The persona reads its own substrate + track record + performance
        # summary and returns a structured verdict. run_reflection() never
        # raises — on failure it returns None and we treat it as "no
        # reflection available right now," log it, and exit cleanly.
        from agents.reviewer_agent import run_reflection

        verdict = await run_reflection(
            client=client,
            user_id=user_id,
            identity_md=identity_md,
            principles_md=principles_md,
            precedent_md=precedent_md,
            mandate_md=mandate_md,
            autonomy_md=autonomy_md,
            recent_decisions_md=recent_decisions_md,
            performance_summary=performance_md_summary,
        )

        if verdict is None:
            structured["invoked"] = True
            structured["reason"] = (
                "reflection-mode LLM returned no verdict (model failure or "
                "invalid structured output); treated as no_change"
            )
            structured["verdict"] = "no_change"
            return _shape_result(started_at, structured)

        structured["invoked"] = True
        structured["verdict"] = verdict.get("overall", "no_change")
        structured["proposals"] = verdict.get("proposals") or []
        structured["reasoning"] = verdict.get("reasoning", "")
        structured["evidence_summary"] = verdict.get("evidence_summary", "")
        structured["reason"] = (
            f"reflection verdict: {structured['verdict']} "
            f"({len(structured['proposals'])} proposals)"
        )

        logger.info(
            "[REFLECTION] user=%s verdict=%s proposals=%d",
            user_id[:8],
            structured["verdict"],
            len(structured["proposals"]),
        )

        # --- 5. Write-back (ADR-218 Commit 4) ---
        # reflection_writer validates each proposal against scope ceiling +
        # mandate-preservation heuristics, applies valid ones via ADR-209
        # write_revision with authored_by="reviewer:{occupant_identity}",
        # appends the reflection entry to /workspace/review/reflections.md,
        # and (for material verdicts) publishes a role='reviewer' chat
        # notification. Never raises — partial failures still produce a
        # summary the task output records.
        if not _APPLY_WRITEBACK:
            # Safety branch — leave in place in case a future commit needs
            # to disable write-back temporarily without reverting code.
            structured["reason"] = (
                f"{structured['reason']} (write-back disabled via "
                f"_APPLY_WRITEBACK flag; verdict returned only)"
            )
            return _shape_result(started_at, structured)

        from services.reflection_writer import apply_reflection_writes
        write_summary = await apply_reflection_writes(
            client, user_id,
            verdict={
                "overall": structured["verdict"],
                "reasoning": structured["reasoning"],
                "evidence_summary": structured["evidence_summary"],
                "proposals": structured["proposals"],
            },
            started_at=started_at,
        )
        structured["writeback_applied"] = bool(write_summary.get("writeback_applied"))
        structured["write_summary"] = write_summary
        return _shape_result(started_at, structured)

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[REFLECTION] failed for user=%s: %s", user_id[:8], exc,
        )
        structured["reason"] = f"exception: {exc}"
        return _shape_result(started_at, structured)


# ---------------------------------------------------------------------------
# Helpers — substrate reads + formatters
# ---------------------------------------------------------------------------

async def _read_file(client: Any, user_id: str, path: str) -> str:
    """Read a workspace_files row's content. Empty string on any failure.

    Tolerates both leading-slash and relative forms since workspace_paths
    stores relative paths but substrate reads commonly use the full form.
    """
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
            "[REFLECTION] read failed path=%s user=%s: %s",
            full_path, user_id[:8], exc,
        )
        return ""
    rows = result.data or []
    if not rows:
        return ""
    return rows[0].get("content") or ""


def _decisions_since(decisions: list[dict], cutoff: datetime | None) -> list[dict]:
    """Filter decisions with ts > cutoff. If cutoff is None, return all."""
    if cutoff is None:
        return decisions
    return [d for d in decisions if d.get("ts") and d["ts"] > cutoff]


def _hours_since(then: datetime | None, now: datetime) -> float | None:
    """Hours elapsed between `then` and `now`. Returns None if then is None."""
    if then is None:
        return None
    delta = now - then
    return delta.total_seconds() / 3600.0


def _format_recent_decisions(decisions: list[dict], *, limit: int = 30) -> str:
    """Render the most recent N decisions as compact Markdown for the
    reflection prompt. One line per decision — enough for the persona to
    notice patterns without blowing the prompt budget."""
    if not decisions:
        return "_(no decisions yet)_"
    tail = decisions[-limit:]
    lines: list[str] = []
    for d in tail:
        ts = d.get("ts")
        ts_str = ts.isoformat(timespec="seconds") if ts else "?"
        verdict = d.get("verdict", "?")
        action = d.get("action_type", "?")
        reasoning = (d.get("reasoning") or "").replace("\n", " ")[:180]
        lines.append(f"- `{ts_str}` **{verdict}** on `{action}` — {reasoning}")
    return "\n".join(lines)


def _format_performance_summary(outcome_totals: dict[str, dict]) -> str:
    """Render per-domain performance summary as compact Markdown."""
    if not outcome_totals:
        return "_(no _performance.md files yet)_"
    lines: list[str] = []
    for domain in sorted(outcome_totals.keys()):
        v = outcome_totals[domain] or {}
        if not v.get("has_performance_md"):
            lines.append(f"- `{domain}`: no _performance.md yet")
            continue
        rolling_7d = v.get("rolling_7d_sum_cents")
        rolling_30d = v.get("rolling_30d_sum_cents")
        rolling_90d = v.get("rolling_90d_sum_cents")
        lines.append(
            f"- `{domain}`: "
            f"7d={_cents(rolling_7d)} · 30d={_cents(rolling_30d)} · "
            f"90d={_cents(rolling_90d)}"
        )
    return "\n".join(lines)


def _cents(c: int | None) -> str:
    if c is None:
        return "—"
    return f"${c/100:+.2f}"


# ---------------------------------------------------------------------------
# Last-reflection timestamp (read reflections.md if it exists)
# ---------------------------------------------------------------------------

_REFLECTION_TS_RE = re.compile(
    r"^timestamp:\s*(?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s*$",
    re.MULTILINE,
)


async def _read_last_reflection_ts(
    client: Any, user_id: str
) -> datetime | None:
    """Return the timestamp of the most recent reflection run, or None
    if reflections.md is absent or empty. reflections.md entries land
    with a YAML `timestamp:` line — we parse that directly.
    """
    content = await _read_file(client, user_id, REFLECTIONS_PATH)
    if not content:
        return None

    timestamps: list[datetime] = []
    for m in _REFLECTION_TS_RE.finditer(content):
        ts_str = m.group("ts")
        try:
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            timestamps.append(datetime.fromisoformat(ts_str))
        except ValueError:
            continue

    if not timestamps:
        return None
    return max(timestamps)


# ---------------------------------------------------------------------------
# Back-office executor shape
# ---------------------------------------------------------------------------

def _shape_result(started_at: datetime, structured: dict) -> dict:
    """Produce the back-office executor return shape."""
    es = structured.get("evidence_snapshot") or {}
    lines = [
        "# Reviewer Reflection",
        "",
        f"**Ran**: {started_at.isoformat(timespec='seconds')}",
        f"**Invoked**: {structured.get('invoked')}",
        f"**Reason**: {structured.get('reason', '')}",
    ]
    if structured.get("verdict"):
        lines.append(f"**Verdict**: {structured['verdict']}")

    lines += [
        "",
        "## Evidence summary",
        "",
        f"- Total decisions in decisions.md: {es.get('total_decisions', 0)}",
        f"- New since last reflection: {es.get('new_decisions_since_last_reflection', 0)}",
        f"- Hours since last reflection: {es.get('hours_since_last_reflection', '—')}",
    ]
    domains = es.get("domains_with_performance_md") or []
    if domains:
        lines.append(f"- Domains with _performance.md: {', '.join(domains)}")
    else:
        lines.append("- Domains with _performance.md: none yet")

    # Persona reasoning + evidence summary from the reflection-mode LLM
    # (present when invoked). These land verbatim in reflections.md via
    # reflection_writer; duplicated here for operator task-output audit.
    if structured.get("reasoning"):
        lines += ["", "## Persona reasoning", "", structured["reasoning"]]
    if structured.get("evidence_summary"):
        lines += ["", "## Persona evidence summary", "", structured["evidence_summary"]]

    proposals = structured.get("proposals") or []
    if proposals:
        lines += ["", "## Proposals", ""]
        for p in proposals:
            lines.append(
                f"- **{p.get('change_type', '?')}** on `{p.get('target_file', '?')}`: "
                f"{p.get('reasoning', '')}"
            )

    write_summary = structured.get("write_summary")
    if write_summary:
        lines += [
            "",
            "## Write-back",
            "",
            f"- Applied: {write_summary.get('proposals_applied', 0)} / {write_summary.get('proposals_total', 0)} proposals",
            f"- Rejected: {write_summary.get('proposals_rejected', 0)}",
            f"- reflections.md appended: {write_summary.get('reflections_md_appended', False)}",
            f"- Chat notified: {write_summary.get('chat_notified', False)}",
        ]
        for rej in write_summary.get("rejections") or []:
            lines.append(
                f"  - rejected `{rej.get('target_file', '?')}`: {rej.get('reason', '?')}"
            )

    if not _APPLY_WRITEBACK:
        lines += [
            "",
            "_Write-back disabled via `_APPLY_WRITEBACK` flag — verdict returned "
            "for operator audit but no files mutated._",
        ]

    return {
        "content": "\n".join(lines) + "\n",
        "structured": structured,
    }
