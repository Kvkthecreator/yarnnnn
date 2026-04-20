"""Per-user outcome reconciliation dispatcher (ADR-195 v2).

Runs every registered OutcomeProvider for a single user, in sequence, and
returns a structured summary. Provider errors are isolated — one provider's
outage does not block siblings.

Per ADR-195 v2, the reconciler writes to
`/workspace/context/{domain}/_performance.md` per domain, not to a SQL
ledger. Providers emit OutcomeCandidate dicts; ledger.fold_outcome_candidates
persists them via filesystem upsert with frontmatter-based idempotency.

The back-office task `back-office-outcome-reconciliation` (ADR-195 Phase 2)
calls `reconcile_user` once per user per day. Callers can also invoke it
manually for smoke tests.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from services.outcomes.base import OutcomeProvider
from services.outcomes.commerce import CommerceOutcomeProvider
from services.outcomes.ledger import (
    compute_since_for_provider,
    fold_outcome_candidates,
    write_performance_summary,
)
from services.outcomes.trading import TradingOutcomeProvider

logger = logging.getLogger(__name__)


#: Ordered list of providers to run. Order is not semantically significant
#: today; kept stable for deterministic logging and future cross-provider
#: ordering (e.g., commerce-refund → trading-hedge).
DEFAULT_PROVIDERS: list[OutcomeProvider] = [
    TradingOutcomeProvider(),
    CommerceOutcomeProvider(),
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
              "appended": int,
              "skipped_duplicate": int,
              "skipped_invalid": int,
              "error": None or str,
           },
           ...
        },
        "total_appended": int,
      }
    """
    providers = providers or DEFAULT_PROVIDERS
    started_at = datetime.now(timezone.utc)

    summary: dict[str, Any] = {
        "user_id": user_id,
        "started_at": started_at.isoformat(),
        "providers": {},
        "total_appended": 0,
        "cross_domain_summary_written": False,
    }

    for provider in providers:
        try:
            since = await compute_since_for_provider(client, user_id, provider)
            candidates = await provider.reconcile(user_id, client, since)
            counts = await fold_outcome_candidates(
                client, user_id, provider, candidates,
            )
            summary["providers"][provider.provider_name] = {
                "since": since.isoformat(),
                "candidates": len(candidates),
                **counts,
                "error": None,
            }
            summary["total_appended"] += counts["appended"]
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
                "appended": 0,
                "skipped_duplicate": 0,
                "skipped_invalid": 0,
                "error": str(exc),
            }

    # Phase 3: regenerate cross-domain summary after all providers fold.
    # Always runs (even if providers failed or had zero appends) so the
    # summary reflects the current state of each domain's _performance.md.
    try:
        provider_domains = [p.context_domain for p in providers]
        summary["cross_domain_summary_written"] = await write_performance_summary(
            client, user_id, provider_domains,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[OUTCOMES] cross-domain summary write failed for user=%s: %s",
            user_id[:8], exc,
        )
        summary["cross_domain_summary_written"] = False

    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    return summary
