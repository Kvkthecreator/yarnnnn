"""Money-Truth Substrate (ADR-195 v2).

Per FOUNDATIONS Axiom 7, money-truth's canonical home is
`/workspace/context/{domain}/_performance.md` per domain. This package
provides:

  - base.py      — OutcomeProvider ABC + OutcomeCandidate shape
  - ledger.py    — fold candidates into `_performance.md` (filesystem),
                   frontmatter-based idempotency
  - trading.py   — TradingOutcomeProvider (Alpaca closed round-trips)
  - commerce.py  — CommerceOutcomeProvider (LS paid/refund orders)
  - reconciler.py — per-user dispatcher across providers

Consumers (Reviewer, daily-update briefing, YARNNN chat) read
`_performance.md` directly via the filesystem. No service layer over
money-truth.
"""

from __future__ import annotations

from services.outcomes.base import OutcomeCandidate, OutcomeProvider
from services.outcomes.commerce import CommerceOutcomeProvider
from services.outcomes.ledger import (
    SUMMARY_PATH,
    compute_since_for_provider,
    fold_outcome_candidates,
    write_performance_summary,
)
from services.outcomes.reconciler import DEFAULT_PROVIDERS, reconcile_user
from services.outcomes.trading import TradingOutcomeProvider

__all__ = [
    "DEFAULT_PROVIDERS",
    "CommerceOutcomeProvider",
    "OutcomeCandidate",
    "OutcomeProvider",
    "SUMMARY_PATH",
    "TradingOutcomeProvider",
    "compute_since_for_provider",
    "fold_outcome_candidates",
    "reconcile_user",
    "write_performance_summary",
]
