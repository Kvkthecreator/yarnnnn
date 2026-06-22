"""Connection demand signal — turn unmet capability requests into a discovery queue.

ADR-353 §15 (connection lifecycle): new platform connections are added Hat-A
(developer-explicit, curated — findings §11.3), in service of *program demand*,
NOT by browsing Composio's catalog. The demand signal is: a recurrence declared a
`required_capability` whose platform connection is not available, so the tool was
silently dropped from the agent's surface (the ADR-227 empty-deliverable failure
mode). That silent drop, captured, IS the discovery queue — "which workspaces
wanted which unsupported capabilities" — grounded in real operator need rather than
speculative catalog curation.

Sink (deliberate, alpha-scale): a structured `[CONNECTION-DEMAND]` log line, NOT a
new table and NOT `execution_events` (that is the ADR-291 cost ledger — a demand
row would pollute cost queries). At alpha volume the "queue" is a log search
(Render logs / `grep`); promote to a table only when volume justifies it. One
recorder, one marker, documented here — per CLAUDE.md behavioral-artifact
discipline (#10).

Read the queue:
  Render logs (yarnnn-api + yarnnn-unified-scheduler) → filter `[CONNECTION-DEMAND]`.
  Each line carries: user_id, capability, reason, required_platform.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_MARKER = "[CONNECTION-DEMAND]"


def record_unmet_capability(
    user_id: str,
    capability: str,
    *,
    reason: str,
    required_platform: str | None,
) -> None:
    """Emit one demand-signal line for a capability a recurrence requested but
    could not get (no curated capability, or platform not connected).

    Args:
        user_id:           the workspace whose recurrence hit the gap.
        capability:        the requested capability key (e.g. "write_linear").
        reason:            "unknown_capability" (no curated capability — a
                           discovery candidate for Hat-A to add) OR
                           "platform_not_connected" (capability exists, operator
                           just hasn't connected — NOT a discovery signal, an
                           operator-onboarding signal).
        required_platform: the platform the capability needs, if known.

    Non-raising: a demand-signal failure must never break tool loading.
    """
    try:
        logger.info(
            "%s user=%s capability=%s reason=%s platform=%s",
            _MARKER, user_id, capability, reason, required_platform or "—",
        )
    except Exception:  # pragma: no cover — telemetry must not break the caller
        pass


def record_unmet_capabilities(user_id: str, gaps: list[dict[str, Any]]) -> None:
    """Batch form: record each gap from `orchestration.unavailable_capabilities()`.

    Only `unknown_capability` rows are true *discovery* candidates (a capability
    YARNNN does not offer yet — the Hat-A add signal). `platform_not_connected`
    rows are operator-onboarding signals (the capability exists; connect it).
    Both are logged with their reason so the queue distinguishes them.
    """
    for gap in gaps or []:
        record_unmet_capability(
            user_id,
            gap.get("capability", "?"),
            reason=gap.get("reason", "unknown"),
            required_platform=gap.get("required_platform"),
        )
