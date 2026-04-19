"""Outcome Provider ABC + candidate shape (ADR-195 Phase 1).

Each domain (trading, commerce, email, ...) implements an OutcomeProvider
that pulls platform events and emits OutcomeCandidate dicts. The ledger
helpers then persist them idempotently into `action_outcomes`.

Providers own their own idempotency semantics via outcome_metadata keys
(e.g., trading stores alpaca_order_id; commerce stores ls_order_id).
The ledger helper dedups on (user_id, action_type, metadata_key).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal, TypedDict

logger = logging.getLogger(__name__)


class OutcomeCandidate(TypedDict, total=False):
    """A reconciled outcome proposal from a provider, ready for insertion."""

    # Required
    action_type: str
        # namespaced string matching action_proposals.action_type shape
    action_inputs: dict[str, Any]
    executed_at: datetime
    outcome_label: str
        # e.g., "closed_profit", "closed_loss", "refund_issued"
    context_domain: str
        # drives _performance.md routing; lives under /workspace/context/<domain>/
    reconciliation_confidence: Literal["high", "medium", "low"]

    # Optional / provider-specific
    outcome_value_cents: int | None
        # signed: +gain, -loss, None when not applicable / attribution missing
    outcome_currency: str  # default "USD"
    outcome_metadata: dict[str, Any]
        # MUST carry an idempotency key the provider documents in
        # `idempotency_key_path` so ledger.insert_outcome_candidates can
        # dedup across reconciliation runs.
    proposal_id: str | None
        # FK to action_proposals when the outcome resolves a proposal.
        # Elevates reconciliation_confidence to "high".
    reconciliation_notes: str | None


class OutcomeProvider(ABC):
    """Per-domain reconciler that turns platform events into outcomes.

    Contract:
      - reconcile(user_id, client, since) returns a list of OutcomeCandidate.
      - Idempotency is the provider's responsibility: each candidate's
        outcome_metadata MUST carry the key at
        `self.idempotency_key_path` so the ledger can skip duplicates.
      - Providers SHOULD be safe to run on empty / disconnected platforms
        (return []), not raise.
    """

    #: Stored in action_outcomes.reconciled_by. Versioned for future-proofing.
    provider_name: str

    #: Canonical context domain this provider writes to.
    context_domain: str

    #: JSONPath-ish string into outcome_metadata that uniquely identifies
    #: a platform event (e.g., "alpaca_order_id", "ls_order_id"). Used by
    #: the ledger for idempotency.
    idempotency_key_path: str

    @abstractmethod
    async def reconcile(
        self,
        user_id: str,
        client: Any,
        since: datetime,
    ) -> list[OutcomeCandidate]:
        """Pull platform events since `since` and return new outcome candidates.

        `client` is a Supabase service client (RLS-bypassing) — providers use
        it to look up platform_connections and write status breadcrumbs if
        they want. The ledger insert happens in ledger.insert_outcome_candidates,
        not in the provider, so providers stay focused on translation logic.

        On provider error (network, credential decryption, platform API),
        the provider should log and return [] rather than raise. The
        reconciliation dispatcher logs partial failures but doesn't let one
        provider's outage break others.
        """
        ...
