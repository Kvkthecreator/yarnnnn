"""Ledger helpers for action_outcomes (ADR-195 Phase 1).

Two responsibilities:
  1. compute_since_for_provider — "reconcile events after this timestamp"
     defaults to (most-recent reconciled_at for this user + provider) or
     a bootstrap window if no prior runs.
  2. insert_outcome_candidates — idempotent bulk insert with dedup on
     the provider's declared idempotency key.

No provider-specific logic lives here. Providers emit OutcomeCandidate
dicts; this module persists them.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from services.outcomes.base import OutcomeCandidate, OutcomeProvider

logger = logging.getLogger(__name__)


#: When a provider has no prior reconciliation rows for a user, reconcile
#: events going this far back to seed the ledger.
BOOTSTRAP_WINDOW_DAYS = 30


async def compute_since_for_provider(
    client: Any,
    user_id: str,
    provider: OutcomeProvider,
) -> datetime:
    """Return the timestamp from which `provider` should reconcile forward."""
    result = (
        client.table("action_outcomes")
        .select("reconciled_at")
        .eq("user_id", user_id)
        .eq("reconciled_by", provider.provider_name)
        .order("reconciled_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if rows:
        raw = rows[0]["reconciled_at"]
        # Supabase returns ISO strings; normalize to timezone-aware datetime
        if isinstance(raw, str):
            return _parse_iso(raw)
        if isinstance(raw, datetime):
            return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - timedelta(days=BOOTSTRAP_WINDOW_DAYS)


async def insert_outcome_candidates(
    client: Any,
    user_id: str,
    provider: OutcomeProvider,
    candidates: list[OutcomeCandidate],
) -> dict[str, int]:
    """Persist candidates with dedup on provider.idempotency_key_path.

    Returns a count breakdown: {"inserted": int, "skipped_duplicate": int,
    "skipped_invalid": int}.
    """
    if not candidates:
        return {"inserted": 0, "skipped_duplicate": 0, "skipped_invalid": 0}

    key_path = provider.idempotency_key_path

    # 1) Extract idempotency keys
    key_values: list[str] = []
    valid_candidates: list[OutcomeCandidate] = []
    skipped_invalid = 0
    for c in candidates:
        metadata = c.get("outcome_metadata") or {}
        key = metadata.get(key_path)
        if not key:
            skipped_invalid += 1
            logger.warning(
                "[OUTCOMES] %s emitted candidate without idempotency key "
                "(%s) — skipping: %s",
                provider.provider_name,
                key_path,
                c.get("action_type"),
            )
            continue
        key_values.append(str(key))
        valid_candidates.append(c)

    if not valid_candidates:
        return {"inserted": 0, "skipped_duplicate": 0, "skipped_invalid": skipped_invalid}

    # 2) Query existing keys for this user + provider to dedup
    existing = (
        client.table("action_outcomes")
        .select("outcome_metadata")
        .eq("user_id", user_id)
        .eq("reconciled_by", provider.provider_name)
        .execute()
    )
    existing_keys: set[str] = set()
    for row in existing.data or []:
        meta = row.get("outcome_metadata") or {}
        key = meta.get(key_path)
        if key:
            existing_keys.add(str(key))

    # 3) Build insert rows for non-duplicates
    rows_to_insert: list[dict[str, Any]] = []
    skipped_duplicate = 0
    for key, candidate in zip(key_values, valid_candidates):
        if key in existing_keys:
            skipped_duplicate += 1
            continue
        rows_to_insert.append(_candidate_to_row(user_id, provider, candidate))

    if not rows_to_insert:
        return {
            "inserted": 0,
            "skipped_duplicate": skipped_duplicate,
            "skipped_invalid": skipped_invalid,
        }

    # 4) Bulk insert
    insert_result = client.table("action_outcomes").insert(rows_to_insert).execute()
    inserted = len(insert_result.data or [])

    logger.info(
        "[OUTCOMES] %s: user=%s inserted=%d duplicate_skipped=%d invalid_skipped=%d",
        provider.provider_name,
        user_id[:8],
        inserted,
        skipped_duplicate,
        skipped_invalid,
    )

    return {
        "inserted": inserted,
        "skipped_duplicate": skipped_duplicate,
        "skipped_invalid": skipped_invalid,
    }


def _candidate_to_row(
    user_id: str,
    provider: OutcomeProvider,
    candidate: OutcomeCandidate,
) -> dict[str, Any]:
    """Translate an OutcomeCandidate to a DB row dict."""
    executed_at = candidate["executed_at"]
    if isinstance(executed_at, datetime):
        executed_at_iso = (
            executed_at.isoformat()
            if executed_at.tzinfo
            else executed_at.replace(tzinfo=timezone.utc).isoformat()
        )
    else:
        executed_at_iso = str(executed_at)

    row: dict[str, Any] = {
        "user_id": user_id,
        "action_type": candidate["action_type"],
        "action_inputs": candidate.get("action_inputs") or {},
        "executed_at": executed_at_iso,
        "outcome_label": candidate["outcome_label"],
        "outcome_metadata": candidate.get("outcome_metadata") or {},
        "outcome_currency": candidate.get("outcome_currency") or "USD",
        "reconciled_by": provider.provider_name,
        "reconciliation_confidence": candidate["reconciliation_confidence"],
        "context_domain": candidate["context_domain"],
    }
    value = candidate.get("outcome_value_cents")
    if value is not None:
        row["outcome_value_cents"] = int(value)
    proposal_id = candidate.get("proposal_id")
    if proposal_id:
        row["proposal_id"] = proposal_id
    notes = candidate.get("reconciliation_notes")
    if notes:
        row["reconciliation_notes"] = notes
    return row


def _parse_iso(raw: str) -> datetime:
    """Parse Supabase ISO timestamp string to timezone-aware datetime."""
    # Supabase returns e.g., "2026-04-19T12:34:56.789+00:00"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        # Truncate fractional seconds beyond microsecond precision if any
        if "." in raw:
            head, _, tail = raw.partition(".")
            # keep only first 6 digits of fractional + preserve timezone suffix
            digits, tz_suffix = "", ""
            for i, ch in enumerate(tail):
                if ch.isdigit():
                    digits += ch
                else:
                    tz_suffix = tail[i:]
                    break
            digits = digits[:6]
            raw = f"{head}.{digits}{tz_suffix}"
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            raise
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
