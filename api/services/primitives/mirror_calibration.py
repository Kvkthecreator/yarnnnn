"""
MirrorCalibration Primitive — ADR-327 D6 (the self-improving loop).

Projects calibration evidence into a compact substrate file the Reviewer
reads before reasoning about cadence. This is the mechanism that turns
"the Reviewer *may* re-author its cadence" into "the Reviewer is *driven*
to": it correlates the Reviewer's cadence-authoring history (every Schedule
call against `_recurrences.yaml`, attributed per ADR-209) against outcome
quality (per-slug fire results in execution_events + the program-declared
ground-truth file).

The pre-ADR-327 gap: the Reviewer had the *authority* to improve its cadence
(Derived Principle 18) but nothing *drove* it to, and nothing *measured*
whether it did. Self-improvement happened only when the LLM happened to
choose it. ADR-327 D6 puts the calibration evidence in the wake envelope so
the Reviewer reasons from substrate.

Kernel-universal, program-parameterized (ADR-327 D6): the machinery here is
written once; the *inputs* (which ground-truth file) come from the active
bundle's `substrate_abi.ground_truth` declaration. A new program declares
its ground-truth file and inherits the loop — no per-program code.

Respects FOUNDATIONS Derived Principle 19 (the kernel does not compute for
the prompt): the correlation is written to substrate first, then read like
any other envelope file — not computed at prompt-assembly time.

Surface:
  MirrorCalibration(diff_aware: bool = True, window_days: int = 14)

Behavior:
  1. Read the Reviewer's cadence-authoring history from
     `workspace_file_versions` for `_recurrences.yaml` (reviewer:* authored
     revisions in the window).
  2. For each judgment recurrence currently declared, read its recent fire
     outcomes from execution_events (fires, failures, proposals-emitted as a
     proxy for "produced value").
  3. Read a compact head of the program-declared ground-truth file (if any).
  4. Compose evidence: per-slug "N fires, M produced value" lines + the
     cadence-authoring trail + ground-truth head. The Reviewer judges what
     it means — the mirror states evidence, not verdicts.
  5. Diff-aware: skip write when content unchanged (excluding `as_of:`).
  6. Write via write_revision() with authored_by="system:mirror-calibration".

Dispatch surface:
  Kernel maintenance phase only — called per scheduler tick from
  unified_scheduler.py via services.kernel_mirrors. NOT in
  CHAT/HEADLESS/FREDDIE_PRIMITIVES.
"""

from __future__ import annotations

import logging
import re as _re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from services.workspace_paths import SYSTEM_CALIBRATION_PATH

logger = logging.getLogger(__name__)


def _strip_as_of(s: str) -> str:
    return _re.sub(r"^as_of:.*$", "as_of: <ts>", s, count=1, flags=_re.MULTILINE)


def _fmt_ts(iso: str) -> str:
    try:
        dt = datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return iso or "?"


def _parse_ground_truth_segments(content: str) -> tuple[dict, dict]:
    """Extract attestation mix + retrospective segment from ground-truth JSON
    frontmatter (ADR-330 D2 + D3). Returns (by_attestation, retrospective).

    The ground-truth file's frontmatter is a single JSON object (per the
    ledger's _render_money_truth_file). We parse only the two fields the
    calibration mirror needs to label segments; everything else is ignored.
    Tolerant: returns ({}, {}) on any parse failure — the mirror degrades to
    head-only presentation, never raises.
    """
    if not content or not content.strip().startswith("---"):
        return {}, {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, {}
    import json
    try:
        data = json.loads(parts[1].strip())
    except Exception:
        return {}, {}
    if not isinstance(data, dict):
        return {}, {}
    by_attestation = data.get("by_attestation") or {}
    retrospective = data.get("retrospective") or {}
    return (
        by_attestation if isinstance(by_attestation, dict) else {},
        retrospective if isinstance(retrospective, dict) else {},
    )


async def handle_mirror_calibration(auth: Any, input: dict) -> dict:
    """Execute MirrorCalibration (ADR-327 D6).

    Inputs:
      diff_aware: bool — default True
      window_days: int — default 14; lookback for cadence history + fires

    Returns:
      {success, paths_written, paths_skipped, slugs_correlated, error?}
    """
    diff_aware = input.get("diff_aware", True)
    window_days = input.get("window_days", 14)
    if not isinstance(window_days, int) or window_days < 1:
        window_days = 14

    client = getattr(auth, "client", None)
    user_id = getattr(auth, "user_id", None)
    if client is None or not user_id:
        return {
            "success": False, "paths_written": [], "paths_skipped": [],
            "slugs_correlated": 0, "error": "missing auth context",
        }

    output_path = f"/workspace/{SYSTEM_CALIBRATION_PATH}"
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    cutoff_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- 1. Cadence-authoring history (workspace_file_versions for _recurrences.yaml) ---
    from services.conventions import RECURRENCES_PATH
    cadence_edits: list[dict] = []
    try:
        res = (
            client.table("workspace_file_versions")
            .select("created_at, authored_by, message")
            .eq("user_id", user_id)
            .eq("path", RECURRENCES_PATH)
            .gte("created_at", cutoff_iso)
            .order("created_at", desc=True)
            .limit(30)
            .execute()
        )
        cadence_edits = res.data or []
    except Exception as exc:
        logger.warning("[MIRROR_CALIBRATION] cadence-history query failed for %s: %s", user_id[:8], exc)

    # --- 2. Current judgment recurrences + their recent fire outcomes ---
    from services.recurrence import walk_workspace_recurrences
    judgment_slugs: list[str] = []
    try:
        recs = walk_workspace_recurrences(client, user_id)
        judgment_slugs = [
            r.slug for r in recs
            if getattr(r, "mode", "judgment") == "judgment" and r.slug
        ]
    except Exception as exc:
        logger.warning("[MIRROR_CALIBRATION] recurrence walk failed for %s: %s", user_id[:8], exc)

    per_slug: list[dict] = []
    for slug in judgment_slugs:
        try:
            ev = (
                client.table("execution_events")
                .select("status, funnel_decision, created_at")
                .eq("user_id", user_id)
                .eq("slug", slug)
                .gte("created_at", cutoff_iso)
                .order("created_at", desc=True)
                .limit(50)
                .execute()
            )
            rows = ev.data or []
        except Exception:
            rows = []
        fires = len(rows)
        escalations = sum(1 for r in rows if r.get("funnel_decision") == "escalate")
        failures = sum(1 for r in rows if r.get("status") not in ("success", None))
        last_iso = _fmt_ts(rows[0]["created_at"]) if rows else None
        per_slug.append({
            "slug": slug, "fires": fires, "escalations": escalations,
            "failures": failures, "last": last_iso,
        })

    # --- 3. Proposal correlation (proxy for "produced value") ---
    # Per-slug proposal emission is the cleanest cross-program "did this wake
    # produce a consequential output" signal available without program code.
    proposals_by_slug: dict[str, int] = {}
    try:
        pr = (
            client.table("action_proposals")
            .select("task_slug, created_at")
            .eq("user_id", user_id)
            .gte("created_at", cutoff_iso)
            .limit(200)
            .execute()
        )
        for row in (pr.data or []):
            s = row.get("task_slug")
            if s:
                proposals_by_slug[s] = proposals_by_slug.get(s, 0) + 1
    except Exception:
        pass  # action_proposals may not exist in all workspaces; degrade gracefully

    # --- 4. Ground-truth file head (program-declared) ---
    ground_truth_path: Optional[str] = None
    ground_truth_head: str = ""
    ground_truth_attestation: dict = {}
    ground_truth_segment: dict = {}
    try:
        from services.bundle_reader import get_ground_truth_for_workspace
        ground_truth_path = get_ground_truth_for_workspace(user_id, client)
        if ground_truth_path:
            gt = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", f"/workspace/{ground_truth_path}")
                .limit(1)
                .execute()
            )
            content = (gt.data or [{}])[0].get("content") or ""
            # ADR-330 D2 + D3: parse the ground-truth frontmatter so the
            # calibration mirror can surface attestation mix + the segmented
            # backfill count as LABELED lines — not a raw JSON dump. An
            # agent-asserted row must never read as an independent platform
            # fill; a backfill dump must never read as live performance.
            ground_truth_attestation, ground_truth_segment = _parse_ground_truth_segments(content)
            # Body head only (skip the JSON frontmatter so the head is the
            # narrative, not raw machine state) — pointer + freshness signal,
            # not a duplication. The Reviewer reads the full file on demand.
            body = content.split("---", 2)[-1] if content.startswith("---") else content
            ground_truth_head = "\n".join(body.strip().splitlines()[:20]).strip()
    except Exception as exc:
        logger.warning("[MIRROR_CALIBRATION] ground-truth read failed for %s: %s", user_id[:8], exc)

    # --- 5. Compose evidence ---
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    frontmatter = (
        f"---\n"
        f"as_of: {now_iso}\n"
        f"window: {window_days}d\n"
        f"judgment_slugs: {len(judgment_slugs)}\n"
        f"cadence_edits: {len(cadence_edits)}\n"
        f"---\n\n"
    )

    lines: list[str] = [
        "# Calibration — cadence vs. ground truth (ADR-327 D6)",
        "",
        "_Evidence for your self-improving loop. Read this before reasoning",
        "about cadence. Where your cadence choices are falsified by ground",
        "truth — fires that produced no value, recurrences never escalating —",
        "re-author. This file states evidence; you render the judgment._",
        "",
        f"## Per-recurrence outcomes (last {window_days}d)",
        "",
    ]
    if per_slug:
        for s in per_slug:
            produced = proposals_by_slug.get(s["slug"], 0)
            verdict_hint = ""
            if s["fires"] >= 3 and produced == 0 and s["escalations"] >= 3:
                verdict_hint = "  ⚠ fired+escalated repeatedly, produced no proposals — cadence or signal may be miscalibrated"
            elif s["fires"] == 0:
                verdict_hint = "  ⚠ zero fires in window — paused, mis-scheduled, or stale"
            elif s["failures"] >= 2:
                verdict_hint = f"  ⚠ {s['failures']} failures — investigate"
            lines.append(
                f"- **{s['slug']}**: {s['fires']} fires · {s['escalations']} escalated · "
                f"{produced} proposal(s) · {s['failures']} failure(s)"
                + (f" · last {s['last']}" if s["last"] else "")
                + verdict_hint
            )
    else:
        lines.append("_(no judgment recurrences declared)_")

    lines += ["", "## Your cadence-authoring trail", ""]
    reviewer_edits = [e for e in cadence_edits if str(e.get("authored_by", "")).startswith("freddie:")]
    if reviewer_edits:
        for e in reviewer_edits[:10]:
            lines.append(
                f"- {_fmt_ts(e.get('created_at',''))} · {e.get('authored_by','?')} · "
                f"{(e.get('message') or '').strip()[:100]}"
            )
    else:
        lines.append("_(you have not authored any cadence changes in this window —")
        lines.append("the bundle scaffold is still your operating rhythm; refine when evidence warrants)_")

    if ground_truth_path:
        lines += ["", f"## Ground truth — `{ground_truth_path}` (head; read full on demand)", ""]

        # ADR-330 D2: attestation mix — how much of this evidence is
        # independently verified vs operator-imported vs agent-asserted.
        # The Reviewer must weigh operator/agent-attested rows differently
        # from platform fills; surfacing the mix here keeps that honest.
        if ground_truth_attestation:
            att_parts = [
                f"{level} {ground_truth_attestation[level]}"
                for level in ("platform", "operator", "agent")
                if ground_truth_attestation.get(level)
            ]
            if att_parts:
                lines.append(f"**Attestation mix:** {' · '.join(att_parts)}")
                if ground_truth_attestation.get("agent"):
                    lines.append(
                        "  ⚠ agent-attested rows present — corroboration-seeking "
                        "evidence, not independent verification (ADR-330 §3)"
                    )

        # ADR-330 D3: segmented backfill — pre-YARNNN history kept OUT of the
        # live loop. Label it so the Reviewer never reads backfill as recent
        # performance.
        retro_count = ((ground_truth_segment or {}).get("totals") or {}).get(
            "reconciled_event_count", 0
        ) or 0
        if retro_count > 0:
            lines.append(
                f"**Backfilled history:** {retro_count} segmented row(s) — "
                f"pre-YARNNN, NOT in the live windows above"
            )
        if ground_truth_attestation or retro_count > 0:
            lines.append("")

        if ground_truth_head:
            lines.append("```")
            lines.append(ground_truth_head)
            lines.append("```")
        else:
            lines.append("_(ground-truth file empty or absent — no outcome basis yet)_")

    summary = frontmatter + "\n".join(lines) + "\n"

    # --- 6. Diff-aware skip ---
    if diff_aware:
        try:
            existing = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", output_path)
                .limit(1)
                .execute()
            )
            prior = (existing.data or [{}])[0].get("content") or ""
            if _strip_as_of(prior) == _strip_as_of(summary):
                return {
                    "success": True, "paths_written": [], "paths_skipped": [output_path],
                    "slugs_correlated": len(per_slug), "error": None,
                }
        except Exception:
            pass

    # --- 7. Write via Authored Substrate (ADR-209) ---
    try:
        from services.authored_substrate import write_revision
        write_revision(
            client,
            user_id=user_id,
            path=output_path,
            content=summary,
            authored_by="system:mirror-calibration",
            message=f"calibration: {len(per_slug)} slug(s), {len(reviewer_edits)} cadence edit(s)",
            summary="Calibration evidence substrate (ADR-327 D6 — self-improving loop)",
            tags=["pulse", "calibration", "adr-327"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return {
            "success": True, "paths_written": [output_path], "paths_skipped": [],
            "slugs_correlated": len(per_slug), "error": None,
        }
    except Exception as exc:
        logger.warning("[MIRROR_CALIBRATION] write failed for %s: %s", user_id[:8], exc)
        return {
            "success": False, "paths_written": [], "paths_skipped": [],
            "slugs_correlated": len(per_slug), "error": f"write failed: {exc}",
        }
