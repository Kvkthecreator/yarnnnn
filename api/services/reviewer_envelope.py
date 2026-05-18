"""Reviewer wake envelope assembly (ADR-276 + ADR-281).

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

ADR-281: program-shaped envelope inputs are read from the active bundle's
MANIFEST `substrate_abi.reviewer_wake_envelope` declaration via
`services.bundle_reader.get_substrate_abi_for_workspace`. **One declaration
shape: `{key, path, optional}`.** No `path_glob`, no `summarizer`. Per
Derived Principle 19 ("The kernel does not compute for the prompt") the
envelope helper reads substrate; it does not derive new state at
prompt-assembly time. Substrate that needs compaction (signal-state
summary, customer aggregates, position summaries — any future case) is
written by mechanical-mode recurrences invoking deterministic primitives
that write substrate at known cadence; the envelope reads the resulting
substrate file like every other path entry.

Universal envelope inputs (the six operator-authored governance files
every workspace has) remain hardcoded as kernel-universal constants.
Adding a new program requires zero edits to this module — the new bundle
declares its envelope; bundle_reader exposes it; this module reads it.

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
from datetime import datetime, timezone
from typing import Any, Awaitable

from services.workspace_paths import (
    REVIEW_IDENTITY_PATH,
    REVIEW_PRINCIPLES_PATH,
    REVIEW_OCCUPANT_PATH,
    REVIEW_STANDING_INTENT_PATH,
    SHARED_PRECEDENT_PATH,
    SHARED_MANDATE_PATH,
    SHARED_AUTONOMY_PATH,
    SHARED_PREFERENCES_PATH,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Universal envelope inputs (kernel-shipped — present in every workspace)
# ---------------------------------------------------------------------------
# Per ADR-281 D2 the kernel ships the universal "how" envelope; bundles
# declare their program-shaped additions via MANIFEST `substrate_abi.reviewer_wake_envelope`.
# This list is the kernel side. Each entry: (key, workspace-relative-path).

_UNIVERSAL_ENVELOPE_DECLS: list[tuple[str, str]] = [
    # — Governance (Persona + Framework class) —
    ("identity_md", REVIEW_IDENTITY_PATH),
    ("principles_md", REVIEW_PRINCIPLES_PATH),
    ("precedent_md", SHARED_PRECEDENT_PATH),
    ("mandate_md", SHARED_MANDATE_PATH),
    ("autonomy_md", SHARED_AUTONOMY_PATH),
    ("preferences_yaml", SHARED_PREFERENCES_PATH),
    # — Seat Occupant (ADR-284) — current occupant identity, runtime-truth-aligned
    ("occupant_md", REVIEW_OCCUPANT_PATH),
    # — Standing Intent (ADR-284) — what the Reviewer was watching for last cycle.
    # The Reviewer reads this on every wake, compares against current world state,
    # and updates it before standing down. The substrate counterpart to a no-fire
    # judgment is an updated standing_intent.md.
    ("standing_intent_md", REVIEW_STANDING_INTENT_PATH),
]


# ---------------------------------------------------------------------------
# Envelope assembly — substrate-only, no kernel-side computation
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
      - occupant_md          → /workspace/review/OCCUPANT.md            (ADR-284)
      - standing_intent_md   → /workspace/review/standing_intent.md     (ADR-284)

    Program-shaped envelope (read from active bundle's MANIFEST per ADR-281
    D2): substrate paths declared in `substrate_abi.reviewer_wake_envelope`.
    For alpha-trader workspaces today this includes `operator_profile_md`,
    `risk_md`, `ground_truth_md`, and `signal_files` (which reads the
    `_signals_summary.md` substrate file written by alpha-trader's
    `mirror-signal-state` mechanical recurrence per ADR-281 D3).

    Adding a new program requires zero edits to this function. The new
    bundle declares its envelope; `bundle_reader.get_substrate_abi_for_workspace`
    exposes it; the loop below reads it. All values returned are str (empty
    string when absent — never raises) so the Reviewer's envelope renderer
    (`_build_user_message`) skips absent sections gracefully.

    Per Derived Principle 19: the kernel reads substrate; it does not
    derive state at prompt-assembly time. Substrate that needs compaction
    is written by mechanical primitives, not summarized at envelope-load
    time.
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
    # Per ADR-281 D1: one declaration shape per envelope entry: {key, path, optional}.
    # No path_glob, no summarizer. The kernel reads substrate; mechanical
    # primitives write derivative-compaction substrate.
    from services import bundle_reader

    abi = bundle_reader.get_substrate_abi_for_workspace(user_id, client)
    program_decls = abi.get("reviewer_wake_envelope", []) or []

    program_tasks: list[Awaitable[str]] = []
    program_keys: list[str] = []
    for decl in program_decls:
        if not isinstance(decl, dict):
            continue
        key = decl.get("key")
        path = decl.get("path")
        if not key or not isinstance(path, str):
            continue
        # Skip duplicates of universal entries — kernel universals win.
        if key in envelope:
            logger.warning(
                "[REVIEWER_ENVELOPE] bundle envelope key %s collides with "
                "kernel-universal entry; kernel value wins", key,
            )
            continue
        program_keys.append(key)
        program_tasks.append(_read(path))

    if program_tasks:
        program_results = await _asyncio.gather(*program_tasks)
        for key, value in zip(program_keys, program_results):
            envelope[key] = value

    elapsed_ms = int(
        (datetime.now(timezone.utc) - _started_at).total_seconds() * 1000
    )
    return envelope, elapsed_ms
