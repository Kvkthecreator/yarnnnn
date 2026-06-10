"""Ground-truth intake — the consequence pipe (ADR-195 Phase 1, ADR-330).

This module is the kernel-level contract for **ground-truth intake** (flow 3
of the four-flow operation loop per FOUNDATIONS Axiom 8 + ADR-332): reality's
verdict on the operation's own acts flowing back into substrate. The pipe that
carries it — the reconciler + its providers — is the **consequence pipe**.

`OutcomeProvider` is the code-level name for one intake source. Each source
(a platform API, an operator's own import, a future agent harvest) implements
the ABC and emits `OutcomeCandidate` dicts; the ledger helpers fold them
idempotently into the domain's ground-truth file
(`/workspace/operation/{domain}/_money_truth.md` for trading,
`_signal.md` for authored — the per-domain ground-truth substrate, Axiom 8).
The class/TypedDict names predate the Axiom-8 vocabulary and are preserved
unchanged per ADR-282 + ADR-330 D5 (the concept misled, not the symbol).

Per ADR-330 D2, every candidate carries `attestation` — who vouched for the
row (`platform | operator | agent`). Calibration records and surfaces the
attestation level so an agent-asserted number is never silently weighted like
an independent platform fill. This is what keeps the moat claim honest as
intake generalizes beyond platform providers.

Providers own their own idempotency semantics via outcome_metadata keys
(e.g., trading stores alpaca_order_id; commerce stores ls_order_id).
The ledger helper dedups on (user_id, action_type, metadata_key) — folded
into the per-domain `_money_truth.md` frontmatter, not a SQL table
(ADR-195 v2 moved persistence to the filesystem; the dropped `action_outcomes`
table no longer exists).
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
        # drives _money_truth.md routing; lives under /workspace/operation/<domain>/
    reconciliation_confidence: Literal["high", "medium", "low"]

    # Attestation — who vouched for this outcome (ADR-330 D2). Required in
    # spirit (every producer stamps it); kept in the optional block only
    # because TypedDict total=False applies to all keys and existing rows
    # written before this field default to "platform" on read.
    #   platform — external API independent of operator AND agent (gold)
    #   operator — operator's own import / manual entry (strong; agent
    #              can't fake it, operator can)
    #   agent    — an agent read/asserted the number (weak; corroboration-
    #              seeking, never silently raises confidence)
    # An operator-proxy import (ADR-294) stamps "operator" + carries an
    # `attestation_sublabel: "operator-proxy"` in outcome_metadata — kept a
    # sub-label, not a fourth enum value (ADR-330 §3 + open question #4).
    attestation: Literal["platform", "operator", "agent"]

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
    signal_id: str | None
        # Operator-declared signal that produced the proposal (e.g.,
        # "momentum-breakout", "mean-reversion-oversold" for alpha-trader).
        # Pulled from action_proposals.inputs.signal_id at reconciliation
        # time via the client_order_id → proposal lookup (2026-05-12 P&L
        # unification). Drives per-signal P&L bucketing in _money_truth.md.
        # None when no signal attribution was carried by the proposal
        # (e.g., manual operator trades not tied to a fired signal).
    reconciliation_notes: str | None
    retrospective: bool
        # ADR-330 D3: this row is an operator backfill of pre-YARNNN history,
        # not a live outcome. Defaults False. Orthogonal to `attestation`
        # (which says *who vouched*); `retrospective` says *is this backfill*.
        # The ledger segments retrospective rows in _money_truth.md so the
        # calibration mirror can present "live outcomes since activation"
        # separately from "backfilled history" and not let a large historical
        # dump swamp the live loop.


class OutcomeProvider(ABC):
    """One ground-truth intake source — turns reality's verdict into candidates.

    A provider is one source feeding the consequence pipe (ADR-330): a platform
    API (trading, commerce), the operator's own import (CSV / manual /
    operator-proxy), or a future agent harvest. Each emits OutcomeCandidate
    dicts the ledger folds into the per-domain ground-truth file.

    Contract:
      - reconcile(user_id, client, since) returns a list of OutcomeCandidate.
      - Every candidate MUST stamp `attestation` (ADR-330 D2). Platform
        providers stamp "platform"; the operator provider stamps "operator";
        any future agent-harvest provider stamps "agent".
      - Idempotency is the provider's responsibility: each candidate's
        outcome_metadata MUST carry the key at
        `self.idempotency_key_path` so the ledger can skip duplicates.
      - Providers SHOULD be safe to run on empty / disconnected platforms
        (return []), not raise.
    """

    #: Recorded in the per-domain _money_truth.md frontmatter (by_provider
    #: state) so compute_since can recover the last-reconciled high-water
    #: mark. Versioned for future-proofing.
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
        they want. The fold into _money_truth.md happens in
        ledger.fold_outcome_candidates, not in the provider, so providers stay
        focused on translation logic.

        On provider error (network, credential decryption, platform API),
        the provider should log and return [] rather than raise. The
        reconciliation dispatcher logs partial failures but doesn't let one
        provider's outage break others.
        """
        ...
