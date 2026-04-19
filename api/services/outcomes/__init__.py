"""Outcome Attribution Substrate (ADR-195).

Ledger + providers + reconciliation dispatcher. Translates platform events
into `action_outcomes` rows that feed:
  - AI reviewer track-record (ADR-194 Phase 4)
  - daily-update briefing (ADR-195 Phase 4)
  - feedback actuation (ADR-181)

This package is Phase 1 of ADR-195:
  - base.py     — OutcomeProvider ABC + OutcomeCandidate shape
  - ledger.py   — insert + idempotency helpers over action_outcomes
  - trading.py  — TradingOutcomeProvider (Alpaca closed round-trips)

Later phases add commerce.py, email.py, and the back-office reconciliation
task that sweeps all providers daily per user.
"""

from __future__ import annotations

from services.outcomes.base import OutcomeCandidate, OutcomeProvider
from services.outcomes.commerce import CommerceOutcomeProvider
from services.outcomes.ledger import (
    compute_since_for_provider,
    insert_outcome_candidates,
)
from services.outcomes.reconciler import DEFAULT_PROVIDERS, reconcile_user
from services.outcomes.trading import TradingOutcomeProvider

__all__ = [
    "DEFAULT_PROVIDERS",
    "CommerceOutcomeProvider",
    "OutcomeCandidate",
    "OutcomeProvider",
    "TradingOutcomeProvider",
    "compute_since_for_provider",
    "insert_outcome_candidates",
    "reconcile_user",
]
