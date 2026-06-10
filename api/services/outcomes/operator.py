"""Operator ground-truth intake — CSV / manual import (ADR-330 D1 + D3).

The universal fallback for flow 3 (outcomes in): an operator whose ground
truth is NOT an Alpaca or Lemon Squeezy API hands the system their own
records. This provider reads a one-shot, operator-supplied CSV staged via
the upload path (`/workspace/uploads/{slug}.md` per ADR-249) and emits
OutcomeCandidate dicts stamped `attestation: "operator"` (ADR-330 D2 —
the agent can't fake it; the operator can, incl. unconsciously, so the
moat claim narrows from "judged against reality" to "judged against your
own records").

This is NOT a registered always-on provider — it is invoked on demand
against a named import via `reconcile_operator_import` (an addressed
invocation). `DEFAULT_PROVIDERS` stays platform-only for the daily
back-office reconciliation. There is exactly ONE intake pipe (the
reconciler + `fold_outcome_candidates`); this widens its set of producers,
it does not add a parallel path.

CSV contract (header row required; column order free):
  Required:
    - context_domain      e.g. "trading", "revenue", "authored"
    - outcome_label       e.g. "closed_profit", "revenue_received"
  Recommended:
    - executed_at         ISO timestamp; defaults to import time if absent
    - outcome_value_cents signed integer cents (+gain / -loss); blank → None
  Optional:
    - external_id         operator's own unique id for the row → idempotency
    - proposal_id         YARNNN action_proposals.id this row reconciles
                          (elevates reconciliation_confidence to "high")
    - retrospective       truthy → segmented backfill (ADR-330 D3)
    - outcome_currency    defaults "USD"
    - signal_id           operator-declared signal attribution
  Any other columns are carried into outcome_metadata verbatim.

Idempotency (ADR-330 §4.1): each row's key is the operator-provided
`external_id` when present, else `{import_batch_id}:{row-hash}` where
import_batch_id is a stable hash of the import content. Re-importing the
same CSV is a no-op, not a double-count — the ledger's
processed_event_keys dedup applies unchanged.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
from datetime import datetime, timezone
from typing import Any

from services.outcomes.base import OutcomeCandidate, OutcomeProvider

logger = logging.getLogger(__name__)


#: Truthy spellings accepted for the optional `retrospective` column.
_TRUTHY = {"1", "true", "yes", "y", "t", "retrospective", "backfill"}

#: Reserved columns the provider interprets directly; everything else on a
#: row is carried into outcome_metadata verbatim.
_RESERVED_COLUMNS = {
    "context_domain", "outcome_label", "executed_at", "outcome_value_cents",
    "external_id", "proposal_id", "retrospective", "outcome_currency",
    "signal_id", "action_type",
}


class OperatorOutcomeProvider(OutcomeProvider):
    """One ground-truth intake source: the operator's own CSV import.

    Constructed with the workspace path of a staged CSV upload. Reads that
    file's content from workspace_files and parses each row into an
    OutcomeCandidate. Unlike platform providers it ignores `since` — an
    operator import is a bounded, explicit act, not a high-water-mark poll.
    """

    provider_name = "operator-import-v1"
    idempotency_key_path = "operator_event_key"

    def __init__(self, import_path: str, default_context_domain: str | None = None):
        #: Workspace path of the staged CSV (e.g. "/workspace/uploads/trades.md").
        self.import_path = import_path
        #: Fallback domain for rows that omit context_domain. Also the
        #: provider's declared context_domain so compute_since + the
        #: empty-stub path have a home; rows may override per-row.
        self.context_domain = default_context_domain or "trading"

    async def reconcile(
        self,
        user_id: str,
        client: Any,
        since: datetime,  # noqa: ARG002 — operator import ignores high-water mark
    ) -> list[OutcomeCandidate]:
        content = self._read_import(client, user_id)
        if not content:
            return []

        # Stable batch id from content so re-importing the same file dedups.
        import_batch_id = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        try:
            rows = list(csv.DictReader(io.StringIO(content)))
        except Exception as exc:  # noqa: BLE001 — provider must never raise
            logger.warning(
                "[OUTCOMES:operator] CSV parse failed for user=%s path=%s: %s",
                user_id[:8], self.import_path, exc,
            )
            return []

        candidates: list[OutcomeCandidate] = []
        for idx, raw in enumerate(rows):
            candidate = self._row_to_candidate(raw, import_batch_id, idx)
            if candidate is not None:
                candidates.append(candidate)

        logger.info(
            "[OUTCOMES:operator] user=%s path=%s rows=%d candidates=%d batch=%s",
            user_id[:8], self.import_path, len(rows), len(candidates), import_batch_id,
        )
        return candidates

    # ------------------------------------------------------------------ #

    def _read_import(self, client: Any, user_id: str) -> str | None:
        """Read the staged CSV content from workspace_files. Never raises."""
        try:
            result = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", self.import_path)
                .limit(1)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[OUTCOMES:operator] import read failed for user=%s path=%s: %s",
                user_id[:8], self.import_path, exc,
            )
            return None
        rows = result.data or []
        if not rows:
            logger.warning(
                "[OUTCOMES:operator] no staged import at %s for user=%s",
                self.import_path, user_id[:8],
            )
            return None
        return rows[0].get("content") or None

    def _row_to_candidate(
        self, raw: dict[str, Any], import_batch_id: str, idx: int,
    ) -> OutcomeCandidate | None:
        """Translate one CSV row into an OutcomeCandidate. None on invalid row."""
        # Normalize keys (strip whitespace; lowercase for lookups).
        row = {(k or "").strip().lower(): (v.strip() if isinstance(v, str) else v)
               for k, v in raw.items()}

        outcome_label = row.get("outcome_label")
        if not outcome_label:
            logger.warning(
                "[OUTCOMES:operator] row %d missing outcome_label — skipping", idx,
            )
            return None

        context_domain = row.get("context_domain") or self.context_domain
        executed_at = self._parse_ts(row.get("executed_at"))
        value_cents = self._parse_int(row.get("outcome_value_cents"))
        retrospective = (str(row.get("retrospective") or "").lower() in _TRUTHY)

        # Idempotency key: operator external_id wins; else batch + row hash.
        external_id = row.get("external_id")
        if external_id:
            event_key = str(external_id)
        else:
            row_hash = hashlib.sha256(
                "|".join(f"{k}={row.get(k)}" for k in sorted(row)).encode("utf-8")
            ).hexdigest()[:12]
            event_key = f"{import_batch_id}:{row_hash}"

        # Carry non-reserved columns into metadata verbatim.
        extra_metadata = {
            k: v for k, v in row.items()
            if k not in _RESERVED_COLUMNS and v not in (None, "")
        }
        metadata: dict[str, Any] = {
            self.idempotency_key_path: event_key,
            "import_batch_id": import_batch_id,
            "import_path": self.import_path,
            **extra_metadata,
        }

        candidate: OutcomeCandidate = {
            "action_type": row.get("action_type") or f"{context_domain}.operator_import",
            "action_inputs": {},
            "executed_at": executed_at,
            "outcome_label": outcome_label,
            "outcome_value_cents": value_cents,
            "outcome_currency": row.get("outcome_currency") or "USD",
            "outcome_metadata": metadata,
            "context_domain": context_domain,
            # proposal_id linking elevates confidence per the ABC contract;
            # most operator imports are pre-YARNNN history with no link.
            "reconciliation_confidence": "high" if row.get("proposal_id") else "medium",
            "attestation": "operator",
        }
        if row.get("proposal_id"):
            candidate["proposal_id"] = str(row["proposal_id"])
        if row.get("signal_id"):
            candidate["signal_id"] = str(row["signal_id"])
        if retrospective:
            candidate["retrospective"] = True
        return candidate

    @staticmethod
    def _parse_ts(raw: Any) -> datetime:
        """Parse an ISO timestamp; fall back to import time (now, UTC)."""
        if not raw or not isinstance(raw, str):
            return datetime.now(timezone.utc)
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def _parse_int(raw: Any) -> int | None:
        """Parse signed integer cents; blank/invalid → None (honest, not 0)."""
        if raw in (None, ""):
            return None
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            return None


async def reconcile_operator_import(
    client: Any,
    user_id: str,
    import_path: str,
    default_context_domain: str | None = None,
) -> dict[str, Any]:
    """Addressed-invocation entrypoint for operator CSV import (ADR-330 D1).

    The operator fires "reconcile this import"; this runs the operator
    provider once against the named staged upload, folding through the SAME
    reconciler + ledger as platform providers. The daily back-office
    reconciliation (DEFAULT_PROVIDERS) is untouched — this is a separate,
    on-demand call, not a registered always-on provider.

    Returns the reconciler summary dict (provider counts + total_appended).
    """
    from services.outcomes.reconciler import reconcile_user

    provider = OperatorOutcomeProvider(import_path, default_context_domain)
    return await reconcile_user(client, user_id, providers=[provider])
