"""Ledger helpers for money-truth accumulation (ADR-195 v2).

Money-truth's canonical home per FOUNDATIONS Axiom 7 is:

    /workspace/context/{domain}/_performance.md

One file per domain. YAML-compatible JSON frontmatter (machine-readable
track record + idempotency key list) + narrative markdown body
(operator + Reviewer legible).

Two responsibilities, same shape as v1 (only the write target changes):

  1. compute_since_for_provider — "reconcile events after this timestamp"
     reads the current `_performance.md` frontmatter's last_reconciled_at
     for this provider, or falls back to a bootstrap window if the file
     doesn't exist.

  2. fold_outcome_candidates — idempotent fold of new candidates into
     `_performance.md`. Reads current file → filters against
     processed_event_keys → appends new events → rewrites frontmatter
     totals + body narrative → upserts to workspace_files.

No provider-specific logic lives here. Providers emit OutcomeCandidate
dicts; this module reconciles them into the domain's performance file.

Idempotency keys are namespaced as "{provider.idempotency_key_path}:
{metadata[key_path]}" — this prevents collisions between providers that
share a context_domain (e.g., a future TradingOutcomeProvider + a future
InteractiveBrokersOutcomeProvider both writing to domain=trading).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from services.outcomes.base import OutcomeCandidate, OutcomeProvider

logger = logging.getLogger(__name__)


#: When a provider has no prior reconciliation for a user, reconcile
#: events going this far back to seed the file.
BOOTSTRAP_WINDOW_DAYS = 30

#: How many entries to keep in each narrative section (Recent wins / losses).
NARRATIVE_WINDOW = 10

#: Rolling windows (days) tracked in _performance.md frontmatter per domain.
#: The longest window determines the event-retention horizon.
ROLLING_WINDOWS_DAYS = (7, 30, 90)
EVENT_RETENTION_DAYS = max(ROLLING_WINDOWS_DAYS)


# =============================================================================
# Public API
# =============================================================================


async def compute_since_for_provider(
    client: Any,
    user_id: str,
    provider: OutcomeProvider,
) -> datetime:
    """Return the timestamp from which `provider` should reconcile forward.

    Reads `/workspace/context/{provider.context_domain}/_performance.md` and
    returns the last reconciliation timestamp recorded for this provider.
    Falls back to a bootstrap window if the file doesn't exist yet or has
    no entries for this provider.
    """
    performance = await _read_performance_file(client, user_id, provider.context_domain)
    if performance is not None:
        by_provider = performance.get("by_provider") or {}
        provider_state = by_provider.get(provider.provider_name) or {}
        raw = provider_state.get("last_reconciled_at")
        if raw:
            return _parse_iso(raw)
    return datetime.now(timezone.utc) - timedelta(days=BOOTSTRAP_WINDOW_DAYS)


async def fold_outcome_candidates(
    client: Any,
    user_id: str,
    provider: OutcomeProvider,
    candidates: list[OutcomeCandidate],
) -> dict[str, int]:
    """Fold candidates into the domain's _performance.md.

    Returns a count breakdown:
      {"appended": int, "skipped_duplicate": int, "skipped_invalid": int}
    """
    if not candidates:
        return {"appended": 0, "skipped_duplicate": 0, "skipped_invalid": 0}

    key_path = provider.idempotency_key_path

    # 1) Validate + extract namespaced idempotency keys
    keyed: list[tuple[str, OutcomeCandidate]] = []
    skipped_invalid = 0
    for c in candidates:
        metadata = c.get("outcome_metadata") or {}
        raw_key = metadata.get(key_path)
        if not raw_key:
            skipped_invalid += 1
            logger.warning(
                "[OUTCOMES] %s emitted candidate without idempotency key "
                "(%s) — skipping: %s",
                provider.provider_name,
                key_path,
                c.get("action_type"),
            )
            continue
        namespaced = f"{key_path}:{raw_key}"
        keyed.append((namespaced, c))

    if not keyed:
        return {"appended": 0, "skipped_duplicate": 0, "skipped_invalid": skipped_invalid}

    # 2) Load current file state (frontmatter + body) or initialize
    performance = await _read_performance_file(client, user_id, provider.context_domain)
    if performance is None:
        performance = _init_performance(provider.context_domain)

    processed_keys: set[str] = set(performance.get("processed_event_keys") or [])

    # 3) Filter out duplicates, fold the rest
    new_entries: list[OutcomeCandidate] = []
    skipped_duplicate = 0
    for namespaced, candidate in keyed:
        if namespaced in processed_keys:
            skipped_duplicate += 1
            continue
        processed_keys.add(namespaced)
        new_entries.append(candidate)

    if not new_entries:
        return {
            "appended": 0,
            "skipped_duplicate": skipped_duplicate,
            "skipped_invalid": skipped_invalid,
        }

    # 4) Update frontmatter state (totals, by_action_type, by_provider, rolling windows)
    _apply_entries(performance, new_entries, provider)
    performance["processed_event_keys"] = sorted(processed_keys)
    performance["last_reconciled_at"] = datetime.now(timezone.utc).isoformat()
    _update_provider_state(performance, provider)

    # 5) Render + write
    rendered = _render_performance_file(performance)
    ok = await _upsert_performance_file(
        client, user_id, provider.context_domain, rendered,
    )
    if not ok:
        logger.error(
            "[OUTCOMES] Upsert failed for %s / domain=%s — %d candidates NOT persisted",
            provider.provider_name,
            provider.context_domain,
            len(new_entries),
        )
        return {
            "appended": 0,
            "skipped_duplicate": skipped_duplicate,
            "skipped_invalid": skipped_invalid + len(new_entries),
        }

    # 6) ADR-195 Phase 5: route high-impact outcomes to the originating
    # task's feedback.md per ADR-181. Never blocks — failures log and
    # the outcome is still persisted to _performance.md above.
    try:
        from services.outcomes.high_impact import (
            load_high_impact_thresholds,
            write_feedback_entries_for_outcomes,
        )
        thresholds = load_high_impact_thresholds(client, user_id)
        if thresholds:
            await write_feedback_entries_for_outcomes(
                client, user_id, provider, new_entries, thresholds,
            )
        # When no thresholds declared, no writes happen (safe default).
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[OUTCOMES] high-impact actuation failed for %s / user=%s: %s",
            provider.provider_name, user_id[:8], exc,
        )

    logger.info(
        "[OUTCOMES] %s: user=%s domain=%s appended=%d duplicate_skipped=%d invalid_skipped=%d",
        provider.provider_name,
        user_id[:8],
        provider.context_domain,
        len(new_entries),
        skipped_duplicate,
        skipped_invalid,
    )

    return {
        "appended": len(new_entries),
        "skipped_duplicate": skipped_duplicate,
        "skipped_invalid": skipped_invalid,
    }


# =============================================================================
# File I/O
# =============================================================================


def _performance_path(context_domain: str) -> str:
    return f"/workspace/context/{context_domain}/_performance.md"


async def _read_performance_file(
    client: Any, user_id: str, context_domain: str,
) -> dict | None:
    """Load existing performance file state. Returns parsed frontmatter dict
    or None if file doesn't exist or can't be parsed.
    """
    path = _performance_path(context_domain)
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "[OUTCOMES] Failed to read %s for user=%s: %s",
            path, user_id[:8], exc,
        )
        return None

    rows = result.data or []
    if not rows:
        return None

    content = rows[0].get("content") or ""
    return _parse_performance_file(content)


async def _upsert_performance_file(
    client: Any, user_id: str, context_domain: str, content: str,
) -> bool:
    """Upsert `_performance.md` for the domain through Authored Substrate.

    ADR-209: authored_by="system:outcome-reconciliation" — the
    reconciler is a deterministic system actor (daily back-office task),
    not a cognitive layer. The revision chain captures each reconciliation
    cycle as an attributed revision.
    """
    path = _performance_path(context_domain)
    try:
        from services.authored_substrate import write_revision

        write_revision(
            client,
            user_id=user_id,
            path=path,
            content=content,
            authored_by="system:outcome-reconciliation",
            message=f"reconcile {context_domain} outcomes",
            summary=f"Money-truth track record for domain={context_domain}",
            tags=["_performance", context_domain, "money-truth"],
            lifecycle="active",
            content_type="text/markdown",
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[OUTCOMES] Upsert failed for %s user=%s: %s",
            path, user_id[:8], exc,
        )
        return False


# =============================================================================
# Parse / Render — JSON frontmatter + narrative body
# =============================================================================


def _parse_performance_file(content: str) -> dict | None:
    """Parse a rendered `_performance.md` back into the frontmatter dict.

    The file format is:
      ---
      {json-object}
      ---
      # <markdown body — derivable from frontmatter, not canonical>

    We only parse the frontmatter. The body is regenerated on each write.
    """
    if not content.strip().startswith("---"):
        return None
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None
    frontmatter_raw = parts[1].strip()
    if not frontmatter_raw:
        return None
    try:
        data = json.loads(frontmatter_raw)
    except json.JSONDecodeError:
        logger.warning("[OUTCOMES] Could not parse _performance.md frontmatter as JSON")
        return None
    if not isinstance(data, dict):
        return None
    return data


def _init_performance(context_domain: str) -> dict:
    """Initial state for a domain that has never been reconciled."""
    return {
        "domain": context_domain,
        "last_reconciled_at": None,
        "processed_event_keys": [],
        "totals": {
            "reconciled_event_count": 0,
            "aggregate_value_cents": 0,
            "currency": "USD",
        },
        "by_action_type": {},
        "by_provider": {},
        "recent_wins": [],
        "recent_losses": [],
        # ADR-195 Phase 3: compact time-series of reconciled events, used
        # to compute rolling windows at fold time. Bounded by
        # EVENT_RETENTION_DAYS — older entries are pruned on every fold.
        "events": [],
        # ADR-195 Phase 3: rolling-window summaries recomputed on every
        # fold from `events`. Consumers (AI Reviewer, daily-update) read
        # these without recomputing.
        "rolling_7d": _empty_window(),
        "rolling_30d": _empty_window(),
        "rolling_90d": _empty_window(),
    }


def _empty_window() -> dict:
    return {"count": 0, "value_cents": 0, "wins": 0, "losses": 0}


def _apply_entries(
    performance: dict,
    entries: list[OutcomeCandidate],
    provider: OutcomeProvider,
) -> None:
    """Apply a batch of new outcome entries to the performance state dict.

    Phase 3: also appends to the bounded events list + recomputes rolling
    windows. Window math is done once per fold so readers (AI Reviewer,
    daily-update) never need to recompute.
    """
    totals = performance.setdefault("totals", {
        "reconciled_event_count": 0,
        "aggregate_value_cents": 0,
        "currency": "USD",
    })
    by_action = performance.setdefault("by_action_type", {})
    wins: list[dict] = performance.setdefault("recent_wins", [])
    losses: list[dict] = performance.setdefault("recent_losses", [])
    events: list[dict] = performance.setdefault("events", [])

    for entry in entries:
        totals["reconciled_event_count"] = int(totals.get("reconciled_event_count", 0)) + 1
        value = entry.get("outcome_value_cents")
        if value is not None:
            totals["aggregate_value_cents"] = int(totals.get("aggregate_value_cents", 0)) + int(value)

        action_type = entry.get("action_type") or "unknown"
        action_state = by_action.setdefault(action_type, {
            "count": 0,
            "value_cents": 0,
            "wins": 0,
            "losses": 0,
        })
        action_state["count"] = int(action_state.get("count", 0)) + 1
        if value is not None:
            action_state["value_cents"] = int(action_state.get("value_cents", 0)) + int(value)
            if value > 0:
                action_state["wins"] = int(action_state.get("wins", 0)) + 1
            elif value < 0:
                action_state["losses"] = int(action_state.get("losses", 0)) + 1

        # Narrative windows: prepend newest, cap
        narrative_entry = _to_narrative_entry(entry, provider)
        if value is not None and value > 0:
            wins.insert(0, narrative_entry)
        elif value is not None and value < 0:
            losses.insert(0, narrative_entry)
        # Entries with NULL value (position_opened, closed_unknown, etc.)
        # are counted but not narrated — narrative focuses on realized P&L.

        # Phase 3: compact time-series entry for rolling-window math.
        # Only realized events (value_cents not None) contribute to
        # windows — open positions and unattributable outcomes don't.
        if value is not None:
            executed_at_iso = _executed_at_iso(entry.get("executed_at"))
            if executed_at_iso:
                events.append({
                    "executed_at": executed_at_iso,
                    "action_type": action_type,
                    "value_cents": int(value),
                })

    # Cap narrative windows
    performance["recent_wins"] = wins[:NARRATIVE_WINDOW]
    performance["recent_losses"] = losses[:NARRATIVE_WINDOW]

    # Phase 3: prune events older than EVENT_RETENTION_DAYS + recompute windows.
    performance["events"] = _prune_events(events)
    now = datetime.now(timezone.utc)
    for window_days in ROLLING_WINDOWS_DAYS:
        key = f"rolling_{window_days}d"
        performance[key] = _compute_window(performance["events"], now, window_days)


def _executed_at_iso(value: Any) -> str | None:
    """Normalize an executed_at field to an ISO string, or None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    if isinstance(value, str):
        try:
            # Validate parseability so window math doesn't trip later.
            _parse_iso(value)
            return value
        except Exception:
            return None
    return None


def _prune_events(events: list[dict]) -> list[dict]:
    """Drop events older than EVENT_RETENTION_DAYS. Returns sorted ascending."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=EVENT_RETENTION_DAYS)
    kept: list[dict] = []
    for ev in events:
        raw = ev.get("executed_at")
        if not raw:
            continue
        try:
            dt = _parse_iso(raw)
        except Exception:
            continue
        if dt >= cutoff:
            kept.append(ev)
    # Chronological ascending keeps window scans stable.
    kept.sort(key=lambda e: e.get("executed_at") or "")
    return kept


def _compute_window(events: list[dict], now: datetime, window_days: int) -> dict:
    """Compute {count, value_cents, wins, losses} for events in the last N days."""
    cutoff = now - timedelta(days=window_days)
    count = 0
    value_cents = 0
    wins = 0
    losses = 0
    for ev in events:
        raw = ev.get("executed_at")
        if not raw:
            continue
        try:
            dt = _parse_iso(raw)
        except Exception:
            continue
        if dt < cutoff:
            continue
        count += 1
        v = int(ev.get("value_cents", 0) or 0)
        value_cents += v
        if v > 0:
            wins += 1
        elif v < 0:
            losses += 1
    return {
        "count": count,
        "value_cents": value_cents,
        "wins": wins,
        "losses": losses,
    }


def _update_provider_state(performance: dict, provider: OutcomeProvider) -> None:
    """Track per-provider last_reconciled_at so compute_since can recover it."""
    by_provider = performance.setdefault("by_provider", {})
    by_provider[provider.provider_name] = {
        "last_reconciled_at": performance.get("last_reconciled_at"),
    }


def _to_narrative_entry(entry: OutcomeCandidate, provider: OutcomeProvider) -> dict:
    """Reduce a candidate to the compact shape the narrative body uses."""
    executed_at = entry.get("executed_at")
    if isinstance(executed_at, datetime):
        executed_at_iso = (
            executed_at.isoformat()
            if executed_at.tzinfo
            else executed_at.replace(tzinfo=timezone.utc).isoformat()
        )
    else:
        executed_at_iso = str(executed_at) if executed_at else None

    return {
        "executed_at": executed_at_iso,
        "action_type": entry.get("action_type"),
        "outcome_label": entry.get("outcome_label"),
        "value_cents": entry.get("outcome_value_cents"),
        "currency": entry.get("outcome_currency") or "USD",
        "metadata": {
            k: v for k, v in (entry.get("outcome_metadata") or {}).items()
            # Narrative shouldn't include the idempotency key itself
            if k != provider.idempotency_key_path
        },
    }


def _render_performance_file(performance: dict) -> str:
    """Render the full `_performance.md` (JSON frontmatter + markdown body)."""
    # Frontmatter: single JSON object, pretty-printed for legibility.
    frontmatter_json = json.dumps(
        performance, indent=2, sort_keys=False, default=str,
    )

    # Body: narrative derived from frontmatter. Regenerated every write.
    body_lines: list[str] = []
    domain = performance.get("domain") or "unknown"
    body_lines.append(f"# {domain.title()} Performance")
    body_lines.append("")

    totals = performance.get("totals") or {}
    agg = totals.get("aggregate_value_cents", 0) or 0
    count = totals.get("reconciled_event_count", 0) or 0
    body_lines.append(f"**Reconciled events:** {count}")
    body_lines.append(f"**Aggregate value:** {_format_cents(agg)}")
    last = performance.get("last_reconciled_at")
    if last:
        body_lines.append(f"**Last reconciled:** {last}")
    body_lines.append("")

    # Phase 3: rolling windows — "your book at three horizons"
    window_rows = []
    for window_days in ROLLING_WINDOWS_DAYS:
        w = performance.get(f"rolling_{window_days}d") or _empty_window()
        if w.get("count", 0) > 0:
            window_rows.append((f"{window_days}d", w))
    if window_rows:
        body_lines.append("## Rolling windows")
        body_lines.append("")
        body_lines.append("| Window | Count | Value | Wins | Losses |")
        body_lines.append("|---|---|---|---|---|")
        for label, w in window_rows:
            body_lines.append(
                f"| last {label} | {w.get('count', 0)} | "
                f"{_format_cents(w.get('value_cents', 0))} | "
                f"{w.get('wins', 0)} | {w.get('losses', 0)} |"
            )
        body_lines.append("")

    by_action = performance.get("by_action_type") or {}
    if by_action:
        body_lines.append("## By action type")
        body_lines.append("")
        body_lines.append("| Action | Count | Value | Wins | Losses |")
        body_lines.append("|---|---|---|---|---|")
        for action, state in sorted(by_action.items()):
            body_lines.append(
                f"| {action} | {state.get('count', 0)} | "
                f"{_format_cents(state.get('value_cents', 0))} | "
                f"{state.get('wins', 0)} | {state.get('losses', 0)} |"
            )
        body_lines.append("")

    wins = performance.get("recent_wins") or []
    if wins:
        body_lines.append("## Recent wins")
        body_lines.append("")
        for w in wins:
            body_lines.append(f"- {_narrative_line(w)}")
        body_lines.append("")

    losses = performance.get("recent_losses") or []
    if losses:
        body_lines.append("## Recent losses")
        body_lines.append("")
        for l in losses:
            body_lines.append(f"- {_narrative_line(l)}")
        body_lines.append("")

    if not by_action and not wins and not losses:
        body_lines.append(
            "_No realized outcomes yet. Open positions / pending events "
            "do not produce narrative entries until they close._"
        )
        body_lines.append("")

    body_lines.append(
        "<!-- This file is regenerated on every reconciliation run. "
        "Do not edit by hand — edits will be overwritten. -->"
    )

    return f"---\n{frontmatter_json}\n---\n\n" + "\n".join(body_lines) + "\n"


def _narrative_line(entry: dict) -> str:
    """One-line markdown bullet for a narrative wins/losses entry."""
    executed = entry.get("executed_at") or "unknown-time"
    label = entry.get("outcome_label") or "outcome"
    value = entry.get("value_cents")
    action = entry.get("action_type") or "unknown"
    metadata = entry.get("metadata") or {}

    # Format a brief metadata summary (symbol, product, etc.)
    meta_parts = []
    for key in ("symbol", "product_name", "side", "qty", "fill_price"):
        if key in metadata:
            meta_parts.append(f"{key}={metadata[key]}")
    meta_str = f" ({', '.join(meta_parts)})" if meta_parts else ""

    value_str = _format_cents(value) if value is not None else "n/a"
    return f"{executed} — {action} {label} {value_str}{meta_str}"


def _format_cents(cents: int | None) -> str:
    if cents is None:
        return "$0.00"
    sign = "-" if cents < 0 else ""
    abs_dollars = abs(cents) / 100
    return f"{sign}${abs_dollars:,.2f}"


# =============================================================================
# Time helpers
# =============================================================================


def _parse_iso(raw: str) -> datetime:
    """Parse a stored ISO timestamp to timezone-aware datetime (UTC-normalized)."""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        if "." in raw:
            head, _, tail = raw.partition(".")
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


# =============================================================================
# Cross-domain summary — /workspace/context/_performance_summary.md (Phase 3)
# =============================================================================


SUMMARY_PATH = "/workspace/context/_performance_summary.md"


async def write_performance_summary(
    client: Any, user_id: str, provider_domains: list[str],
) -> bool:
    """Regenerate `/workspace/context/_performance_summary.md` from per-domain files.

    Reads each `_performance.md` under `/workspace/context/{domain}/`,
    aggregates totals + rolling windows across domains, and writes a
    single cross-domain summary. This is the file the daily-update
    briefing (ADR-195 Phase 4) and the Reviewer (ADR-194 Phase 3) read
    when they want the operator's whole book at a glance.

    Currency assumption: USD across all domains. Alpha scope (Alpaca +
    Lemon Squeezy) is USD-only. Multi-currency aggregation is a future
    extension; until then, non-USD domains are included in per-domain
    sections but excluded from the cross-domain aggregate (with a note).

    Never raises — failures log and return False. The back-office task
    surfaces success/failure in its report.
    """
    try:
        domains_state: dict[str, dict] = {}
        seen_domains: set[str] = set()
        for domain in provider_domains:
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            perf = await _read_performance_file(client, user_id, domain)
            if perf is None:
                continue
            domains_state[domain] = perf

        summary = _build_summary_state(domains_state)
        rendered = _render_summary_file(summary)

        try:
            from services.authored_substrate import write_revision

            write_revision(
                client,
                user_id=user_id,
                path=SUMMARY_PATH,
                content=rendered,
                authored_by="system:outcome-reconciliation",
                message="rebuild cross-domain performance summary",
                summary="Cross-domain money-truth summary (ADR-195 Phase 3)",
                tags=["_performance_summary", "money-truth"],
                lifecycle="active",
                content_type="text/markdown",
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "[OUTCOMES] summary upsert failed for user=%s: %s",
                user_id[:8], exc,
            )
            return False
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "[OUTCOMES] summary generation crashed for user=%s: %s",
            user_id[:8], exc,
        )
        return False


def _build_summary_state(domains_state: dict[str, dict]) -> dict:
    """Aggregate per-domain performance state into a cross-domain summary dict."""
    aggregate_currency = "USD"
    non_usd_domains: list[str] = []

    aggregate_totals = {
        "reconciled_event_count": 0,
        "aggregate_value_cents": 0,
        "currency": aggregate_currency,
        "domains_covered": 0,
    }
    aggregate_windows = {
        f"rolling_{w}d": _empty_window() for w in ROLLING_WINDOWS_DAYS
    }

    per_domain: dict[str, dict] = {}
    latest_reconciled_at: str | None = None

    for domain, perf in domains_state.items():
        per_domain_currency = (perf.get("totals") or {}).get("currency") or "USD"
        per_domain[domain] = {
            "totals": perf.get("totals") or {},
            **{f"rolling_{w}d": perf.get(f"rolling_{w}d") or _empty_window()
               for w in ROLLING_WINDOWS_DAYS},
            "last_reconciled_at": perf.get("last_reconciled_at"),
        }
        last = perf.get("last_reconciled_at")
        if last and (latest_reconciled_at is None or last > latest_reconciled_at):
            latest_reconciled_at = last

        if per_domain_currency != aggregate_currency:
            non_usd_domains.append(domain)
            continue  # excluded from cross-domain aggregate

        aggregate_totals["domains_covered"] += 1
        totals = perf.get("totals") or {}
        aggregate_totals["reconciled_event_count"] += int(
            totals.get("reconciled_event_count", 0) or 0
        )
        aggregate_totals["aggregate_value_cents"] += int(
            totals.get("aggregate_value_cents", 0) or 0
        )
        for window_days in ROLLING_WINDOWS_DAYS:
            key = f"rolling_{window_days}d"
            src = perf.get(key) or _empty_window()
            dst = aggregate_windows[key]
            dst["count"] += int(src.get("count", 0) or 0)
            dst["value_cents"] += int(src.get("value_cents", 0) or 0)
            dst["wins"] += int(src.get("wins", 0) or 0)
            dst["losses"] += int(src.get("losses", 0) or 0)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest_reconciled_at": latest_reconciled_at,
        "domains": per_domain,
        "aggregate": {
            "totals": aggregate_totals,
            **aggregate_windows,
        },
        "non_aggregate_domains": non_usd_domains,
    }


def _render_summary_file(summary: dict) -> str:
    """Render `_performance_summary.md` (JSON frontmatter + narrative body)."""
    frontmatter_json = json.dumps(summary, indent=2, sort_keys=False, default=str)

    body: list[str] = []
    body.append("# Workspace Money-Truth Summary")
    body.append("")
    generated = summary.get("generated_at")
    latest = summary.get("latest_reconciled_at")
    if generated:
        body.append(f"**Generated:** {generated}")
    if latest:
        body.append(f"**Latest domain reconciliation:** {latest}")
    body.append("")

    domains = summary.get("domains") or {}
    aggregate = summary.get("aggregate") or {}
    aggregate_totals = aggregate.get("totals") or {}
    covered = aggregate_totals.get("domains_covered", 0) or 0

    if not domains:
        body.append(
            "_No reconciled outcomes in any domain yet. Connect a platform "
            "(Alpaca trading, Lemon Squeezy commerce) and the daily outcome "
            "reconciler will populate this file._"
        )
        body.append("")
    else:
        # Cross-domain aggregate (USD-only)
        body.append("## Across all domains (USD)")
        body.append("")
        body.append(
            f"**Domains covered:** {covered} / {len(domains)}"
        )
        agg_value = aggregate_totals.get("aggregate_value_cents", 0) or 0
        agg_count = aggregate_totals.get("reconciled_event_count", 0) or 0
        body.append(f"**Reconciled events:** {agg_count}")
        body.append(f"**Aggregate value:** {_format_cents(agg_value)}")
        body.append("")

        window_rows = []
        for window_days in ROLLING_WINDOWS_DAYS:
            w = aggregate.get(f"rolling_{window_days}d") or _empty_window()
            if w.get("count", 0) > 0:
                window_rows.append((f"{window_days}d", w))
        if window_rows:
            body.append("| Window | Count | Value | Wins | Losses |")
            body.append("|---|---|---|---|---|")
            for label, w in window_rows:
                body.append(
                    f"| last {label} | {w.get('count', 0)} | "
                    f"{_format_cents(w.get('value_cents', 0))} | "
                    f"{w.get('wins', 0)} | {w.get('losses', 0)} |"
                )
            body.append("")

        non_agg = summary.get("non_aggregate_domains") or []
        if non_agg:
            body.append(
                f"_Note: excluded {len(non_agg)} domain(s) from aggregate "
                f"due to non-USD currency ({', '.join(non_agg)}). "
                f"Multi-currency aggregation is a future extension._"
            )
            body.append("")

        # Per-domain breakout
        body.append("## By domain")
        body.append("")
        for domain in sorted(domains.keys()):
            state = domains[domain]
            totals = state.get("totals") or {}
            value = totals.get("aggregate_value_cents", 0) or 0
            count = totals.get("reconciled_event_count", 0) or 0
            currency = totals.get("currency") or "USD"
            body.append(f"### {domain}")
            body.append("")
            body.append(f"**Events:** {count}  |  **Value:** {_format_cents(value)} ({currency})")
            last_dom = state.get("last_reconciled_at")
            if last_dom:
                body.append(f"**Last reconciled:** {last_dom}")

            # Per-domain rolling windows
            dom_rows = []
            for window_days in ROLLING_WINDOWS_DAYS:
                w = state.get(f"rolling_{window_days}d") or _empty_window()
                if w.get("count", 0) > 0:
                    dom_rows.append((f"{window_days}d", w))
            if dom_rows:
                body.append("")
                body.append("| Window | Count | Value | Wins | Losses |")
                body.append("|---|---|---|---|---|")
                for label, w in dom_rows:
                    body.append(
                        f"| last {label} | {w.get('count', 0)} | "
                        f"{_format_cents(w.get('value_cents', 0))} | "
                        f"{w.get('wins', 0)} | {w.get('losses', 0)} |"
                    )
            body.append("")

    body.append(
        "<!-- Regenerated on every reconciliation run by the "
        "back-office-outcome-reconciliation task. Do not edit by hand. -->"
    )

    return f"---\n{frontmatter_json}\n---\n\n" + "\n".join(body) + "\n"
