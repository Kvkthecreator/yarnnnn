"""One-shot test data seeder for seulkim88 workspace cockpit visual validation.

USER-AUTHORIZED 2026-04-28 (Path A) — fabricates narrative session_messages,
reviewer verdict, and agent task-completion entries on a real production
workspace for FE validation purposes only.

Inserts realistic-looking workspace_files + session_messages so the FE
cockpit panes render populated content. Safe parameterized inserts via
the Supabase Python client — no SQL string concatenation.

Run: SUPABASE_SERVICE_KEY=... python3 api/scripts/seed_seulkim_test_data.py

Idempotent on workspace_files (path-based lookup); session_messages will
duplicate if rerun (no natural unique key beyond sequence_number which
auto-advances).

Cleanup later:
  - DELETE FROM workspace_files WHERE user_id='2be30ac5-...' AND path IN (...)
  - DELETE FROM session_messages WHERE session_id='<bootstrapped session id>'
  - DELETE FROM action_proposals WHERE user_id='2be30ac5-...' AND status='pending'
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta

from supabase import create_client

URL = "https://noxgqcwynkzqabljjyon.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
USER_ID = "2be30ac5-b3cf-46b1-aeb8-af39cd351af4"  # seulkim88@gmail.com

if not SERVICE_KEY:
    print("ERROR: SUPABASE_SERVICE_KEY not set", file=sys.stderr)
    sys.exit(1)

client = create_client(URL, SERVICE_KEY)

PERF_SUMMARY = """---
generated_at: "2026-04-28T04:00:00Z"
positions_count: 5
pnl_30d_pct: 6.8
win_rate: 0.62
sharpe_30d: 1.34
max_drawdown_30d_pct: -3.2
schema_version: 1
---

# Workspace Performance Summary

**Headline (last 30 days):** +6.8% (target +5% / month). 18 closed trades · 11 wins · 7 losses · 62% win rate.

## By domain

- **Trading** — +$8,420 net realized · Sharpe 1.34 · Max drawdown -3.2% · NVDA + AMD long thesis carrying the book.
- **Commerce** — n/a (no commerce platform connected).

## Recent wins
- TSLA long Apr 12 -> Apr 24, +18% (+$3,040)
- AMD long Apr 8 -> Apr 22, +12% (+$2,140)

## Recent losses
- META short Apr 15, -2.1% (-$680, stopped out at +1.5%)
"""

PERF_FULL = """---
generated_at: "2026-04-28T04:00:00Z"
positions_count: 5
pnl_30d_pct: 6.8
win_rate: 0.62
schema_version: 1
---

# Portfolio Performance

Headline P&L (rolling 30d): **+6.8%** | 5 open positions | win rate 62% on 18 trades.

| Metric | Value |
|---|---|
| Net P&L (30d) | +$8,420 |
| Realized | +$5,180 |
| Unrealized | +$3,240 |
| Sharpe (30d) | 1.34 |
| Max drawdown (30d) | -3.2% |
| Win rate | 11/18 (62%) |
"""

PERF_POSITIONS = """---
generated_at: "2026-04-28T04:00:00Z"
positions_count: 5
schema_version: 1
---

# Open Positions

| Symbol | Qty | Avg Cost | Last | Unrealized | % |
|---|---|---|---|---|---|
| NVDA | 22 | $895.30 | $912.75 | +$383.90 | +1.9% |
| AMD | 35 | $158.40 | $172.60 | +$497.00 | +9.0% |
| TSLA | 12 | $210.00 | $244.50 | +$414.00 | +16.4% |
| GOOG | 8 | $172.85 | $178.20 | +$42.80 | +3.1% |
| AVGO | 0 | n/a | $1,212.00 | n/a | n/a |
"""

RISK_STATE = """---
generated_at: "2026-04-28T04:00:00Z"
schema_version: 1
---

# Risk State

Within budget. **2/3 positions used (67%)** | max-position cap **2.4%** vs 3% limit | daily-loss buffer **$1,820** of $1,950.

- Per-position cap: 3% of equity, peak 2.4%
- Max concurrent positions: 5 / 5
- Daily loss limit: $1,950, $130 drawn today
- Stop-loss: 5% per ADR-187 baseline
"""

OVERVIEW_OUTPUT = """# Workspace Intelligence — 2026-04-28

**Yesterday in your workspace:** 1 task ran (Signal evaluation), 3 trade proposals queued for review, portfolio +1.4% on the day.

## What needs your attention

- **3 pending trade proposals** in the Reviewer queue (NVDA buy, TSLA partial close, AVGO earnings reaction). 2 reversible, 1 at-market on AVGO carrying slippage flag.
- **AUTONOMY.md still flipped to paper-only.** Live trading gated until you flip the flag. Reviewer continues to surface verdicts under paper rules.
- **Risk budget healthy** — 2/3 position slots used, 6.7% of daily-loss buffer drawn.

## Trends

- 30-day expectancy positive (+0.62 Sharpe across closed trades). Win rate 62%.
- Signal generator producing 1-3 candidates / day, ~80% rejected by Reviewer at calibration thresholds.

_Synthesized by maintain-overview, runs daily 08:00 UTC._
"""


def upsert_file(path: str, content: str):
    """Insert or update a workspace_files row by (user_id, path)."""
    existing = (
        client.table("workspace_files")
        .select("id")
        .eq("user_id", USER_ID)
        .eq("path", path)
        .limit(1)
        .execute()
    )
    if existing.data:
        client.table("workspace_files").update({
            "content": content,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", existing.data[0]["id"]).execute()
        print(f"  updated  {path}  ({len(content)} bytes)")
    else:
        client.table("workspace_files").insert({
            "user_id": USER_ID,
            "path": path,
            "content": content,
            "content_type": "text/markdown",
            "lifecycle": "active",
        }).execute()
        print(f"  inserted {path}  ({len(content)} bytes)")


def main():
    print("\n=== A. Performance + portfolio substrate ===")
    upsert_file("/workspace/context/_performance_summary.md", PERF_SUMMARY)
    upsert_file("/workspace/context/portfolio/_performance.md", PERF_FULL)
    upsert_file("/workspace/context/portfolio/_positions.md", PERF_POSITIONS)
    upsert_file("/workspace/context/portfolio/_risk_state.md", RISK_STATE)

    print("\n=== B. maintain-overview output (IntelligenceCard) ===")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    upsert_file(f"/tasks/maintain-overview/outputs/{today}/output.md", OVERVIEW_OUTPUT)
    upsert_file("/tasks/maintain-overview/outputs/latest/output.md", OVERVIEW_OUTPUT)
    upsert_file(
        f"/tasks/maintain-overview/outputs/{today}/sys_manifest.json",
        json.dumps({
            "schema_version": 1,
            "task_slug": "maintain-overview",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sections": [],
        }),
    )

    print("\n=== C. session_messages (chat narrative for /chat surface) ===")
    session = (
        client.table("chat_sessions")
        .select("id")
        .eq("user_id", USER_ID)
        .eq("session_type", "thinking_partner")
        .eq("status", "active")
        .is_("agent_id", "null")
        .is_("task_slug", "null")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not session.data:
        print("  ERROR: no bootstrapped session found")
        sys.exit(2)
    session_id = session.data[0]["id"]
    print(f"  using session {session_id[:8]}...")

    last = (
        client.table("session_messages")
        .select("sequence_number")
        .eq("session_id", session_id)
        .order("sequence_number", desc=True)
        .limit(1)
        .execute()
    )
    seq = (last.data[0]["sequence_number"] + 1) if last.data else 1

    base_time = datetime.now(timezone.utc) - timedelta(hours=8)
    messages = [
        {
            "role": "system",
            "content": "Your workspace is ready. Tell me what you want to track or build.",
            "metadata": {"system_card": "workspace_init_complete", "summary": "Workspace ready", "pulse": "addressed", "weight": "housekeeping"},
            "minutes_ago": 480,
        },
        {
            "role": "user",
            "content": "Set me up to track NVDA, AMD, TSLA, GOOG and AVGO. Daily signal evaluation, paper trading only for now.",
            "metadata": {"summary": "Operator authored trading scope", "pulse": "addressed", "weight": "material"},
            "minutes_ago": 470,
        },
        {
            "role": "assistant",
            "content": "Got it — I've set up `trading-signal` and `portfolio-review` tasks pinned to NVDA, AMD, TSLA, GOOG, AVGO with daily evaluation. Paper-only mode is on; AUTONOMY.md flip is the gate to live. Reviewer principles default to capital-EV gating with $200 auto-approve threshold (commented out — flip when ready).",
            "metadata": {"summary": "Tasks scaffolded", "pulse": "addressed", "weight": "material"},
            "minutes_ago": 469,
        },
        {
            "role": "agent",
            "content": "Signal evaluation completed. 3 trade candidates surfaced for Reviewer: NVDA buy (limit $910.50), TSLA partial close (limit $248.20), AVGO earnings entry (market). All within risk budget. Output at /tasks/trading-signal/outputs/latest/.",
            "metadata": {
                "summary": "Trading-signal produced 3 candidates",
                "pulse": "periodic",
                "weight": "material",
                "task_slug": "trading-signal",
                "agent_slug": "analyst",
                "provenance": [{"path": "/tasks/trading-signal/outputs/latest/", "kind": "output_folder"}],
            },
            "minutes_ago": 90,
        },
        {
            "role": "reviewer",
            "content": "Reviewing 3 trading proposals. NVDA + TSLA: approve (within reversibility + risk caps). AVGO: defer to operator — at-market on $1.2K notional with slippage flag exceeds auto-approve confidence threshold under paper-discipline phase.",
            "metadata": {
                "summary": "Reviewer triaged 3 proposals - 2 approve, 1 defer",
                "pulse": "reactive",
                "weight": "material",
                "reviewer_identity": "ai:reviewer-sonnet-v1",
                "provenance": [{"path": "/workspace/review/decisions.md", "kind": "decisions_log"}],
            },
            "minutes_ago": 85,
        },
        {
            "role": "system",
            "content": "Daily back-office sweep: 2 ephemeral working files cleaned, 0 underperforming agents flagged, 1 idle proposal expiring in 90m (AVGO).",
            "metadata": {
                "system_card": "narrative_digest",
                "summary": "Back-office hygiene + cleanup",
                "pulse": "periodic",
                "weight": "housekeeping",
            },
            "minutes_ago": 60,
        },
        {
            "role": "agent",
            "content": "Portfolio review snapshot generated: 5 positions held, +6.8% rolling 30-day, 62% win rate, $130 of $1,950 daily loss buffer drawn. Substrate refreshed at /workspace/context/portfolio/_performance.md.",
            "metadata": {
                "summary": "Portfolio review snapshot",
                "pulse": "periodic",
                "weight": "material",
                "task_slug": "portfolio-review",
                "agent_slug": "analyst",
                "provenance": [{"path": "/workspace/context/portfolio/_performance.md", "kind": "frontmatter"}],
            },
            "minutes_ago": 30,
        },
    ]

    for msg in messages:
        ts = (base_time + timedelta(minutes=480 - msg["minutes_ago"])).isoformat()
        client.table("session_messages").insert({
            "session_id": session_id,
            "role": msg["role"],
            "content": msg["content"],
            "sequence_number": seq,
            "metadata": msg["metadata"],
            "created_at": ts,
        }).execute()
        print(f"  seq={seq}  role={msg['role']:9s}  {msg['metadata'].get('summary', '')[:50]}")
        seq += 1

    print(f"\n=== Done. Inserted {len(messages)} narrative entries. ===")


if __name__ == "__main__":
    main()
