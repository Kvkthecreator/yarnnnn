"""Reviewer wake envelope assembly (ADR-276).

The Reviewer perceives full operator-authored governance substrate + domain
substrate at every wake, regardless of trigger shape (addressed | reactive).
This module is the single canonical assembly point for that substrate —
called by both `routes/feed.py` (addressed turns) and
`services/invocation_dispatcher.py` (reactive turns).

Pre-loading discipline (FOUNDATIONS v8.5 Axiom 4 + Derived Principle 18 +
ADR-275 refinement learning): load-bearing substrate arrives in the wake
envelope, NOT as a prose-named "remember to ReadFile X" side-quest. Run-1
vs run-2 of the ADR-275 e2e empirically validated the structural difference:
the same operator-says-hi prompt produced zero Schedule calls when
`_preferences.yaml` was prose-named, but three Schedule calls when it was
pre-loaded in the envelope.

This helper centralizes the 9-file gather so both trigger paths share one
implementation. Singular Implementation: one helper, two callers.
"""

from __future__ import annotations

import asyncio as _asyncio
import logging
from typing import Any

from services.workspace_paths import (
    REVIEW_IDENTITY_PATH,
    REVIEW_PRINCIPLES_PATH,
    SHARED_PRECEDENT_PATH,
    SHARED_MANDATE_PATH,
    SHARED_AUTONOMY_PATH,
    SHARED_PREFERENCES_PATH,
)

logger = logging.getLogger(__name__)


async def load_reviewer_governance_envelope(client: Any, user_id: str) -> dict:
    """Assemble the Reviewer's wake envelope substrate.

    Returns a dict keyed by `ReviewerContext` field names — drop directly
    into the context bag passed to `invoke_reviewer()`. All reads happen
    in parallel via `asyncio.gather` to minimize wake-envelope latency.

    Fields returned (all str, empty string when absent — never raises):
      - identity_md          → /workspace/review/IDENTITY.md
      - principles_md        → /workspace/review/principles.md
      - precedent_md         → /workspace/context/_shared/PRECEDENT.md
      - mandate_md           → /workspace/context/_shared/MANDATE.md
      - autonomy_md          → /workspace/context/_shared/AUTONOMY.md
      - preferences_yaml     → /workspace/context/_shared/_preferences.yaml
      - operator_profile_md  → /workspace/context/trading/_operator_profile.md
      - risk_md              → /workspace/context/trading/_risk.md
      - performance_md       → /workspace/context/trading/_performance.md
      - signal_files         → compact summary of /workspace/context/trading/signals/*

    The `_operator_profile`, `_risk`, `_performance` paths are alpha-trader-
    program-specific. Future programs (alpha-commerce, etc.) read empty
    strings for these fields — the Reviewer's envelope renderer
    (`_build_user_message`) skips absent sections gracefully.
    """

    async def _read(path: str) -> str:
        """Read a workspace file by relative path, return '' on miss."""
        full = f"/workspace/{path}"
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

    (
        identity_md, principles_md, precedent_md, mandate_md,
        autonomy_md, preferences_yaml,
        operator_profile_md, risk_md, performance_md,
    ) = await _asyncio.gather(
        _read(REVIEW_IDENTITY_PATH),
        _read(REVIEW_PRINCIPLES_PATH),
        _read(SHARED_PRECEDENT_PATH),
        _read(SHARED_MANDATE_PATH),
        _read(SHARED_AUTONOMY_PATH),
        _read(SHARED_PREFERENCES_PATH),
        _read("context/trading/_operator_profile.md"),
        _read("context/trading/_risk.md"),
        _read("context/trading/_performance.md"),
    )

    # Signal files compact summary — defer import to avoid circular
    # (reviewer_agent imports from this module via the dispatcher path).
    from agents.reviewer_agent import read_signal_files
    signal_files_summary = await read_signal_files(client, user_id)

    return {
        "identity_md": identity_md,
        "principles_md": principles_md,
        "precedent_md": precedent_md,
        "mandate_md": mandate_md,
        "autonomy_md": autonomy_md,
        "preferences_yaml": preferences_yaml,
        "operator_profile_md": operator_profile_md,
        "risk_md": risk_md,
        "performance_md": performance_md,
        "signal_files": signal_files_summary,
    }
