"""Steward-presence gate — ADR-375 §6 (Phase 1: substrate for humans + external agents).

The single source of truth for **whether the internal steward (the Reviewer —
the future "Freddie") is present** in a deployment. Phase 1 (ADR-375) defines
YARNNN positively as *the file-system-native substrate operated by humans AND
external agents as principals*; the internal steward is a Phase-2 concern that
ships dormant-behind-this-flag.

This resolver is consulted at the four pre-cut chokepoints (ADR-375 §6):
  1. unified_scheduler — the walker+drain+dispatch block (the load-bearing
     Trigger gate; gate the walker AND drain as a unit, never drain-only).
  2. wake.submit_wake_proposal — early-return (belt-and-suspenders; also
     covers the MCP→wake adapter, which reaches the queue only via this fn).
  3. routes/feed.py — the addressed (chat→Reviewer) path.
  4. kernel_surfaces.kernel_surface_entries — filter the steward surfaces.
It is also the input ADR-374 reads to choose the at-rest IA face.

**Default = ON when unset (ADR-375 D4).** The flag is an *isolation seam for a
future public launch, not a behavior flip for the current live system*.
Defaulting OFF would silently gate the steward on every existing deploy the
moment this ships, and risk the API/Scheduler drift CLAUDE.md §5 warns about
(gate the API but forget the Scheduler → wake_queue rows pile up undrained).
Default ON keeps the seam invisible until *invoked*: the off-state is something
a specific deploy SETS (`AGENT_ENABLED=false`), deliberately, for the
interop-first launch.

**Render parity (CLAUDE.md §5):** `AGENT_ENABLED` must be set consistently on
**API + Unified Scheduler** — chokepoint #1 lives on the scheduler. MCP server +
render gateway hold no wake-trigger and are unaffected.
"""

from __future__ import annotations

import os

# Truthy/falsey tokens, matching the COMPOSIO_DRIVER_ENABLED precedent
# (services/composio_driver.py). Anything outside these sets is treated by the
# default rule below.
_TRUE_TOKENS = {"1", "true", "yes", "on"}
_FALSE_TOKENS = {"0", "false", "no", "off"}


def is_agent_enabled(workspace_id: str | None = None) -> bool:
    """Whether the internal steward layer is present for this deployment.

    ADR-375 D4: per-deploy env flag now; per-workspace forward-compatible.

    Args:
        workspace_id: accepted for forward-compatibility (density-gating per
            interop-first-pivot §5 decision 3 — open the beta per-workspace on
            substrate density). **Currently unused** — the resolver reads the
            per-deploy env flag only. A future per-workspace branch lands here
            WITHOUT touching the four chokepoints (they already pass it).

    Returns:
        True when the steward should wake / its surfaces should appear;
        False when the deployment runs substrate-only (Phase-1 interop face).

    Default when `AGENT_ENABLED` is unset: **ON** (ADR-375 D4 — isolation seam,
    not a behavior flip). Set `AGENT_ENABLED=false` to gate the steward off.
    """
    raw = os.getenv("AGENT_ENABLED")
    if raw is None:
        return True  # default ON (D4) — unset means current behavior, unchanged
    token = raw.strip().lower()
    if token in _FALSE_TOKENS:
        return False
    if token in _TRUE_TOKENS:
        return True
    # Unrecognized non-empty value → default ON (fail-safe toward current
    # behavior; an explicit false token is required to gate off).
    return True


__all__ = ["is_agent_enabled"]
