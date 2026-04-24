"""Back Office: Reviewer Calibration — ADR-211 D6.

Cross-references the Reviewer seat's verdict trail (`decisions.md`) with
reconciled outcomes per domain (`/workspace/context/{domain}/_performance.md`),
producing `/workspace/review/calibration.md` — the per-occupant, per-verdict
rolling-window summary that closes the money-truth → future-judgment loop
(FOUNDATIONS Axiom 7 + Axiom 8).

Runs after `back-office-outcome-reconciliation` (daily). Rebuilt from
scratch each cycle — no partial updates, no append pattern.

Consumer surface:
  - AI occupants read their own calibration section as prior context
    for future verdicts.
  - Operator reads the file when deciding whether to rotate the occupant
    or tune `modes.md`.
  - Frontend `/review` page may surface calibration summaries (Phase 4.1
    or later).

Zero LLM cost. Pure filesystem reads + deterministic aggregation.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from services.workspace_paths import (
    REVIEW_DECISIONS_PATH,
    REVIEW_CALIBRATION_PATH,
)

logger = logging.getLogger(__name__)


# Rolling windows (days). Match ADR-195 v2.2 convention.
_WINDOW_DAYS = {
    "rolling_7d": 7,
    "rolling_30d": 30,
    "rolling_90d": 90,
}

# Verdict categories parsed from decisions.md.
_VERDICT_CATEGORIES = ("approve", "reject", "defer")


async def run(client: Any, user_id: str, task_slug: str) -> dict:
    """Rebuild /workspace/review/calibration.md for this user.

    Returns the standard back-office executor shape:
      {
          "content": "<markdown report>",
          "structured": {
              "decisions_parsed": int,
              "occupants": list[str],
              "windows": dict[str, dict],
              "calibration_written": bool,
          },
      }
    """
    started_at = datetime.now(timezone.utc)

    try:
        # 1. Read decisions.md (verdict trail)
        decisions = await _read_decisions(client, user_id)

        # 2. Read per-domain outcome tallies (thin — no recomputation,
        #    just read what the reconciler already wrote)
        outcome_totals = await _read_domain_outcome_totals(client, user_id)

        # 3. Compute rolling-window aggregates per occupant × verdict
        windows = _compute_windows(decisions, started_at)

        # 4. Render calibration.md
        content = _render_calibration_md(
            started_at=started_at,
            windows=windows,
            outcome_totals=outcome_totals,
            decisions_count=len(decisions),
        )

        # 5. Write (replaces existing content — Axiom 1 substrate write)
        from services.workspace import UserMemory
        um = UserMemory(client=client, user_id=user_id)
        await um.write(
            REVIEW_CALIBRATION_PATH,
            content,
            summary=f"Reviewer calibration rebuild — {len(decisions)} decisions over 90d",
        )

        occupants_seen = sorted({d["occupant"] for d in decisions})

        return {
            "content": _render_report(
                started_at=started_at,
                decisions_count=len(decisions),
                occupants=occupants_seen,
                windows=windows,
            ),
            "structured": {
                "decisions_parsed": len(decisions),
                "occupants": occupants_seen,
                "windows": windows,
                "calibration_written": True,
            },
        }
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[REVIEWER_CALIBRATION] rebuild failed for user=%s: %s",
            user_id[:8], exc,
        )
        return {
            "content": f"# Reviewer Calibration — Error\n\nRebuild failed: `{exc}`\n",
            "structured": {
                "decisions_parsed": 0,
                "occupants": [],
                "windows": {},
                "calibration_written": False,
            },
        }


# ---------------------------------------------------------------------------
# decisions.md reading
# ---------------------------------------------------------------------------

async def _read_decisions(client: Any, user_id: str) -> list[dict]:
    """Read and parse decisions.md into a list of verdict entries.

    Each entry: {
        "ts": datetime,      # UTC
        "proposal_id": str,
        "action_type": str,
        "verdict": str,      # approve | reject | defer
        "occupant": str,     # identity string (human:<id>, ai:<model>, ...)
        "reasoning": str,    # trailing reasoning (first line only)
    }

    Tolerant parser — skips malformed entries, never raises.
    Returns empty list on missing / unreadable file.
    """
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", REVIEW_DECISIONS_PATH)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[REVIEWER_CALIBRATION] decisions.md read failed user=%s: %s",
            user_id[:8], exc,
        )
        return []

    rows = result.data or []
    if not rows:
        return []
    content = rows[0].get("content") or ""
    return _parse_decisions_md(content)


# decisions.md entry format (source of truth: services/reviewer_audit.py::_render_entry).
# Each entry is a `--- decision ---` YAML-like block followed by free-form
# reasoning, terminated by the next `--- decision ---` header or EOF:
#
#   --- decision ---
#   timestamp: 2026-04-24T06:04:24.872124+00:00
#   proposal_id: eefef827-4cb8-4d43-9b1e-f97999feaee2
#   action_type: trading.submit_order
#   decision: defer
#   reviewer_identity: ai:reviewer-sonnet-v5
#   reversibility: reversible
#   outcome: pending_human
#   ---
#   <free-form reasoning body, may span multiple paragraphs>
#
# Tolerant: as long as the timestamp + decision parse, missing optional
# fields leave that field empty; the entry is still counted.

_BLOCK_OPEN = "--- decision ---"
_BLOCK_CLOSE = "---"

_FIELD_LINE_RE = re.compile(
    r"^(?P<key>[a-z_][a-z0-9_]*)\s*:\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)


def _parse_decisions_md(content: str) -> list[dict]:
    if not content:
        return []

    entries: list[dict] = []
    # Split into blocks by _BLOCK_OPEN marker. Skip the preamble (first chunk
    # before any opener).
    chunks = content.split(_BLOCK_OPEN)
    for chunk in chunks[1:]:
        entry = _parse_block(chunk)
        if entry is not None:
            entries.append(entry)
    return entries


def _parse_block(chunk: str) -> dict | None:
    """Parse a single decision block body (everything after `--- decision ---`).

    The block body is: field-lines, then a `---` line, then reasoning. We
    tolerate the reasoning being absent.
    """
    # Split into header (fields) and body (reasoning) on the first lone
    # `---` line after the field block.
    lines = chunk.split("\n")
    field_lines: list[str] = []
    reasoning_lines: list[str] = []
    in_reasoning = False
    for raw in lines:
        line = raw.rstrip()
        if not in_reasoning:
            if line.strip() == _BLOCK_CLOSE:
                in_reasoning = True
                continue
            field_lines.append(line)
        else:
            reasoning_lines.append(line)

    fields: dict[str, str] = {}
    for line in field_lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = _FIELD_LINE_RE.match(stripped)
        if not m:
            continue
        key = m.group("key").strip().lower()
        value = m.group("value").strip()
        fields[key] = value

    ts_raw = fields.get("timestamp", "")
    if not ts_raw:
        return None
    try:
        ts = datetime.fromisoformat(ts_raw)
    except ValueError:
        return None

    verdict_raw = fields.get("decision", "").lower()
    if verdict_raw not in ("approve", "reject", "defer"):
        return None

    reasoning = "\n".join(reasoning_lines).strip()

    return {
        "ts": ts,
        "proposal_id": fields.get("proposal_id", ""),
        "action_type": fields.get("action_type", ""),
        "verdict": verdict_raw,
        "occupant": fields.get("reviewer_identity", ""),
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# Per-domain outcome totals (thin read — reconciler is authoritative)
# ---------------------------------------------------------------------------

async def _read_domain_outcome_totals(client: Any, user_id: str) -> dict[str, dict]:
    """Read the `events` + rolling windows from each domain's _performance.md
    frontmatter. Returns a dict keyed by domain:
        {domain: {"has_performance_md": bool, "rolling_7d_sum_cents": int|None, ...}}

    Tolerant — missing frontmatter leaves counts absent. Not authoritative;
    the reconciler is. This is read-only for the calibration report.
    """
    # For Phase 4 initial landing, we return an empty mapping — the
    # calibration report does not cross-multiply against outcomes yet
    # (that's the Phase 4.1 refinement where calibration actually aligns
    # verdicts to outcomes per-proposal). This stub makes the data flow
    # explicit and ready to extend.
    return {}


# ---------------------------------------------------------------------------
# Rolling-window aggregation
# ---------------------------------------------------------------------------

def _compute_windows(decisions: list[dict], now: datetime) -> dict[str, dict]:
    """Build per-window aggregates: {window: {occupant: {verdict: count, total: N}}}.

    Windows are inclusive of the last N days from `now`. `now` is the
    calibration-run timestamp (UTC, timezone-aware).
    """
    windows: dict[str, dict] = {}
    for window_name, days in _WINDOW_DAYS.items():
        cutoff = now - timedelta(days=days)
        per_occupant: dict[str, dict[str, int]] = defaultdict(lambda: {v: 0 for v in _VERDICT_CATEGORIES})
        per_occupant_totals: dict[str, int] = defaultdict(int)

        for d in decisions:
            if d["ts"] < cutoff:
                continue
            occupant = d["occupant"] or "(unattributed)"
            verdict = d["verdict"]
            if verdict not in _VERDICT_CATEGORIES:
                continue
            per_occupant[occupant][verdict] += 1
            per_occupant_totals[occupant] += 1

        # Fold in defer-rate derived field
        shaped: dict[str, dict] = {}
        for occupant, counts in per_occupant.items():
            total = per_occupant_totals[occupant]
            defer_rate = (counts["defer"] / total) if total else 0.0
            shaped[occupant] = {
                **counts,
                "total": total,
                "defer_rate": round(defer_rate, 3),
            }
        windows[window_name] = shaped

    return windows


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _render_calibration_md(
    *,
    started_at: datetime,
    windows: dict[str, dict],
    outcome_totals: dict[str, dict],
    decisions_count: int,
) -> str:
    """Render /workspace/review/calibration.md content."""
    frontmatter_lines = ["---", f"last_calibrated_at: {started_at.isoformat(timespec='seconds')}", "windows:"]
    if not any(windows.get(w) for w in _WINDOW_DAYS):
        frontmatter_lines[-1] = "windows: {}"
    else:
        for window_name in _WINDOW_DAYS:
            occupants = windows.get(window_name) or {}
            if not occupants:
                frontmatter_lines.append(f"  {window_name}: {{}}")
                continue
            frontmatter_lines.append(f"  {window_name}:")
            frontmatter_lines.append("    by_occupant:")
            for occupant in sorted(occupants.keys()):
                stats = occupants[occupant]
                frontmatter_lines.append(f"      \"{occupant}\":")
                frontmatter_lines.append(f"        total_verdicts: {stats['total']}")
                frontmatter_lines.append(f"        approvals: {stats['approve']}")
                frontmatter_lines.append(f"        rejections: {stats['reject']}")
                frontmatter_lines.append(f"        defers: {stats['defer']}")
                frontmatter_lines.append(f"        defer_rate: {stats['defer_rate']}")
    frontmatter_lines.append("---")

    body_lines = [
        "",
        "# Review Seat — Calibration",
        "",
        "Auto-generated by `back-office-reviewer-calibration` (ADR-211 D6).",
        "Do not edit manually — edits are overwritten on the next calibration cycle.",
        "",
        "This file cross-references the Reviewer seat's verdict trail",
        "(`decisions.md`) against reconciled outcomes per domain",
        "(`_performance.md`), producing rolling-window summaries per",
        "occupant × verdict category. It closes the money-truth → future-",
        "judgment loop per FOUNDATIONS Axiom 7 (Recursion) + Axiom 8",
        "(Money-Truth).",
        "",
        f"**Decisions parsed**: {decisions_count}",
        f"**Last calibrated at**: {started_at.isoformat(timespec='seconds')}",
        "",
    ]

    if decisions_count == 0:
        body_lines += [
            "## No decisions yet",
            "",
            "The Reviewer seat has not rendered any verdicts yet. Calibration",
            "will populate after the first verdict lands in `decisions.md`.",
        ]
    else:
        for window_name, days in _WINDOW_DAYS.items():
            body_lines += ["", f"## Last {days} days", ""]
            occupants = windows.get(window_name) or {}
            if not occupants:
                body_lines.append("_No verdicts in this window._")
                continue
            for occupant in sorted(occupants.keys()):
                stats = occupants[occupant]
                body_lines.append(f"### `{occupant}`")
                body_lines.append("")
                body_lines.append(f"- Total verdicts: {stats['total']}")
                body_lines.append(f"- Approvals: {stats['approve']}")
                body_lines.append(f"- Rejections: {stats['reject']}")
                body_lines.append(f"- Defers: {stats['defer']}")
                body_lines.append(f"- Defer rate: {stats['defer_rate']:.1%}")
                body_lines.append("")

    body_lines += [
        "",
        "## Notes",
        "",
        "- Phase 4 (ADR-211) initial calibration counts verdicts per occupant",
        "  per rolling window. Phase 4.1 / later will add per-proposal",
        "  verdict-vs-outcome correlation once the decisions↔outcomes join",
        "  is wired against `_performance.md` per-proposal provenance.",
        "- Rolling windows are UTC-aligned ending at the calibration",
        "  run timestamp above.",
    ]

    return "\n".join(frontmatter_lines + body_lines) + "\n"


def _render_report(
    *,
    started_at: datetime,
    decisions_count: int,
    occupants: list[str],
    windows: dict[str, dict],
) -> str:
    """Back-office executor report shape (markdown)."""
    lines = [
        "# Reviewer Calibration Report",
        "",
        f"**Ran**: {started_at.isoformat(timespec='seconds')}",
        f"**Decisions parsed**: {decisions_count}",
        f"**Occupants seen**: {len(occupants)}",
    ]
    if occupants:
        lines.append("")
        for occ in occupants:
            lines.append(f"- `{occ}`")
    lines += [
        "",
        "## Window summary (last 30 days)",
        "",
    ]
    occs_30 = windows.get("rolling_30d") or {}
    if not occs_30:
        lines.append("_No verdicts in last 30 days._")
    else:
        for occ in sorted(occs_30.keys()):
            stats = occs_30[occ]
            lines.append(
                f"- `{occ}`: {stats['total']} verdicts "
                f"(approve={stats['approve']}, reject={stats['reject']}, "
                f"defer={stats['defer']}, defer_rate={stats['defer_rate']:.1%})"
            )
    return "\n".join(lines) + "\n"
