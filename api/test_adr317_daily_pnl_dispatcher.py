"""ADR-317 regression gate — daily-P&L post-judgment dispatcher.

Locks the invariants that make this dispatcher canon-coherent:
  1. The opt-in gate is default-off (operator must set active: true).
  2. The dispatcher reads _money_truth.md windows correctly into the email.
  3. The Reviewer never gains the email tool (the architectural commitment
     this dispatcher exists to honor) — FREDDIE_PRIMITIVES stays clean.
  4. The wake.py post-judgment hook is gated on the outcome-reconciliation
     slug (costs nothing for any other recurrence).

Pure-offline assertions (no DB, no network). Run:
    .venv/bin/python -m pytest api/test_adr317_daily_pnl_dispatcher.py -q
or directly:
    .venv/bin/python api/test_adr317_daily_pnl_dispatcher.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.daily_pnl_email import (  # noqa: E402
    NOTIFICATION_SLUG,
    TRIGGER_SLUG,
    SENT_MARKER_PATH,
    build_headline,
    build_html,
    is_opted_in,
    _already_sent_today,
    _parse_money_truth_windows,
)

PASS = 0
FAIL = 0


def check(name: str, cond: bool) -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}")


# ── 1. opt-in gate is default-off ──────────────────────────────────────────
OPTED_IN = """
operator_notifications:
  - slug: daily_pnl_reconciliation
    active: true
  - slug: signal_fire_alert
    active: false
"""
OPTED_OUT = """
operator_notifications:
  - slug: daily_pnl_reconciliation
    active: false
"""
NO_BLOCK = "deliverable_preferences:\n  - slug: pre-market-brief\n"

check("opt-in true → sends", is_opted_in(OPTED_IN) is True)
check("opt-in false → does not send", is_opted_in(OPTED_OUT) is False)
check("no operator_notifications block → does not send (default-off)", is_opted_in(NO_BLOCK) is False)
check("empty/None preferences → does not send", is_opted_in(None) is False)
check("notification slug is daily_pnl_reconciliation", NOTIFICATION_SLUG == "daily_pnl_reconciliation")
check("trigger slug is outcome-reconciliation", TRIGGER_SLUG == "outcome-reconciliation")

# ── 2. _money_truth.md windows parse + render ──────────────────────────────
MONEY_TRUTH = """---
last_reconciled: 2026-06-04T21:00:00Z
windows:
  7d:
    realized_pnl_usd: 1240.50
    fills: 12
    win_rate: 0.583
    expectancy_usd: 89.25
    sharpe: 1.42
  30d:
    realized_pnl_usd: 5215.20
    fills: 48
    win_rate: 0.604
    expectancy_usd: 73.10
    sharpe: 1.58
---
# money truth body
"""
windows = _parse_money_truth_windows(MONEY_TRUTH)
check("parses windows frontmatter", "windows" in windows and "7d" in windows["windows"])
headline = build_headline(windows)
check("headline carries 7d P&L sign + fills", "+$1,240.50" in headline and "12 fills" in headline)
html = build_html(windows, "https://app.yarnnn.com/home")
check("html renders 30d row", "exp +$73.10" in html or "+$5,215.20" in html)
check("html is pointer-only (deep-link CTA, no action button)", "Open cockpit" in html and "submit_order" not in html)

# bootstrap / empty windows degrade honestly (no fabricated numbers)
EMPTY_MT = "---\nlast_reconciled: 2026-06-04T21:00:00Z\nwindows: {}\n---\n"
empty_windows = _parse_money_truth_windows(EMPTY_MT)
empty_html = build_html(empty_windows, "https://app.yarnnn.com/home")
check("empty windows → honest bootstrap copy, no fake numbers", "bootstrap phase" in empty_html.lower())

# ── 3. Reviewer never gains the email tool (the commitment this honors) ─────
try:
    from services.primitives.registry import FREDDIE_PRIMITIVES

    tool_names = {
        t.get("name") if isinstance(t, dict) else getattr(t, "name", None)
        for t in FREDDIE_PRIMITIVES
    }
    check(
        "FREDDIE_PRIMITIVES excludes platform_email_send_to_operator",
        "platform_email_send_to_operator" not in tool_names,
    )
except Exception as exc:  # noqa: BLE001
    check(f"FREDDIE_PRIMITIVES importable ({exc})", False)

# ── 4. wake.py hook is slug-gated ──────────────────────────────────────────
wake_src = (Path(__file__).resolve().parent / "services" / "wake.py").read_text()
check(
    "wake.py gates dispatcher on outcome-reconciliation slug",
    'recurrence.slug == "outcome-reconciliation"' in wake_src
    and "maybe_send_daily_pnl_email" in wake_src,
)


# ── 5. idempotency — once per UTC day (the 2026-06-04 double-fire fix) ───────
class _FakeTable:
    def __init__(self, content):
        self._content = content

    def select(self, *a, **k):
        return self

    def eq(self, *a, **k):
        return self

    def limit(self, *a, **k):
        return self

    def execute(self):
        class R:
            pass

        r = R()
        r.data = [{"content": self._content}] if self._content is not None else []
        return r


class _FakeClient:
    def __init__(self, content):
        self._content = content

    def table(self, *_a, **_k):
        return _FakeTable(self._content)


_today = "2026-06-04"
sent_marker = f"# marker\nlast_sent_date: '{_today}'\nlast_headline: \"x\"\n"
check(
    "already-sent-today TRUE when marker matches today",
    _already_sent_today(_FakeClient(sent_marker), "u", _today) is True,
)
check(
    "already-sent-today FALSE for a different date (new day → send)",
    _already_sent_today(_FakeClient(sent_marker), "u", "2026-06-05") is False,
)
check(
    "already-sent-today FALSE when no marker exists yet",
    _already_sent_today(_FakeClient(None), "u", _today) is False,
)
check(
    "sent-marker lives under /workspace/persona/ (system-authored, not Reviewer-locked)",
    SENT_MARKER_PATH.startswith("/workspace/persona/"),
)

# ── 6. CTA points at the live landing route, not the dead /overview stub ────
from services.deep_links import overview_url  # noqa: E402

cta = overview_url()
check("CTA targets /desktop (HOME_ROUTE), not the dead /overview stub",
      "/desktop" in cta and "/overview" not in cta)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
