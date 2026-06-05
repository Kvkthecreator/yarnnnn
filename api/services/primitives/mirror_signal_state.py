"""
MirrorSignalState Primitive — ADR-281

A mechanical-recurrence-friendly primitive that mirrors per-signal state
files into a compact substrate summary. Established by ADR-281 D3 to
honor FOUNDATIONS Derived Principle 19 ("The kernel does not compute for
the prompt"): substrate-derivative state must be written by mechanical
primitives, not summarized at LLM-prompt-assembly time.

The pattern: bundle ships per-signal YAML state files (e.g. one file per
signal slug under `context/{domain}/signals/`). The Reviewer doesn't
need the full content of every signal at every wake — it needs a compact
"what state is each signal in, did any fire today" summary for capital-EV
reasoning. Pre-ADR-281, this summary was computed at LLM-prompt-assembly
time via an `ENVELOPE_SUMMARIZERS["signal_files"]` kernel function — an
Axiom 1 violation (state produced without substrate write). Post-ADR-281,
a mechanical-mode recurrence invokes this primitive at known cadence; the
primitive writes the compact summary to a substrate file; the Reviewer's
wake envelope reads that substrate file like every other path entry.

Surface:
  MirrorSignalState(
      source: str,         # glob pattern, workspace-relative
                           # (e.g. "operation/trading/signals/*.yaml")
      write_to: str,       # output substrate path, workspace-relative
                           # (e.g. "operation/trading/_signals_summary.md")
      diff_aware: bool = True,
  )

Behavior:
  1. Glob-list workspace files matching `source` pattern.
  2. For each file, extract `state:` and `triggered_today:` via regex on
     the raw YAML text (signal yaml files have stable shape; regex is
     fast + tolerant of formatting variation).
  3. Compose a compact one-line-per-signal summary string.
  4. If `diff_aware` and the composed summary matches the prior revision
     of `write_to`, skip the write (no revision noise).
  5. Otherwise write via `write_revision()` with
     `authored_by="system:mirror-signal-state"` per ADR-209 §D8.

Returns: {success, paths_written, paths_skipped, signals_processed, error?}

Dispatch surfaces:
  - Mechanical recurrence: dispatched by `invocation_dispatcher` when a
    `mechanical`-mode recurrence's prompt names
    `@primitive: MirrorSignalState(source=..., write_to=...)` per ADR-263
    D5 + ADR-281 D3.
  - NOT in CHAT_PRIMITIVES, NOT in HEADLESS_PRIMITIVES, NOT in
    REVIEWER_PRIMITIVES per ADR-281: operators and LLMs don't invoke
    directly; the primitive is purely the mechanical mirror.

This primitive does ONE job: project per-signal substrate into a compact
substrate summary. It does not evaluate signals against market conditions
(that's the alpha-trader bundle's separate `signal-evaluation` recurrence)
or invoke the Reviewer (the recurrence's `mode=mechanical` keeps the
Reviewer asleep).
"""

from __future__ import annotations

import logging
import re as _re
from typing import Any

logger = logging.getLogger(__name__)


# No LLM tool definition (no LLM dispatch surface — this primitive is
# mechanical-only per ADR-281). The dispatcher routes by name through
# HANDLERS; the handler signature matches the standard primitive shape
# (auth, input: dict) -> dict.


async def handle_mirror_signal_state(auth: Any, input: dict) -> dict:
    """Execute MirrorSignalState primitive (ADR-281).

    Inputs:
      source: str — glob pattern, workspace-relative
                    (e.g. "operation/trading/signals/*.yaml")
      write_to: str — output substrate path, workspace-relative
                      (e.g. "operation/trading/_signals_summary.md")
      diff_aware: bool — default True; skip write when content unchanged

    Returns:
      {
        "success": bool,
        "paths_written": list[str],
        "paths_skipped": list[str],     # diff-aware skips
        "signals_processed": int,
        "error": str | None,
      }
    """
    source = input.get("source") or input.get("source_glob")
    write_to = input.get("write_to") or input.get("output")
    diff_aware = input.get("diff_aware", True)

    if not isinstance(source, str) or not source:
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "signals_processed": 0,
            "error": "missing required arg `source` (glob pattern)",
        }
    if not isinstance(write_to, str) or not write_to:
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "signals_processed": 0,
            "error": "missing required arg `write_to` (output substrate path)",
        }

    # Normalize patterns: PostgREST `like` uses `%`; bundle declarations use `*`.
    sql_pattern = source.replace("*", "%")
    if not sql_pattern.startswith("/workspace/"):
        sql_pattern = f"/workspace/{sql_pattern.lstrip('/')}"

    output_path = write_to
    if not output_path.startswith("/workspace/"):
        output_path = f"/workspace/{output_path.lstrip('/')}"

    client = getattr(auth, "client", None)
    user_id = getattr(auth, "user_id", None)
    if client is None or not user_id:
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "signals_processed": 0,
            "error": "missing auth context (client or user_id)",
        }

    try:
        result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", sql_pattern)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "[MIRROR_SIGNAL_STATE] glob query failed for user=%s pattern=%s: %s",
            user_id[:8], sql_pattern, exc,
        )
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "signals_processed": 0,
            "error": f"glob query failed: {exc}",
        }

    # Compose the compact summary deterministically.
    lines = []
    for row in result.data or []:
        path = row.get("path", "")
        content = row.get("content", "")
        slug = path.split("/")[-1].replace(".yaml", "")
        triggered_m = _re.search(r"triggered_today:\s*(\[.*?\])", content)
        state_m = _re.search(r"state:\s*(\S+)", content)
        lines.append(
            f"- {slug}: state={state_m.group(1) if state_m else '?'} "
            f"triggered={triggered_m.group(1) if triggered_m else '[]'}"
        )

    if lines:
        summary = "# Signals Summary\n\n" + "\n".join(lines) + "\n"
    else:
        summary = "# Signals Summary\n\n_(no signal state files found)_\n"

    # Diff-aware check: skip if content matches prior revision.
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
            prior_content = (existing.data or [{}])[0].get("content") or ""
            if prior_content == summary:
                return {
                    "success": True,
                    "paths_written": [],
                    "paths_skipped": [output_path],
                    "signals_processed": len(lines),
                    "error": None,
                }
        except Exception:
            # Read failure → fall through to write (safer to write than to skip
            # incorrectly).
            pass

    # Write via Authored Substrate per ADR-209.
    try:
        from services.authored_substrate import write_revision

        # write_revision expects workspace-relative path without /workspace/ prefix
        # (matches the bundle MANIFEST + workspace_paths conventions).
        relative_path = output_path
        if relative_path.startswith("/workspace/"):
            relative_path = relative_path[len("/workspace/"):]

        write_revision(
            client,
            user_id=user_id,
            path=output_path,  # write_revision accepts full /workspace/... paths
            content=summary,
            authored_by="system:mirror-signal-state",
            message=f"mirrored {len(lines)} signal(s) → _signals_summary.md",
            summary="Signals summary substrate (ADR-281 derivative-compaction)",
            tags=["signals", "world-mirror", "adr-281"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return {
            "success": True,
            "paths_written": [output_path],
            "paths_skipped": [],
            "signals_processed": len(lines),
            "error": None,
        }
    except Exception as exc:
        logger.warning(
            "[MIRROR_SIGNAL_STATE] write failed for user=%s path=%s: %s",
            user_id[:8], output_path, exc,
        )
        return {
            "success": False,
            "paths_written": [],
            "paths_skipped": [],
            "signals_processed": len(lines),
            "error": f"write failed: {exc}",
        }
