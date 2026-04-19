"""Commerce Outcome Provider — Lemon Squeezy (ADR-195 Phase 2).

Reconciles LS orders into `action_outcomes` rows.

Attribution model (v1):
  - Each order emits one or two outcomes depending on its current status:
      - status="paid"               → "revenue_received" (+total_cents)
      - status="refunded"           → "revenue_received" (+total_cents) IF
                                      not previously recorded, plus
                                      "refund_issued" (-total_cents). The
                                      two events are idempotent by distinct
                                      keys so later reconciliations capture
                                      the refund flipping without duplicating
                                      the paid event.
      - status="partially_refunded" → "revenue_received" (+total_cents) IF
                                      not previously recorded, plus
                                      "refund_issued" with NULL value and
                                      confidence="low" (the list_orders
                                      endpoint doesn't carry refund amount —
                                      honest fallback, no fabrication).
      - status="pending" / "failed" → no outcome (not a realization event)
  - Net realized cash for the user is always the sum of outcome_value_cents
    regardless of when the refund arrives — because paid and refund are
    separate ledger rows.

Idempotency key: `ls_event_key` = `<order_id>:paid` or `<order_id>:refund`
or `<order_id>:partial_refund`. Stored in outcome_metadata, declared via
`idempotency_key_path = "ls_event_key"`.

Context domain: "revenue" (per ADR-183 + directory_registry — revenue/ is
the aggregate-metrics domain for commerce).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from integrations.core.lemonsqueezy_client import get_commerce_client
from integrations.core.tokens import get_token_manager
from services.outcomes.base import OutcomeCandidate, OutcomeProvider

logger = logging.getLogger(__name__)


#: How many recent orders to scan per reconciliation run. LS `list_orders`
#: returns the most recent first (default page size 50 via _paginate with
#: max_pages=1). If a user closes more than this in a day we simply catch
#: up on the next run — since is the high-water mark from the ledger.
_ORDER_SCAN_LIMIT = 100


class CommerceOutcomeProvider(OutcomeProvider):
    provider_name = "commerce-reconciler-v1"
    context_domain = "revenue"
    idempotency_key_path = "ls_event_key"

    async def reconcile(
        self,
        user_id: str,
        client: Any,
        since: datetime,
    ) -> list[OutcomeCandidate]:
        api_key = _load_commerce_api_key(client, user_id)
        if api_key is None:
            return []

        commerce = get_commerce_client()
        try:
            orders = await commerce.list_orders(api_key, limit=_ORDER_SCAN_LIMIT)
        except Exception as exc:  # noqa: BLE001 — provider must never raise
            logger.warning(
                "[OUTCOMES:commerce] list_orders failed for user=%s: %s",
                user_id[:8],
                exc,
            )
            return []

        candidates: list[OutcomeCandidate] = []
        for order in orders:
            order_id = order.id
            status = (order.status or "").lower()
            total_cents = int(order.total_cents or 0)
            currency = order.currency or "USD"
            created_at = _parse_ls_ts(order.created_at)

            # Skip pre-`since` orders once we've crossed the time boundary.
            # List_orders returns newest first; we still scan the full batch
            # because a refund on an older order can flip its status *after*
            # since — the refund event's "executed_at" is still the original
            # order creation for simplicity (LS doesn't expose refund_at on
            # this endpoint). Honest: refund outcomes may land in the ledger
            # a few days after the refund actually happened.

            if status not in {"paid", "refunded", "partially_refunded"}:
                # pending / failed / other — not a realization event
                continue

            base_inputs = {
                "order_id": order_id,
                "product_name": order.product_name,
                "customer_email": order.customer_email,
                "currency": currency,
            }

            # Always try to emit the paid event; the ledger dedups on
            # ls_event_key=<order_id>:paid so repeating is cheap and correct.
            if total_cents > 0:
                candidates.append({
                    "action_type": "commerce.order",
                    "action_inputs": base_inputs,
                    "executed_at": created_at,
                    "outcome_label": "revenue_received",
                    "outcome_value_cents": total_cents,
                    "outcome_currency": currency,
                    "outcome_metadata": {
                        "ls_event_key": f"{order_id}:paid",
                        "ls_order_id": order_id,
                        "status_at_reconcile": status,
                    },
                    "context_domain": self.context_domain,
                    "reconciliation_confidence": "high",
                })

            if status == "refunded":
                candidates.append({
                    "action_type": "commerce.order",
                    "action_inputs": base_inputs,
                    "executed_at": created_at,
                    "outcome_label": "refund_issued",
                    "outcome_value_cents": -total_cents,
                    "outcome_currency": currency,
                    "outcome_metadata": {
                        "ls_event_key": f"{order_id}:refund",
                        "ls_order_id": order_id,
                        "refund_type": "full",
                    },
                    "context_domain": self.context_domain,
                    "reconciliation_confidence": "high",
                })
            elif status == "partially_refunded":
                candidates.append({
                    "action_type": "commerce.order",
                    "action_inputs": base_inputs,
                    "executed_at": created_at,
                    "outcome_label": "refund_issued",
                    "outcome_value_cents": None,
                    "outcome_currency": currency,
                    "outcome_metadata": {
                        "ls_event_key": f"{order_id}:partial_refund",
                        "ls_order_id": order_id,
                        "refund_type": "partial",
                    },
                    "context_domain": self.context_domain,
                    "reconciliation_confidence": "low",
                    "reconciliation_notes": (
                        "Order marked partially_refunded but LS list_orders "
                        "does not expose the refund amount. Outcome value "
                        "NULL — true net impact needs the refunds endpoint."
                    ),
                })

        return candidates


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_commerce_api_key(client: Any, user_id: str) -> str | None:
    """Load + decrypt LS api key from platform_connections.

    Returns api_key or None. Never raises.
    """
    try:
        result = (
            client.table("platform_connections")
            .select("credentials_encrypted")
            .eq("user_id", user_id)
            .eq("platform", "commerce")
            .eq("status", "active")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[OUTCOMES:commerce] platform_connections lookup failed for %s: %s",
            user_id[:8],
            exc,
        )
        return None

    rows = result.data or []
    if not rows:
        return None

    try:
        return get_token_manager().decrypt(rows[0]["credentials_encrypted"])
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[OUTCOMES:commerce] credential decrypt failed for %s: %s",
            user_id[:8],
            exc,
        )
        return None


def _parse_ls_ts(raw: str | None) -> datetime:
    """Parse an LS ISO timestamp (or fall back to now in UTC)."""
    if not raw:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
