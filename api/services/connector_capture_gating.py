"""Connector-capture gate — ADR-404 D2 (the commons-first launch).

The single source of truth for **whether the connector capture lane runs**
in a deployment. ADR-404 puts the mechanical 15-minute pull lane
(ADR-392→401) DORMANT for the commons-first launch: hide, not revert —
every capture module, migration, and test gate stays intact; this flag is
the only thing between dormant and live.

Consulted at the three cut sites (ADR-404 D2, the minimal cut):
  1. unified_scheduler — the capture drain (`drain_due_captures`) and the
     connector raw-lane GC (`prune_raw_lane` loop). Cutting the drain is
     what stops captures firing; the GC is meaningless without intake.
  2. routes/integrations.update_selected_sources — the seed-at-select
     (`seed_connector_capture`) so source selection stops minting new
     `_captures.yaml` entries. Disconnect teardown stays UNGUARDED —
     cleanup must always work.
  3. The capture-signal endpoint surfaces `connector_capture_enabled` so
     the FE hides the CADENCE + YIELD sections and the retention dial
     (ACCESS + SCOPE stay — OAuth, scopes, and the validate probe are the
     launch substance, not part of the cut).

**Default = OFF when unset (ADR-404 D2).** This deliberately inverts the
`AGENT_ENABLED` default-ON rationale (ADR-375 D4): there, unset had to mean
"current behavior, unchanged" because the flag was an isolation seam for a
*future* launch. Here, dormancy IS the ratified current decision — an
unset deploy must not silently resume the burn the flag exists to stop.
Set `CONNECTOR_CAPTURE_ENABLED=true` (dev / e2e / a future re-entry) to
run the lane.

**Render parity (CLAUDE.md §5):** when re-enabling, set the flag on
**API + Unified Scheduler** together — the drain lives on the scheduler,
the seed + FE signal on the API. Unset everywhere = dormant everywhere,
which is the safe launch state.
"""

from __future__ import annotations

import os

# Truthy/falsey tokens, matching the AGENT_ENABLED / COMPOSIO_DRIVER_ENABLED
# precedent.
_TRUE_TOKENS = {"1", "true", "yes", "on"}
_FALSE_TOKENS = {"0", "false", "no", "off"}


def is_connector_capture_enabled() -> bool:
    """Whether the connector capture lane (seed, drain, GC, cadence UI) runs.

    Default when `CONNECTOR_CAPTURE_ENABLED` is unset: **OFF** (ADR-404 D2 —
    dormant is the decision, not the exception). An explicit true token is
    required to run the lane.
    """
    raw = os.getenv("CONNECTOR_CAPTURE_ENABLED")
    if raw is None:
        return False  # default OFF (ADR-404 D2) — dormancy is the ratified state
    token = raw.strip().lower()
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    # Unrecognized non-empty value → default OFF (fail-safe toward dormancy).
    return False


__all__ = ["is_connector_capture_enabled"]
