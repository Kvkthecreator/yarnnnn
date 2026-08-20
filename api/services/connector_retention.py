"""Connector raw-lane retention — the anti-bloat dial (ADR-392 D8).

Connectors are the first HIGH-VOLUME context-in transport, so the capture lane
(inbound/{platform}/) needs a retention answer that MCP + web never forced (their
volume never triggered ADR-376 §8's deferred raw-lane GC). This module un-defers
that GC as an operator DIAL:

  - a substrate-read `retention_days` policy (NOT a hard-coded enum) at a
    governance path; the 7/14/30 the UI offers are PRESETS over a dynamic value;
  - EVIDENCE-BOUNDED RETENTION (ADR-394 D4 / ADR-401 D4): a raw observation is
    prunable only if (a) it is older than the window AND (b) NO derived act
    cites it. A cited raw is EVIDENCE in a provenance chain (derived_from /
    trace) and is never pruned; un-cited raw past the window is presumed noise
    (connector raw is mostly un-context chatter) and ages out mechanically.
    Unknown citation state (the gather failed) prunes NOTHING — fail-safe.

⭐ PRICING SEAM (ADR-391, wired in a LATER session — mechanic only here).
`resolve_retention_days` reads ONE value, so the pricing layer can gate the
MAXIMUM allowed window per subscription tier WITHOUT touching GC code:
retention-window is a natural commons-scale tier axis (parallel to ADR-391's
# principals · # connectors · autonomy-ceiling). The pricing session sets the
tier→max-window mapping by clamping the operator's declared value against a
tier ceiling BEFORE it reaches `resolve_retention_days`, or by having this reader
consult the tier ceiling. Either way the GC is untouched — it just honors the
resolved number. No pricing code lives here.

Axiom-1 / resume safety: like SyncPlatformState, the GC does NOT read the clock.
`now_iso` is passed in by the caller (the scheduler stamps it), and raw age is
computed from the {observed_at} segment already in the filename — deterministic,
replayable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Governance path — operator config the steward reads-not-authors (ADR-254
# machine-parsed yaml, `_`-prefixed). governance/ is the GRANT root (locked to
# operator authorship; ADR-366), which is correct: retention is a spend/storage
# envelope, kin to _budget.yaml.
RETENTION_POLICY_PATH = "governance/_retention.yaml"

# Kernel default — generous so no operator loses raw silently before opting in.
DEFAULT_RETENTION_DAYS = 30

INBOUND_ROOT = "inbound/"


async def resolve_retention_days(
    client: Any,
    user_id: str,
    *,
    tier_max_days: Optional[int] = None,
) -> int:
    """Resolve the effective raw-lane retention window (days).

    Reads governance/_retention.yaml (`retention_days: <int>`); falls back to
    DEFAULT_RETENTION_DAYS when unset/unparseable. `tier_max_days` is the PRICING
    SEAM (ADR-391): when a subscription tier caps the window, the resolved value
    is clamped to it — the pricing session passes this; today's callers pass None
    and the operator's declared value stands. Never raises.
    """
    from services.workspace import UserMemory
    from services.review_policy import load_workspace_yaml

    declared = DEFAULT_RETENTION_DAYS
    um = UserMemory(client, user_id)
    try:
        body = await um.read(RETENTION_POLICY_PATH)
    except Exception:
        body = None
    if body:
        parsed = load_workspace_yaml(body)
        raw = parsed.get("retention_days")
        if isinstance(raw, bool):  # bool is an int subclass — reject explicitly
            raw = None
        if isinstance(raw, int) and raw > 0:
            declared = raw
        elif raw is not None:
            logger.warning(
                "[CONNECTOR_RETENTION] non-int retention_days=%r for user=%s; using default",
                raw, user_id[:8],
            )
    if tier_max_days is not None and tier_max_days > 0:
        return min(declared, tier_max_days)
    return declared


async def read_retention_days(client: Any, user_id: str) -> int:
    """The operator's DECLARED retention window (no tier clamp) — for the FE dial's
    current-state read. Returns DEFAULT_RETENTION_DAYS when unset. Never raises.

    Distinct from `resolve_retention_days`: that applies the pricing tier ceiling
    (the effective GC value); this returns the raw declared value the dial edits."""
    return await resolve_retention_days(client, user_id, tier_max_days=None)


async def write_retention_days(
    client: Any,
    user_id: str,
    days: int,
    *,
    authored_by: str = "operator",
) -> int:
    """Author governance/_retention.yaml with `retention_days: <days>` (ADR-392 D8).

    The single write path for the retention dial. Clamps to a sane floor (1 day)
    so a zero/negative can't disable retention silently. governance/ is the GRANT
    root (operator-authored; the steward reads-not-authors), so authored_by is
    'operator' by default. Returns the written value.
    """
    from services.workspace import UserMemory
    import yaml as _yaml

    clamped = max(1, int(days))
    content = _yaml.safe_dump(
        {"retention_days": clamped}, sort_keys=False, default_flow_style=False,
    )
    um = UserMemory(client, user_id)
    await um.write(
        RETENTION_POLICY_PATH,
        content,
        summary="retention-policy",
        authored_by=authored_by,
        message=f"set raw-capture retention window to {clamped} days",
    )
    logger.info("[CONNECTOR_RETENTION] user=%s set retention_days=%d", user_id[:8], clamped)
    return clamped


__all__ = [
    "RETENTION_POLICY_PATH",
    "DEFAULT_RETENTION_DAYS",
    "resolve_retention_days",
    "read_retention_days",
    "write_retention_days",
]
