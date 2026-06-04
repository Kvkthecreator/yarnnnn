"""Daily P&L reconciliation email — post-judgment operator-addressing dispatcher (ADR-317).

This is the dispatcher the `operator_notifications.daily_pnl_reconciliation`
opt-in (alpha-trader bundle `_preferences.yaml`) describes but that did not
exist until ADR-317. It is the *send* half of the operator's "the Reviewer
runs my daily P&L confirmation alone" requirement.

Why a dispatcher and not a Reviewer tool call:
  `platform_email_send_to_operator` is deliberately and permanently EXCLUDED
  from `REVIEWER_PRIMITIVES` (registry.py ~L431; the 2026-05-25 v4 canary
  proved adding it collapsed verdict quality ~74% — tool-list size is
  corrosive to judgment for the Reviewer surface). The Reviewer therefore
  cannot compose-and-send the email itself. Instead it RUNS the judgment
  (the `outcome-reconciliation` recurrence folds fills into `_money_truth.md`
  and closes with a verdict); this dispatcher fires AFTER that judgment
  completes, reads the substrate the judgment produced, and sends the email
  out-of-band via the system Resend wire. Reviewer triggers; dispatcher sends.

Shape mirrors `daily_update_email.py` (ADR-202): deterministic counts read
from substrate → expository-pointer HTML (deep-link CTA, never an
action-on-email button) → `jobs.email.send_email`. The email is the
invitation back to the cockpit, not a replacement UX (FOUNDATIONS Axiom 6 /
Derived Principle 12 — channel legibility).

Observability, not consequential action (ADR-299 D5): the opt-in IS the
standing approval. AUTONOMY `delegation` does NOT gate this — it is the
operator's own inbox, no third-party write, same model ADR-040 + ADR-202
already use for the operator-addressing channel. Default-off in the bundle
(`active: false`); the operator flips it on per workspace.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# The recurrence whose completion triggers this dispatcher.
TRIGGER_SLUG = "outcome-reconciliation"

# The operator_notifications opt-in slug in _preferences.yaml.
NOTIFICATION_SLUG = "daily_pnl_reconciliation"

# Canonical substrate the dispatcher reads (the judgment's output).
MONEY_TRUTH_PATH = "/workspace/context/trading/_money_truth.md"
PREFERENCES_PATH = "/workspace/context/_shared/_preferences.yaml"


def _get_workspace_file_content(client: Any, user_id: str, path: str) -> Optional[str]:
    """Read a single workspace_files row's content by absolute path.

    Mirrors working_memory._get_workspace_file_sync — `content` is the
    denormalized head per ADR-209 Phase 5 (FTS/embedding indexes require it).
    """
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", path)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if rows and rows[0].get("content"):
            return rows[0]["content"].strip()
    except Exception as exc:  # noqa: BLE001 — best-effort read
        logger.warning("[daily-pnl] read failed for %s: %s", path, exc)
    return None


def is_opted_in(preferences_content: Optional[str]) -> bool:
    """True iff the operator flipped operator_notifications.daily_pnl_reconciliation active.

    Default-off discipline (ADR-299): the bundle ships `active: false`; this
    returns False unless the operator explicitly set `active: true`.
    """
    if not preferences_content:
        return False
    try:
        from services.review_policy import load_workspace_yaml

        parsed = load_workspace_yaml(preferences_content) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[daily-pnl] _preferences.yaml parse failed: %s", exc)
        return False

    for entry in parsed.get("operator_notifications") or []:
        if not isinstance(entry, dict):
            continue
        if entry.get("slug") == NOTIFICATION_SLUG:
            return bool(entry.get("active") is True)
    return False


def _parse_money_truth_windows(money_truth_content: str) -> dict:
    """Extract the windows frontmatter from _money_truth.md.

    Schema per /workspace/specs/performance-rollup.md:
        ---
        last_reconciled: ...
        windows:
          7d: {realized_pnl_usd, fills, win_rate, ...}
          30d: {...}
          90d: {...}
        ---
    Returns {} on any parse failure (the email degrades to an honest
    empty-state pointer rather than fabricating numbers).
    """
    import re

    import yaml

    match = re.match(r"^---\s*\n(.*?)\n---", money_truth_content, re.DOTALL)
    if not match:
        return {}
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[daily-pnl] _money_truth.md frontmatter parse failed: %s", exc)
        return {}
    return fm if isinstance(fm, dict) else {}


def _fmt_usd(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    sign = "+" if n >= 0 else "−"
    return f"{sign}${abs(n):,.2f}"


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def build_headline(windows: dict) -> str:
    """Deterministic one-line headline from the 7d window (the EOD horizon)."""
    w7 = (windows.get("windows") or {}).get("7d") or {}
    pnl = _fmt_usd(w7.get("realized_pnl_usd"))
    fills = w7.get("fills")
    fills_str = f"{int(fills)} fills" if isinstance(fills, (int, float)) else "— fills"
    win = _fmt_pct(w7.get("win_rate"))
    return f"7-day P&L {pnl} · {fills_str} · {win} win rate"


def build_html(windows: dict, overview_url: str) -> str:
    """Expository-pointer email body (ADR-202). Deep-link CTA, never an action button."""
    w = windows.get("windows") or {}
    last = windows.get("last_reconciled", "—")

    def _row(label: str, win: dict) -> str:
        pnl = _fmt_usd(win.get("realized_pnl_usd"))
        fills = win.get("fills")
        fills_str = str(int(fills)) if isinstance(fills, (int, float)) else "—"
        wr = _fmt_pct(win.get("win_rate"))
        exp = _fmt_usd(win.get("expectancy_usd"))
        sharpe = win.get("sharpe")
        sharpe_str = f"{float(sharpe):.2f}" if isinstance(sharpe, (int, float)) else "—"
        return (
            f'<tr><td style="padding:6px 12px 6px 0;color:#6b7280;">{label}</td>'
            f'<td style="padding:6px 12px;font-weight:600;">{pnl}</td>'
            f'<td style="padding:6px 12px;color:#374151;">{fills_str} fills</td>'
            f'<td style="padding:6px 12px;color:#374151;">{wr} win</td>'
            f'<td style="padding:6px 12px;color:#374151;">exp {exp}</td>'
            f'<td style="padding:6px 12px;color:#374151;">Sharpe {sharpe_str}</td></tr>'
        )

    rows = "".join(
        _row(label, w.get(key) or {})
        for label, key in (("7d", "7d"), ("30d", "30d"), ("90d", "90d"))
        if w.get(key)
    )
    if not rows:
        body = (
            '<p style="color:#374151;font-size:15px;">Outcome reconciliation ran, '
            "but no reconciled P&amp;L windows are populated yet — the operation "
            "is in its bootstrap phase (calibration begins from zero). Once fills "
            "reconcile, this email carries per-window P&amp;L.</p>"
        )
    else:
        body = (
            '<table style="border-collapse:collapse;font-size:14px;margin:8px 0 16px;">'
            f"{rows}</table>"
        )

    return f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <p style="color:#111;font-size:16px;font-weight:600;margin-bottom:4px;">Daily P&amp;L reconciliation</p>
        <p style="color:#9ca3af;font-size:12px;margin-top:0;">Reconciled through {last}</p>
        {body}
        <a href="{overview_url}" style="display:inline-block;background:#111;color:#fff;padding:10px 20px;text-decoration:none;border-radius:6px;margin-top:8px;">Open cockpit</a>
        <p style="color:#888;font-size:12px;margin-top:32px;">
            — yarnnn · your Reviewer reconciled today's outcomes
            <br>
            <a href="{overview_url}" style="color:#888;">Open cockpit</a>
        </p>
    </body>
    </html>
    """


def build_text(windows: dict, overview_url: str) -> str:
    w = windows.get("windows") or {}
    lines = ["Daily P&L reconciliation", ""]
    any_window = False
    for label, key in (("7d", "7d"), ("30d", "30d"), ("90d", "90d")):
        win = w.get(key)
        if not win:
            continue
        any_window = True
        lines.append(
            f"  {label}: {_fmt_usd(win.get('realized_pnl_usd'))} · "
            f"{int(win.get('fills', 0))} fills · {_fmt_pct(win.get('win_rate'))} win · "
            f"exp {_fmt_usd(win.get('expectancy_usd'))}"
        )
    if not any_window:
        lines.append("  Bootstrap phase — no reconciled P&L windows yet.")
    lines += ["", f"Open cockpit: {overview_url}", "", "— yarnnn"]
    return "\n".join(lines)


async def maybe_send_daily_pnl_email(client: Any, user_id: str) -> dict:
    """Post-judgment dispatcher — called after the outcome-reconciliation wake completes.

    Best-effort, never raises (caller wraps it; dispatch must not break on a
    notification failure). Returns a structured result for logging/telemetry.

    Gates, in order:
      1. operator opted in (operator_notifications.daily_pnl_reconciliation active)
      2. _money_truth.md exists (the judgment produced substrate to summarize)
      3. operator email resolvable
    """
    prefs = _get_workspace_file_content(client, user_id, PREFERENCES_PATH)
    if not is_opted_in(prefs):
        return {"sent": False, "reason": "not_opted_in"}

    money_truth = _get_workspace_file_content(client, user_id, MONEY_TRUTH_PATH)
    if not money_truth:
        return {"sent": False, "reason": "no_money_truth"}

    try:
        from jobs.unified_scheduler import get_user_email

        to = await get_user_email(client, user_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[daily-pnl] email lookup failed for %s: %s", user_id[:8], exc)
        to = None
    if not to:
        return {"sent": False, "reason": "no_operator_email"}

    windows = _parse_money_truth_windows(money_truth)

    from jobs.email import send_email
    from services.deep_links import overview_url as _overview_url

    overview = _overview_url()
    headline = build_headline(windows)
    result = await send_email(
        to=to,
        subject=f"Daily P&L — {headline}",
        html=build_html(windows, overview),
        text=build_text(windows, overview),
    )
    if result.success:
        logger.info("[daily-pnl] sent to %s (%s)", user_id[:8], headline)
        return {"sent": True, "headline": headline, "message_id": result.message_id}
    logger.warning("[daily-pnl] send failed for %s: %s", user_id[:8], result.error)
    return {"sent": False, "reason": "send_failed", "error": result.error}
