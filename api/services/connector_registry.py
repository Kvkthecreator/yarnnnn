"""
Connector registry — the backend half of the SINGLE offered-connector source
(ADR-494 D1).

## Why this module exists

Before ADR-494 the offered set was duplicated: a 5-entry `CONNECTOR_REGISTRY`
array in `web/lib/connectors/registry.tsx` drove what rendered, while a
hardcoded `SUPPORTED_PLATFORMS = {...}` literal inside
`routes/integrations.py::get_integrations_summary` decided what the API would
report. Adding the Nth connector meant editing both, and nothing detected
drift. Worse, a THIRD list — the summary emission loop, which iterated a bare
`("slack", "notion", "github")` tuple — meant a connected commerce/trading
connection was never emitted as active, so the frontend (which keys
connectedness off that summary) rendered it under "New connection" forever.

This module is the one backend list. `routes/integrations.py` derives from it;
`api/test_adr494_connector_registry.py` asserts it stays byte-identical to the
frontend registry by parsing the .tsx directly — so drift fails CI rather than
reaching an operator.

## Status semantics (mirrors the TS `ConnectorStatus`)

- ``live``    — a real connect path AND a capture binding. Offered.
- ``retired`` — kept as data so a historical connection still resolves, but not
                offered as a new connection (hide-not-delete, per ADR-404 D2 /
                ADR-425).

Dormancy is deliberately NOT a status here: it is a property of the capture
LANE (the capture flag, deleted by ADR-591 — capture is consumer-invoked), read once from
`services.connector_capture_gating`, never encoded per-connector.
"""

from __future__ import annotations

from typing import Literal

ConnectorStatus = Literal["live", "retired"]

# The registry. Order mirrors the frontend's render order so the gate test can
# compare positionally as well as by membership.
#
# ADR-494 D2 — commerce + trading are RETIRED. Receipted 2026-07-29: zero rows
# of either have ever existed in `platform_connections`; neither appears in
# `CONNECTOR_CAPTURE_BINDINGS` (so neither ever had a connector-lane reader);
# trading's only capture path is the alpha-trader bundle's SyncPlatformState
# mirrors, gated behind a hire with no operator surface (ADR-414 D5).
CONNECTOR_REGISTRY: dict[str, ConnectorStatus] = {
    "slack": "live",
    "notion": "live",
    "github": "live",
    "commerce": "retired",
    "trading": "retired",
}

# Every provider the API recognizes at all — live + retired. A retired
# provider stays recognized so an existing connection can still be READ and
# DISCONNECTED; it is simply never offered.
CONNECTOR_PROVIDERS: frozenset[str] = frozenset(CONNECTOR_REGISTRY)

# The providers offered as a NEW connection, in registry order.
OFFERED_PROVIDERS: tuple[str, ...] = tuple(
    p for p, s in CONNECTOR_REGISTRY.items() if s == "live"
)


def is_offered(provider: str) -> bool:
    """Whether `provider` may be connected as a NEW connection (ADR-494 D1)."""
    return CONNECTOR_REGISTRY.get(provider) == "live"


__all__ = [
    "ConnectorStatus",
    "CONNECTOR_REGISTRY",
    "CONNECTOR_PROVIDERS",
    "OFFERED_PROVIDERS",
    "is_offered",
]
