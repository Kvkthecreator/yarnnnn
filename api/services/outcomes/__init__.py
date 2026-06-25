"""Ground-truth intake — the consequence pipe (ADR-195 v2 + ADR-330).

Per FOUNDATIONS Axiom 8 + ADR-332's four-flow model, this package is
**flow 3 — outcomes in**: reality's verdict on the operation's own acts
flowing back into substrate. Ground-truth's canonical home is
`/workspace/operation/{domain}/_money_truth.md` per domain (the alpha-trader
instance filename; `_signal.md` for authored), with
`/workspace/operation/_money_truth_summary.md` as the cross-domain rollup.
This package provides:

  - base.py      — OutcomeProvider ABC + OutcomeCandidate shape (signal_id
                   for per-signal attribution; `attestation` + `retrospective`
                   per ADR-330)
  - ledger.py    — fold candidates into the ground-truth file (filesystem),
                   frontmatter-based idempotency + by_signal bucketing +
                   attestation accounting + segmented retrospective backfill
  - trading.py   — TradingOutcomeProvider (Alpaca, attestation=platform)
  - commerce.py  — CommerceOutcomeProvider (LS, attestation=platform)
  - operator.py  — OperatorOutcomeProvider (CSV import, attestation=operator;
                   ADR-330 D1 universal fallback) + reconcile_operator_import
  - reconciler.py — per-user dispatcher across providers (the consequence pipe)

Consumers (Reviewer, daily-update briefing, YARNNN chat, Home ground-truth
hero) read the ground-truth file directly via the filesystem. No service
layer over it.
"""

from __future__ import annotations

from services.outcomes.base import OutcomeCandidate, OutcomeProvider
from services.outcomes.commerce import CommerceOutcomeProvider
from services.outcomes.ledger import (
    SUMMARY_PATH,
    compute_since_for_provider,
    fold_outcome_candidates,
    write_money_truth_summary,
)
from services.outcomes.operator import (
    OperatorOutcomeProvider,
    reconcile_operator_import,
)
from services.outcomes.reconciler import (
    DEFAULT_PROVIDERS,
    PLATFORM_ATTESTED_PLATFORMS,
    has_platform_attested_provider,
    reconcile_user,
)
from services.outcomes.trading import TradingOutcomeProvider

__all__ = [
    "DEFAULT_PROVIDERS",
    "PLATFORM_ATTESTED_PLATFORMS",
    "CommerceOutcomeProvider",
    "OperatorOutcomeProvider",
    "OutcomeCandidate",
    "OutcomeProvider",
    "SUMMARY_PATH",
    "TradingOutcomeProvider",
    "compute_since_for_provider",
    "fold_outcome_candidates",
    "has_platform_attested_provider",
    "reconcile_operator_import",
    "reconcile_user",
    "write_money_truth_summary",
]
