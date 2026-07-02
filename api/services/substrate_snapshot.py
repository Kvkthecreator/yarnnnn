"""The substrate-snapshot — the `gitStatus`-analogue for the wake envelope.

ENVELOPE COLLAPSE (docs/analysis/the-envelope-collapse-2026-06-24.md, the
parallel deliverable to ADR-360's wake collapse).

Claude Code's entire standing context is three things (`src_claudeCC/context.ts`):
`claudeMd` (the authored governing file), `gitStatus` (a curated snapshot of
substrate state, stamped "will not update during the conversation"), and
`currentDate`. Everything else the agent reads on demand through tools.

`gitStatus` is the **scoping organ** — branch + dirty paths (`git status --short`)
+ recent commits (`git log --oneline -n 5`), capped, a pointer to *where the
truth lives* without dumping the repo. It is the load-bearing replacement for the
absent scoping-principal: in CC the user message scopes the read; in YARNNN's
absence-by-design the agent needs *something* that says "these paths moved — read
the ones your ask touches," or it judges blind on partial substrate.

This module builds the YARNNN-shaped analogue: a curated delta of authored
substrate, not a dump. Four heads (mirroring gitStatus's four lines):

  1. What changed since your last wake — recent `workspace_file_versions`
     (path — authored_by — message), capped + truncated like CC's 2k status.
     The `git status --short` + `git log` analogue. The core scoping signal.
  2. Pulse head — declared cadence + last fires (folds in _schedule_index +
     _recent_execution mirror heads). Full mirror is on-demand ReadFile.
  3. Ground-truth head — the by-signal/outcome summary head (NOT the body).
     The closest YARNNN has to "the state of the world the judgment is about".
  4. Calibration head — where cadence stands vs ground truth (the ⚠ hints).

Each is a HEAD/POINTER, never a body — enough to scope the read, never the full
content. Target: ~10-20 lines total, like gitStatus, vs the current multi-hundred-
line mirror dumps in _build_user_message.

**Derived Principle 19 (the kernel does not compute for the prompt):** this is a
substrate READ, not LLM-time derivation. The "what changed" line is one indexed
query on `workspace_file_versions` (ADR-209). The mirror heads are the first lines
of files already written mechanically per scheduler tick (`kernel_mirrors.py`).
The ground-truth head is the head of the already-envelope-loaded `ground_truth_md`
value (no re-query). Nothing new is derived at assembly time.

Seeded by `working_memory._get_recent_authorship_sync` (which already groups
recent revisions by authored_by layer); this extends it to carry PATHS so the
agent knows *what to read*, scoped since the prior wake.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Cap the "what changed" list — gitStatus truncates at 2k chars; we cap at N
# recent revisions, the head of the change-stream. Full history is on-demand
# via ListRevisions/ListFiles(since=...).
_MAX_CHANGED = 15
# Per-line truncation for commit messages (gitStatus truncates the whole status).
_MSG_TRUNC = 80
# Head-line cap for mirror/ground-truth heads — the first meaningful lines only.
_HEAD_LINES = 4


def _head(content: str, n: int = _HEAD_LINES) -> str:
    """Return the first n non-blank, non-frontmatter lines of a file body.

    The HEAD discipline: enough to scope, never the body. Skips a leading
    YAML frontmatter block (--- ... ---) so the head is the actual content
    summary, not the machine fields.
    """
    if not content or not content.strip():
        return ""
    lines = content.splitlines()
    # Skip a leading frontmatter block.
    if lines and lines[0].strip() == "---":
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
            lines = lines[end + 1 :]
        except StopIteration:
            pass
    out: list[str] = []
    for ln in lines:
        if ln.strip():
            out.append(ln.rstrip())
        if len(out) >= n:
            break
    return "\n".join(out)


def _pending_proposals(client: Any, user_id: str, limit: int = 8) -> list[dict]:
    """Pending action_proposals — one indexed query, bounded (ADR-400).

    The duplicate-work signal: a decided-and-queued proposal means the agent
    must not re-derive the same act while the operator's witness is pending.
    """
    try:
        res = (
            client.table("action_proposals")
            .select("primitive, inputs")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception:  # noqa: BLE001 — snapshot is best-effort, never raises
        return []


def _changed_since(
    client: Any, user_id: str, since_iso: Optional[str]
) -> list[dict]:
    """Recent substrate revisions since `since_iso` (or last 24h fallback).

    Returns [{path, authored_by, message, created_at}] most-recent-first,
    capped at _MAX_CHANGED. The `git status --short` + `git log` analogue —
    the scoping signal that tells the agent WHAT MOVED.
    """
    if not since_iso:
        since_iso = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    try:
        res = (
            client.table("workspace_file_versions")
            .select("path, authored_by, message, created_at")
            .eq("user_id", user_id)
            .gte("created_at", since_iso)
            .order("created_at", desc=True)
            .limit(_MAX_CHANGED)
            .execute()
        )
        return res.data or []
    except Exception as exc:
        logger.warning(
            "[SUBSTRATE_SNAPSHOT] changed-since query failed for user=%s: %s",
            user_id[:8], exc,
        )
        return []


def build_substrate_snapshot(
    client: Any,
    user_id: str,
    *,
    since_iso: Optional[str] = None,
    schedule_index_md: str = "",
    recent_execution_md: str = "",
    calibration_md: str = "",
    ground_truth_md: str = "",
) -> str:
    """Assemble the substrate-snapshot — the gitStatus-analogue.

    Reads the already-loaded mirror/ground-truth values (passed by the envelope
    helper to avoid re-query) and runs ONE indexed query for "what changed".
    Returns a compact markdown block (~10-20 lines) or "" when the workspace
    is brand-new and nothing has happened yet.

    The four heads — each a pointer, never a body. The agent ReadFiles the full
    mirror / ground-truth / changed file when its judgment needs the detail.

    Args mirror the envelope keys so the caller passes what it already loaded:
    no double-read of the mirror files (DP19 — substrate read, not recompute).
    """
    parts: list[str] = [
        "## Substrate snapshot (a pointer to where the truth lives — read on "
        "demand for detail)",
        "",
        "_This is a snapshot of substrate state at wake time. For any file's full "
        "content, ReadFile it — do not reason from this head alone where the "
        "judgment needs the body._",
        "",
    ]

    # 1. What changed since your last wake (the core scoping signal).
    changed = _changed_since(client, user_id, since_iso)
    if changed:
        parts.append("**What changed since your last wake** (most recent first):")
        for row in changed:
            path = (row.get("path") or "").replace("/workspace/", "")
            author = (row.get("authored_by") or "?").strip()
            msg = (row.get("message") or "").strip().replace("\n", " ")
            if len(msg) > _MSG_TRUNC:
                msg = msg[:_MSG_TRUNC] + "…"
            line = f"- `{path}` — {author}"
            if msg:
                line += f": {msg}"
            parts.append(line)
        parts.append("")
    else:
        parts.append(
            "**What changed since your last wake**: nothing recorded "
            "(new workspace, or quiet since last wake).")
        parts.append("")

    # 1b. Pending proposals (ADR-400 / the rung-2 residual): work already
    # decided and waiting for the operator's witness — so the agent does NOT
    # re-derive a placement whose proposal already sits in the queue.
    pending = _pending_proposals(client, user_id)
    if pending:
        parts.append("**Pending proposals** (decided, awaiting operator approval "
                     "— do NOT re-do this work):")
        for row in pending:
            prim = row.get("primitive") or "?"
            path = ""
            inputs = row.get("inputs") or {}
            if isinstance(inputs, dict):
                path = inputs.get("path") or inputs.get("slug") or ""
            line = f"- {prim}"
            if path:
                line += f" → `{path}`"
            parts.append(line)
        parts.append("")

    # 2. Pulse head (declared cadence + last fires).
    pulse_head = _head(schedule_index_md, 3)
    fires_head = _head(recent_execution_md, 3)
    if pulse_head or fires_head:
        parts.append("**Pulse** (head — full in `system/_schedule_index.md` + "
                     "`system/_recent_execution.md`):")
        if pulse_head:
            parts.append(pulse_head)
        if fires_head:
            parts.append(fires_head)
        parts.append("")

    # 3. Ground-truth head (the state of the world the judgment is about).
    gt_head = _head(ground_truth_md, _HEAD_LINES)
    if gt_head:
        parts.append("**Ground-truth** (head — full track record on demand):")
        parts.append(gt_head)
        parts.append("")

    # 4. Calibration head (cadence vs ground truth).
    cal_head = _head(calibration_md, _HEAD_LINES)
    if cal_head:
        parts.append("**Calibration** (head — full in `system/_calibration.md`):")
        parts.append(cal_head)
        parts.append("")

    # Only emit a meaningful snapshot — if literally nothing populated, return ""
    # so the envelope skips the header (a brand-new workspace pre-anything).
    body = "\n".join(parts).strip()
    # The minimal block is just the 4-line header + the "nothing changed" line —
    # if that's all there is, it's still worth showing (it tells the agent the
    # world is quiet, which is a real signal, like gitStatus showing "(clean)").
    return body


__all__ = ["build_substrate_snapshot"]
