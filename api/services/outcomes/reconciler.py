"""Per-user outcome reconciliation dispatcher (ADR-195 v2).

Runs every registered OutcomeProvider for a single user, in sequence, and
returns a structured summary. Provider errors are isolated — one provider's
outage does not block siblings.

Per ADR-195 v2 + the P&L unification refactor (2026-05-12), the reconciler
writes to `/workspace/operation/{domain}/_money_truth.md` per domain, not
to a SQL ledger. Providers emit OutcomeCandidate dicts (now with optional
signal_id per Commit 1); ledger.fold_outcome_candidates persists them via
filesystem upsert with frontmatter-based idempotency and per-signal bucketing.

WHO CALLS THIS (live wiring, 2026-06-26):
  This step is the MECHANICAL pre-fold for a *platform-attested* ground-truth
  loop (ADR-330 `attestation: "platform"`): it polls an external oracle (the
  Alpaca broker, the Lemon Squeezy API), matches fills/orders deterministically
  (FIFO, client_order_id attribution), and writes the reconciled outcomes to
  `_money_truth.md` BEFORE the `outcome-reconciliation` judgment wake reads
  them. An LLM judgment wake structurally cannot do this poll-and-match — so a
  platform-attested program needs this mechanical pre-step, and its prompt
  reads (not folds) the result.

  Live caller: `services.wake._invoke_recurrence_wake` runs this as a pre-step
  before envelope assembly when the workspace has a platform-attested provider
  (`has_platform_attested_provider`), gated on the `outcome-reconciliation`
  slug. (The historical caller — the `back-office-outcome-reconciliation` task,
  ADR-195 Phase 2 — was dissolved when ADR-260/261 collapsed back-office tasks
  into recurrences; the dead wire left `_money_truth.md` un-materialized on
  workspaces that never got the one-time bootstrap. Re-wired 2026-06-26 — see
  docs/evaluations/2026-06-25-trader-money-truth-orphaned-reconciler-AUDIT.md.)

  NOT for operator/agent-attested loops: the alpha-author program's
  ground-truth is operator-attested (`attestation: "operator"`) — already
  LLM-readable substrate — so its `outcome-reconciliation` prompt directs the
  JUDGMENT wake to fold events itself, with NO mechanical pre-step. The
  pre-step gate (`has_platform_attested_provider`) is False for the author, so
  this never runs there. The fold-by-whom split follows the attestation source.

  Operators can also invoke `reconcile_user` manually for smoke tests / CSV
  intake (`services.outcomes.operator`).
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
    write_money_truth_summary,
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

#: The `platform_connections.platform` strings whose presence (active) means
#: this workspace runs a PLATFORM-ATTESTED outcome loop — i.e. an external
#: oracle (broker, payment processor) that must be polled + matched
#: mechanically before the judgment wake can read the result. Kept in lockstep
#: with DEFAULT_PROVIDERS: trading provider ↔ `trading`, commerce provider ↔
#: `commerce`. Operator/agent-attested loops (e.g. alpha-author) have no entry
#: here and fold inside the judgment wake instead — so the mechanical pre-step
#: gate (`has_platform_attested_provider`) is False for them.
PLATFORM_ATTESTED_PLATFORMS: tuple[str, ...] = ("trading", "commerce")


def has_platform_attested_provider(client: Any, user_id: str) -> bool:
    """True iff this workspace has an active platform connection feeding a
    platform-attested outcome provider — the tight gate for running the
    mechanical reconciler as a pre-step before the `outcome-reconciliation`
    judgment wake (see `reconcile_user` docstring + the wake pre-step).

    A pure no-op signal for operator/agent-attested programs: alpha-author
    has slack/notion/github connections but no `trading`/`commerce`, so this
    returns False and the pre-step never runs (no empty-stub pollution of a
    `trading` domain the author does not have — `fold_outcome_candidates`
    writes the stub unconditionally on empty candidates, which is exactly why
    the gate must precede the call, not rely on the fold no-op'ing).

    Never raises — a lookup failure reads as "no platform provider" so the
    pre-step is skipped rather than breaking dispatch.
    """
    try:
        result = (
            client.table("platform_connections")
            .select("platform")
            .eq("user_id", user_id)
            .eq("status", "active")
            .in_("platform", list(PLATFORM_ATTESTED_PLATFORMS))
            .limit(1)
            .execute()
        )
        return bool(result.data)
    except Exception as exc:  # noqa: BLE001 — gate must never break dispatch
        logger.warning(
            "[OUTCOMES] platform-attested gate lookup failed for user=%s: %s — "
            "skipping mechanical pre-step",
            user_id[:8], exc,
        )
        return False


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
    # summary reflects the current state of each domain's _money_truth.md.
    try:
        provider_domains = [p.context_domain for p in providers]
        summary["cross_domain_summary_written"] = await write_money_truth_summary(
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
