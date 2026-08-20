"""Capture-lane gate — the ADR-393 declaration lane's dormancy (ADR-591).

Replaces `connector_capture_gating.py`, whose name and docstring described a
world that no longer exists: it gated the CONNECTOR walk (deleted by ADR-591
D2), the connector digest walker (D3.a), the connector raw-lane GC (D3.b),
and — incidentally — this lane, which is a different thing with different
tenants.

**What this gates**: `services/capture/drainer.py::drain_due_captures`, the
ADR-393 declaration lane (`_captures.yaml`) whose tenants are ground-truth
state mirrors, perception watches, and substrate mirrors. It has never been
the connector's trigger; the connector merely shared its flag.

**Default = OFF when unset**, carrying ADR-404 D2's ratified dormancy
forward unchanged. Production holds exactly one declaration file and it is
empty (`captures: []`, measured 2026-08-20), so the lane walks nothing
either way — the flag stays because the lane's own re-light is a decision
this ADR does not make.

Connector capture is NOT here and has no flag: it is consumer-invoked
(ADR-591 D3). The writer is `services.connectors.run_connector_capture`;
what calls it is a named, unbuilt seam.
"""

from __future__ import annotations

import os

# Truthy/falsey tokens, matching the AGENT_ENABLED precedent.
_TRUE_TOKENS = {"1", "true", "yes", "on"}
_FALSE_TOKENS = {"0", "false", "no", "off"}


def is_capture_lane_enabled() -> bool:
    """Whether the ADR-393 declaration capture lane runs.

    Default when `CAPTURE_LANE_ENABLED` is unset: **OFF** (ADR-404 D2's
    dormancy, carried forward). An explicit true token is required.
    """
    raw = os.getenv("CAPTURE_LANE_ENABLED")
    if raw is None:
        return False  # default OFF — dormancy is the ratified state
    token = raw.strip().lower()
    if token in _TRUE_TOKENS:
        return True
    if token in _FALSE_TOKENS:
        return False
    # An unrecognized value must not silently start a lane.
    return False


__all__ = ["is_capture_lane_enabled"]
