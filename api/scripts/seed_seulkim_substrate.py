"""Substrate-only test data seeder for seulkim88 workspace cockpit visual validation.

Path B (substrate-only) per user authorization 2026-04-28. Inserts workspace_files
that drive the SnapshotPane, PerformanceSnapshot, TradingPortfolioMetadata,
and IntelligenceCard renderers. Does NOT fabricate session_messages (no
narrative impersonation of reviewer/agent system actors).

Run: SUPABASE_SERVICE_KEY=... api/venv/bin/python3 api/scripts/seed_seulkim_substrate.py

Cleanup later:
  DELETE FROM workspace_files WHERE user_id='2be30ac5-b3cf-46b1-aeb8-af39cd351af4'
    AND path IN (
      '/workspace/context/_performance_summary.md',
      '/workspace/context/portfolio/_performance.md',
      '/workspace/context/portfolio/_positions.md',
      '/workspace/context/portfolio/_risk_state.md',
      '/tasks/maintain-overview/outputs/latest/output.md',
      '/tasks/maintain-overview/outputs/2026-04-28/output.md',
      '/tasks/maintain-overview/outputs/2026-04-28/sys_manifest.json'
    );
  DELETE FROM action_proposals WHERE user_id='2be30ac5-b3cf-46b1-aeb8-af39cd351af4'
    AND status='pending';
"""

import os
import sys
import json
from datetime import datetime, timezone

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

**Headline (last 30 days):** +6.8% (target +5% / month). 18 closed trades | 11 wins | 7 losses | 62% win rate.

## By domain

- **Trading** — +$8,420 net realized | Sharpe 1.34 | Max drawdown -3.2% | NVDA + AMD long thesis carrying the book.
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

    print("\n=== Done. Substrate-only seed complete (Path B). ===")
    print("Chat narrative remains empty (no session_messages fabricated).")


if __name__ == "__main__":
    main()
