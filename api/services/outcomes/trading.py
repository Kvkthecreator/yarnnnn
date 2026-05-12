"""Trading Outcome Provider — Alpaca (ADR-195 Phase 1).

Reconciles Alpaca `filled` orders into `action_outcomes` rows.

Attribution model (v1):
  - Every filled SELL order is a realization event (closed round-trip or
    reducing a position). Emit one OutcomeCandidate per filled sell.
  - P&L is computed against the weighted average entry price of prior
    filled BUY orders for the same symbol within a rolling window.
    If no prior buys can be matched, outcome_value_cents is NULL and
    reconciliation_confidence is "low" — honest fallback, not a
    fabricated number.
  - Every filled BUY order is an entry event — recorded as an outcome
    with outcome_label="position_opened" and outcome_value_cents=NULL.
    This keeps the ledger dense enough for the AI reviewer to see
    the operator's action cadence, not just their realized P&L.

Idempotency key: alpaca_order_id in outcome_metadata.
Context domain: "trading".
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from integrations.core.alpaca_client import get_trading_client
from integrations.core.tokens import get_token_manager
from services.outcomes.base import OutcomeCandidate, OutcomeProvider

logger = logging.getLogger(__name__)


class TradingOutcomeProvider(OutcomeProvider):
    provider_name = "trading-reconciler-v1"
    context_domain = "trading"
    idempotency_key_path = "alpaca_order_id"

    async def reconcile(
        self,
        user_id: str,
        client: Any,
        since: datetime,
    ) -> list[OutcomeCandidate]:
        creds = _load_trading_credentials(client, user_id)
        if creds is None:
            return []
        api_key, api_secret, paper = creds

        alpaca = get_trading_client()
        try:
            orders = await alpaca.list_orders(
                api_key=api_key,
                api_secret=api_secret,
                paper=paper,
                status="closed",
                limit=100,
            )
        except Exception as exc:  # noqa: BLE001 — provider must never raise
            logger.warning(
                "[OUTCOMES:trading] list_orders failed for user=%s: %s",
                user_id[:8],
                exc,
            )
            return []

        filled_orders = [
            o for o in orders
            if o.get("status") == "filled"
            and o.get("filled_at")
            and _parse_alpaca_ts(o["filled_at"]) > since
        ]
        if not filled_orders:
            return []

        # Sort ascending so we can build a weighted-avg entry trace as we go
        filled_orders.sort(key=lambda o: _parse_alpaca_ts(o["filled_at"]))

        # P&L unification (2026-05-12): batch-fetch proposals by client_order_id
        # so we can recover signal_id + proposal_id for each filled order in
        # one DB hit, not per-order. Empty client_order_ids (orders submitted
        # before this feature shipped, or manual trades via Alpaca dashboard)
        # produce no attribution — that's correct behavior.
        proposal_lookup = _build_proposal_lookup(client, user_id, filled_orders)

        # entry_traces maps symbol -> list[{qty, price, signal_id}] for FIFO-ish matching.
        # Carrying signal_id on the entry lets the close-out sell inherit signal
        # attribution from the buy that opened the position.
        entry_traces: dict[str, list[dict[str, Any]]] = {}

        candidates: list[OutcomeCandidate] = []
        for order in filled_orders:
            symbol = (order.get("symbol") or "").upper()
            side = (order.get("side") or "").lower()
            qty = _safe_float(order.get("filled_qty") or order.get("qty"))
            price = _safe_float(order.get("filled_avg_price"))
            order_id = order.get("id")
            client_order_id = order.get("client_order_id") or ""
            filled_at = _parse_alpaca_ts(order["filled_at"])

            if not symbol or not order_id or qty <= 0 or price <= 0:
                continue

            # Recover signal attribution from the originating proposal (if any).
            proposal = proposal_lookup.get(client_order_id) if client_order_id else None
            signal_id = _extract_signal_id(proposal) if proposal else None
            proposal_id = proposal["id"] if proposal else None

            action_inputs = {
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "filled_avg_price": price,
                "order_type": order.get("type"),
            }

            if side == "buy":
                entry_traces.setdefault(symbol, []).append({
                    "qty": qty,
                    "price": price,
                    "signal_id": signal_id,
                })
                metadata: dict[str, Any] = {
                    "alpaca_order_id": str(order_id),
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "fill_price": price,
                }
                if signal_id:
                    metadata["signal_id"] = signal_id
                candidate: OutcomeCandidate = {
                    "action_type": "trading.submit_order",
                    "action_inputs": action_inputs,
                    "executed_at": filled_at,
                    "outcome_label": "position_opened",
                    "outcome_value_cents": None,
                    "outcome_metadata": metadata,
                    "context_domain": self.context_domain,
                    "reconciliation_confidence": "high",
                }
                if signal_id:
                    candidate["signal_id"] = signal_id
                if proposal_id:
                    candidate["proposal_id"] = proposal_id
                candidates.append(candidate)
                continue

            if side != "sell":
                continue

            # Match sell against accumulated entry trace (FIFO)
            realized_cents, matched_qty, avg_entry, attribution_signal_id = _consume_entry_fifo(
                entry_traces.get(symbol, []), qty, price
            )
            # Prefer the sell-order's own signal attribution (close-out
            # proposals carry the signal that originated the position via
            # their inputs); fall back to the entry trace's recovered signal
            # when the close is platform-side (stop-loss leg auto-fired by
            # Alpaca with no matching close proposal).
            effective_signal_id = signal_id or attribution_signal_id

            if matched_qty >= qty and avg_entry is not None:
                pnl_label = (
                    "closed_profit" if realized_cents > 0
                    else "closed_loss" if realized_cents < 0
                    else "closed_flat"
                )
                confidence = "high"
                notes = None
            else:
                # Not enough prior entries on record — honest fallback
                pnl_label = "closed_unknown"
                realized_cents = None  # type: ignore[assignment]
                confidence = "low"
                notes = (
                    "Matched {:.4f} of {:.4f} qty against prior entries; "
                    "remaining not attributable (entries pre-date ledger "
                    "window or were seeded outside this reconciler).".format(
                        matched_qty, qty,
                    )
                )

            metadata = {
                "alpaca_order_id": str(order_id),
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "fill_price": price,
            }
            if avg_entry is not None:
                metadata["avg_entry_price"] = round(avg_entry, 4)
                metadata["matched_qty"] = round(matched_qty, 6)
            if effective_signal_id:
                metadata["signal_id"] = effective_signal_id

            candidate = {
                "action_type": "trading.submit_order",
                "action_inputs": action_inputs,
                "executed_at": filled_at,
                "outcome_label": pnl_label,
                "outcome_value_cents": realized_cents,
                "outcome_metadata": metadata,
                "context_domain": self.context_domain,
                "reconciliation_confidence": confidence,
                "reconciliation_notes": notes,
            }
            if effective_signal_id:
                candidate["signal_id"] = effective_signal_id
            if proposal_id:
                candidate["proposal_id"] = proposal_id
            candidates.append(candidate)

        return candidates


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _load_trading_credentials(
    client: Any, user_id: str
) -> tuple[str, str, bool] | None:
    """Load + decrypt trading credentials from platform_connections.

    Returns (api_key, api_secret, paper) or None if no active connection.
    Never raises — reconciler must be tolerant of disconnected users.
    """
    try:
        result = (
            client.table("platform_connections")
            .select("credentials_encrypted, metadata")
            .eq("user_id", user_id)
            .eq("platform", "trading")
            .eq("status", "active")
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[OUTCOMES:trading] platform_connections lookup failed for %s: %s",
            user_id[:8],
            exc,
        )
        return None

    rows = result.data or []
    if not rows:
        return None
    row = rows[0]

    try:
        decrypted = get_token_manager().decrypt(row["credentials_encrypted"])
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[OUTCOMES:trading] credential decrypt failed for %s: %s",
            user_id[:8],
            exc,
        )
        return None

    if ":" not in decrypted:
        logger.warning(
            "[OUTCOMES:trading] credentials not in expected key:secret shape for %s",
            user_id[:8],
        )
        return None

    api_key, api_secret = decrypted.split(":", 1)
    metadata = row.get("metadata") or {}
    paper = bool(metadata.get("paper", True))
    return api_key, api_secret, paper


def _parse_alpaca_ts(raw: str) -> datetime:
    """Parse an Alpaca ISO timestamp to timezone-aware datetime (UTC)."""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _safe_float(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _consume_entry_fifo(
    entry_trace: list[dict[str, Any]],
    sell_qty: float,
    sell_price: float,
) -> tuple[int | None, float, float | None, str | None]:
    """FIFO-match a sell qty against the entry trace. Mutates entry_trace.

    Returns (realized_cents, matched_qty, weighted_avg_entry, attribution_signal_id).
      - realized_cents: signed integer cents (positive=profit). None only
        when matched_qty == 0 (unattributable).
      - matched_qty: how much of sell_qty was paired against entries.
      - weighted_avg_entry: avg entry price over matched_qty, None if 0.
      - attribution_signal_id: signal_id from the FIRST matched entry. If
        the sell consumed multiple entries from different signals, the
        first-entry signal wins. This is a deliberate simplification —
        cross-signal position-mixing is rare in practice and full split
        attribution would require splitting the outcome row itself.
    """
    remaining = sell_qty
    matched_qty = 0.0
    cost_basis = 0.0  # cumulative (qty * entry_price) for matched portion
    attribution_signal_id: str | None = None

    while remaining > 1e-9 and entry_trace:
        head = entry_trace[0]
        if attribution_signal_id is None:
            attribution_signal_id = head.get("signal_id")
        consume = min(head["qty"], remaining)
        cost_basis += consume * head["price"]
        matched_qty += consume
        remaining -= consume
        head["qty"] -= consume
        if head["qty"] <= 1e-9:
            entry_trace.pop(0)

    if matched_qty <= 0:
        return None, 0.0, None, None

    avg_entry = cost_basis / matched_qty
    realized_dollars = (sell_price - avg_entry) * matched_qty
    realized_cents = int(round(realized_dollars * 100))
    return realized_cents, matched_qty, avg_entry, attribution_signal_id


def _build_proposal_lookup(
    client: Any,
    user_id: str,
    filled_orders: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Fetch action_proposals by client_order_id (proposal.id) in one batch.

    Returns {client_order_id -> proposal_row}. Orders without a
    client_order_id, orders whose client_order_id doesn't match a proposal
    (e.g., manual trades), and DB errors all degrade to empty dict /
    missing keys silently — the reconciler must tolerate partial
    attribution.
    """
    proposal_ids = [
        o["client_order_id"]
        for o in filled_orders
        if o.get("client_order_id")
    ]
    if not proposal_ids:
        return {}

    try:
        result = (
            client.table("action_proposals")
            .select("id, inputs, action_type, task_slug")
            .eq("user_id", user_id)
            .in_("id", proposal_ids)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[OUTCOMES:trading] proposal batch lookup failed for %s: %s",
            user_id[:8],
            exc,
        )
        return {}

    rows = result.data or []
    # Proposal.id IS the client_order_id we wrote to Alpaca.
    return {str(row["id"]): row for row in rows}


def _extract_signal_id(proposal: dict[str, Any]) -> str | None:
    """Pull signal_id from a proposal row's inputs JSONB.

    The trade-proposal recurrence prompt mandates signal_id in entry
    proposals. Exit proposals may carry signal_id (when the close was
    triggered by an exit-condition rule per the operator's signal spec)
    or omit it (when the operator closed manually). Both shapes are valid;
    we return None when signal_id is absent.
    """
    inputs = proposal.get("inputs") or {}
    if not isinstance(inputs, dict):
        return None
    signal_id = inputs.get("signal_id")
    if not signal_id:
        return None
    return str(signal_id).strip() or None
