"""Money-Truth Substrate (ADR-195 v2 + P&L unification 2026-05-12).

Per FOUNDATIONS Axiom 8 + the P&L unification refactor, money-truth's
canonical home is `/workspace/context/{domain}/_money_truth.md` per
domain, with `/workspace/context/_money_truth_summary.md` as the cross-
domain rollup. This package provides:

  - base.py      — OutcomeProvider ABC + OutcomeCandidate shape (with
                   signal_id for per-signal attribution)
  - ledger.py    — fold candidates into `_money_truth.md` (filesystem),
                   frontmatter-based idempotency + by_signal bucketing
  - trading.py   — TradingOutcomeProvider (Alpaca closed round-trips
                   with proposal-recovered signal attribution)
  - commerce.py  — CommerceOutcomeProvider (LS paid/refund orders)
  - reconciler.py — per-user dispatcher across providers

Consumers (Reviewer, daily-update briefing, YARNNN chat, cockpit
faces) read `_money_truth.md` directly via the filesystem. No service
layer over money-truth.
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
    "write_money_truth_summary",
]
