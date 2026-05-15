"""Reviewer wake envelope assembly (ADR-276 + ADR-280 Stream A).

The Reviewer perceives full operator-authored governance substrate +
program-shaped substrate at every wake, regardless of trigger shape
(addressed | reactive). This module is the single canonical assembly
point for that substrate — called by both `routes/feed.py` (addressed
turns) and `services/invocation_dispatcher.py` (reactive turns).

Pre-loading discipline (FOUNDATIONS v8.5 Axiom 4 + Derived Principle 18 +
ADR-275 refinement learning): load-bearing substrate arrives in the wake
envelope, NOT as a prose-named "remember to ReadFile X" side-quest. Run-1
vs run-2 of the ADR-275 e2e empirically validated the structural difference:
the same operator-says-hi prompt produced zero Schedule calls when
`_preferences.yaml` was prose-named, but three Schedule calls when it was
pre-loaded in the envelope.

ADR-280 Stream A: program-shaped envelope inputs are read from the active
bundle's MANIFEST `substrate_abi.reviewer_wake_envelope` declaration via
`services.bundle_reader.get_substrate_abi_for_workspace`. Universal
envelope inputs (the six operator-authored governance files every
workspace has) remain hardcoded as kernel-universal constants. Adding a
new program requires zero edits to this module — the new bundle declares
its envelope; bundle_reader exposes it; this module reads it.

Singular Implementation: one helper, two callers (feed.py + invocation_dispatcher).

Observability (2026-05-15 hardening):
The helper returns `(envelope_dict, elapsed_ms)` so callers can record
the dominant Reviewer DB-read pattern to `execution_events.envelope_load_ms`
(migration 175). Reactive callers route the elapsed ms through telemetry;
addressed callers log it to the structured logger.
"""

from __future__ import annotations

import asyncio as _asyncio
import logging
import re as _re
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from services.workspace_paths import (
    REVIEW_IDENTITY_PATH,
    REVIEW_PRINCIPLES_PATH,
    SHARED_PRECEDENT_PATH,
    SHARED_MANDATE_PATH,
    SHARED_AUTONOMY_PATH,
    SHARED_PREFERENCES_PATH,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Universal envelope inputs (kernel-shipped — present in every workspace)
# ---------------------------------------------------------------------------
# Per ADR-280 §D5 the kernel ships the universal "how" envelope; bundles
# declare their program-shaped additions via MANIFEST `substrate_abi.reviewer_wake_envelope`.
# This list is the kernel side. Each entry: (key, workspace-relative-path).

_UNIVERSAL_ENVELOPE_DECLS: list[tuple[str, str]] = [
    ("identity_md", REVIEW_IDENTITY_PATH),
    ("principles_md", REVIEW_PRINCIPLES_PATH),
    ("precedent_md", SHARED_PRECEDENT_PATH),
    ("mandate_md", SHARED_MANDATE_PATH),
    ("autonomy_md", SHARED_AUTONOMY_PATH),
    ("preferences_yaml", SHARED_PREFERENCES_PATH),
]


# ---------------------------------------------------------------------------
# Summarizer registry (kernel-implemented, bundle-referenced by name)
# ---------------------------------------------------------------------------
# Per ADR-280 §D5.b: bundles reference summarizers by name in their
# substrate_abi.reviewer_wake_envelope path_glob declarations; the kernel
# hosts the implementations. Bundles cannot ship arbitrary summarizer
# code (security + kernel/program boundary). Adding a new summarizer
# kind requires its own ADR (rare event).
#
# Signature contract: `async (client, user_id, path_glob) -> str` (compact
# string surfaced in the envelope under the declaration's `key`).
#
# Today there is exactly one summarizer; future summarizer kinds (per-customer
# profile compaction for alpha-commerce, per-position compaction for
# portfolio reconciliation) graduate via ADR.

SummarizerFn = Callable[[Any, str, str], Awaitable[str]]


async def _summarize_signal_files(client: Any, user_id: str, path_glob: str) -> str:
    """Read all signal state YAML files matching `path_glob` and return compact summary.

    Per-signal one-line summary: `- {slug}: state={state} triggered={triggered_today}`.
    Empty case returns the literal `_(no signal state files found)_`.

    Two regex extracts (`triggered_today:` + `state:`) against raw YAML text
    rather than yaml.safe_load — these signal YAML files have stable shape;
    regex is faster + less brittle to formatting variation. The Reviewer
    receives a compact compact-index-friendly string rather than full
    per-file content (each signal file is ~40-80 lines of declared signal
    logic the Reviewer doesn't need to re-read every wake).

    Relocated from `agents/reviewer_agent.py::read_signal_files` per ADR-280
    Stream A — this is kernel-internal envelope-summarizer infrastructure,
    not a Reviewer-facing primitive. Made path_glob-parametric so bundles
    can reference it from their substrate_abi declarations.
    """
    # Convert glob pattern to PostgREST `like` pattern: `*` → `%`.
    sql_pattern = path_glob.replace("*", "%")
    if not sql_pattern.startswith("/workspace/"):
        sql_pattern = f"/workspace/{sql_pattern.lstrip('/')}"
    try:
        result = (
            client.table("workspace_files")
            .select("path, content")
            .eq("user_id", user_id)
            .like("path", sql_pattern)
            .execute()
        )
        lines = []
        for row in result.data or []:
            path = row.get("path", "")
            content = row.get("content", "")
            slug = path.split("/")[-1].replace(".yaml", "")
            triggered = _re.search(r"triggered_today:\s*(\[.*?\])", content)
            state = _re.search(r"state:\s*(\S+)", content)
            lines.append(
                f"- {slug}: state={state.group(1) if state else '?'} "
                f"triggered={triggered.group(1) if triggered else '[]'}"
            )
        return "\n".join(lines) if lines else "_(no signal state files found)_"
    except Exception:
        return "_(signal files unavailable)_"


#: Kernel-side registry mapping summarizer name → implementation. Bundles
#: reference these names in `substrate_abi.reviewer_wake_envelope[*].summarizer`.
ENVELOPE_SUMMARIZERS: dict[str, SummarizerFn] = {
    "signal_files": _summarize_signal_files,
}


# ---------------------------------------------------------------------------
# Envelope assembly
# ---------------------------------------------------------------------------

async def load_reviewer_governance_envelope(
    client: Any, user_id: str
) -> tuple[dict, int]:
    """Assemble the Reviewer's wake envelope substrate.

    Returns `(envelope_dict, elapsed_ms)`:
      - envelope_dict: keyed by `ReviewerContext` field names — drop
        directly into the context bag passed to `invoke_reviewer()`. All
        reads happen in parallel via `asyncio.gather` to minimize
        wake-envelope latency.
      - elapsed_ms: wall-clock ms spent in this call. Callers route it
        to `execution_events.envelope_load_ms` (reactive path) or to the
        structured logger (addressed path) per ADR-276 hardening.

    Universal envelope (always present, kernel-shipped):
      - identity_md          → /workspace/review/IDENTITY.md
      - principles_md        → /workspace/review/principles.md
      - precedent_md         → /workspace/context/_shared/PRECEDENT.md
      - mandate_md           → /workspace/context/_shared/MANDATE.md
      - autonomy_md          → /workspace/context/_shared/AUTONOMY.md
      - preferences_yaml     → /workspace/context/_shared/_preferences.yaml

    Program-shaped envelope (read from active bundle's MANIFEST per ADR-280
    Stream A): whatever `substrate_abi.reviewer_wake_envelope` declares.
    For alpha-trader workspaces today this includes `operator_profile_md`,
    `risk_md`, `performance_md`, `signal_files` (path_glob with summarizer).

    Adding a new program requires zero edits to this function. The new
    bundle declares its envelope; `bundle_reader.get_substrate_abi_for_workspace`
    exposes it; the loop below reads it. All values returned are str (empty
    string when absent — never raises) so the Reviewer's envelope renderer
    (`_build_user_message`) skips absent sections gracefully.
    """
    _started_at = datetime.now(timezone.utc)

    async def _read(path: str) -> str:
        """Read a workspace file by relative path, return '' on miss."""
        full = f"/workspace/{path.lstrip('/')}" if not path.startswith("/workspace/") else path
        try:
            res = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", full)
                .limit(1)
                .execute()
            )
            return (res.data or [{}])[0].get("content") or ""
        except Exception as exc:
            logger.warning(
                "[REVIEWER_ENVELOPE] read failed for user=%s path=%s: %s",
                user_id[:8], path, exc,
            )
            return ""

    # --- Universal reads (kernel-shipped, parallel) ---
    universal_results = await _asyncio.gather(
        *[_read(path) for _, path in _UNIVERSAL_ENVELOPE_DECLS]
    )
    envelope: dict[str, str] = {
        key: value
        for (key, _path), value in zip(_UNIVERSAL_ENVELOPE_DECLS, universal_results)
    }

    # --- Program-shaped reads (from active bundle's substrate_abi) ---
    # Lazy import to avoid circular: bundle_reader imports nothing in this
    # module; this is defensive only.
    from services import bundle_reader

    abi = bundle_reader.get_substrate_abi_for_workspace(user_id, client)
    program_decls = abi.get("reviewer_wake_envelope", []) or []

    # Two declaration shapes (per ADR-280 §D5.b):
    #   {key, path, optional}                    — direct file read
    #   {key, path_glob, summarizer, optional}   — collection via summarizer
    program_tasks: list[Awaitable[str]] = []
    program_keys: list[str] = []
    for decl in program_decls:
        if not isinstance(decl, dict):
            continue
        key = decl.get("key")
        if not key:
            continue
        # Skip duplicates of universal entries — kernel universals win
        # (defensive; bundles shouldn't redeclare universal keys, but if
        # they do the kernel-shipped read is authoritative).
        if key in envelope:
            logger.warning(
                "[REVIEWER_ENVELOPE] bundle envelope key %s collides with "
                "kernel-universal entry; kernel value wins", key,
            )
            continue
        if "path" in decl:
            program_keys.append(key)
            program_tasks.append(_read(decl["path"]))
        elif "path_glob" in decl:
            summarizer_name = decl.get("summarizer")
            summarizer = ENVELOPE_SUMMARIZERS.get(summarizer_name)
            if summarizer is None:
                logger.warning(
                    "[REVIEWER_ENVELOPE] unknown summarizer %r referenced by "
                    "bundle for key %s; skipping", summarizer_name, key,
                )
                continue
            program_keys.append(key)
            program_tasks.append(summarizer(client, user_id, decl["path_glob"]))

    if program_tasks:
        program_results = await _asyncio.gather(*program_tasks)
        for key, value in zip(program_keys, program_results):
            envelope[key] = value

    elapsed_ms = int(
        (datetime.now(timezone.utc) - _started_at).total_seconds() * 1000
    )
    return envelope, elapsed_ms
