"""Per-user outcome reconciliation dispatcher (ADR-195 Phase 1).

Runs every registered OutcomeProvider for a single user, in sequence, and
returns a structured summary. Provider errors are isolated — one provider's
outage does not block siblings.

Phase 1 registers only TradingOutcomeProvider. Phase 2 adds
CommerceOutcomeProvider. Phase 5 adds EmailOutcomeProvider.

Phase 2 will also add a back-office task (`back-office-outcome-reconciliation`)
that calls `reconcile_user` once per user per day. Phase 1 exposes the
dispatcher so it can be smoke-tested manually.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from services.outcomes.base import OutcomeProvider
from services.outcomes.ledger import (
    compute_since_for_provider,
    insert_outcome_candidates,
)
from services.outcomes.trading import TradingOutcomeProvider

logger = logging.getLogger(__name__)


#: Ordered list of providers to run. Order is not semantically significant
#: today; kept stable for deterministic logging and future cross-provider
#: ordering (e.g., commerce-refund → trading-hedge).
DEFAULT_PROVIDERS: list[OutcomeProvider] = [
    TradingOutcomeProvider(),
]


async def reconcile_user(
    client: Any,
    user_id: str,
    providers: list[OutcomeProvider] | None = None,
) -> dict[str, Any]:
    """Reconcile outcomes for a single user across all registered providers.

    Returns a summary dict:
      {
        "user_id": "...",
        "started_at": "...",
        "finished_at": "...",
        "providers": {
           "trading-reconciler-v1": {
              "since": "...",
              "candidates": int,
              "inserted": int,
              "skipped_duplicate": int,
              "skipped_invalid": int,
              "error": None or str,
           },
           ...
        },
        "total_inserted": int,
      }
    """
    providers = providers or DEFAULT_PROVIDERS
    started_at = datetime.now(timezone.utc)

    summary: dict[str, Any] = {
        "user_id": user_id,
        "started_at": started_at.isoformat(),
        "providers": {},
        "total_inserted": 0,
    }

    for provider in providers:
        try:
            since = await compute_since_for_provider(client, user_id, provider)
            candidates = await provider.reconcile(user_id, client, since)
            counts = await insert_outcome_candidates(
                client, user_id, provider, candidates,
            )
            summary["providers"][provider.provider_name] = {
                "since": since.isoformat(),
                "candidates": len(candidates),
                **counts,
                "error": None,
            }
            summary["total_inserted"] += counts["inserted"]
        except Exception as exc:  # noqa: BLE001 — dispatcher isolates failures
            logger.error(
                "[OUTCOMES] provider=%s failed for user=%s: %s",
                provider.provider_name,
                user_id[:8],
                exc,
                exc_info=True,
            )
            summary["providers"][provider.provider_name] = {
                "since": None,
                "candidates": 0,
                "inserted": 0,
                "skipped_duplicate": 0,
                "skipped_invalid": 0,
                "error": str(exc),
            }

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    return summary
