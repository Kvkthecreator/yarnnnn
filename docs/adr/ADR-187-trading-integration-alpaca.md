# ADR-187: Trading Integration — Alpaca as Execution Platform

> **Status**: Proposed
> **Date**: 2026-04-16
> **Related**: ADR-138 (Agents as Work Units), ADR-141 (Unified Execution), ADR-151/152 (Context Domains / Directory Registry), ADR-153 (Platform Content Sunset — live API reads, no mirrored cache), ADR-158 (Platform Bot Ownership), ADR-176 (Work-First Agent Model), ADR-183 (Commerce Substrate — fourth platform class pattern)
> **Extends**: ADR-147 (GitHub Platform Integration — Direct API client pattern), ADR-166 (Registry Coherence Pass — output_kind taxonomy)

---

## Context

### The proof-of-concept thesis

YARNNN's agent framework — persistent workspace, recurring task execution, accumulating context domains, multi-agent coordination — can be validated most rigorously by closing the loop against a domain with objective, measurable outcomes. Financial markets provide that: agents gather data, produce analysis files, generate trading signals, execute trades, and measure results in dollars. The P&L is the feedback signal. No subjectivity, no "did the user find this useful" ambiguity.

This ADR adds trading as the fifth platform class. The integration follows the same architectural patterns as Slack, Notion, GitHub, and Commerce (ADR-183): Direct API client, platform tools in `platform_tools.py`, platform bot ownership (ADR-158), and context domains for accumulated intelligence.

### Why Alpaca

| Requirement | Alpaca |
|---|---|
| Paper-to-live parity | Same API, same code, flip `paper=True/False` |
| Commission | Zero for self-directed individual cash accounts |
| Minimum deposit | None (cash account) |
| Fractional shares | $1 minimum, 2000+ US equities |
| Asset classes | US stocks, ETFs, options, crypto — single unified API |
| Auth | API key + secret (same pattern as Commerce/Lemon Squeezy) |
| Rate limits | 200 req/min (generous for daily-cadence agents) |
| Python SDK | Official `alpaca-py` library |
| MCP server | Official `alpaca-mcp-server` exists (validates AI agent trading as first-class use case) |

### Scope: personal validation, not a product

This integration is for personal proof-of-concept validation. No multi-user trading infrastructure, no regulatory considerations, no subscriber-facing trading signals. One workspace, one Alpaca account, one user. The goal is to validate the agent framework's closed-loop capability: data → analysis → decision → execution → measurement → learning.

---

## Decisions (all locked)

### 1. Trading is the fifth platform class

| Class | Platforms | Auth | Data flow |
|---|---|---|---|
| **Communication** | Slack | OAuth | Live reads during task execution |
| **Document** | Notion | OAuth | Live reads during task execution |
| **Work artifact** | GitHub | OAuth | Live reads during task execution |
| **Commerce** | Lemon Squeezy | API key | Live reads + webhook-driven writes |
| **Trading** | Alpaca (first) | API key + secret | Live reads + agent-initiated writes |

Same `platform_connections` table. Same encrypted credential storage. Same `platform_tools.py` pattern. Same agent-mediated observation pattern (ADR-158).

**Key characteristic**: Trading platforms have a write-back path with real-world financial consequences. Unlike Slack (post a message) or Commerce (create a product), a trading write is an irreversible market order. The agent pipeline must surface order details in workspace files before execution, enabling human review during the paper-trading validation phase. Live-trading automation is a graduated capability, not a default.

### 2. Two context domains: `markets/` and `portfolio/`

| Domain | Type | Contains | Written by |
|---|---|---|---|
| `markets/` | canonical | Per-asset entity files (price history, fundamentals, signal history, news) | Trading Bot + Researcher |
| `portfolio/` | canonical | Account state, positions, trade history, P&L tracking | Trading Bot |

Both canonical (not temporal). Market intelligence and portfolio history are permanent accumulated knowledge — the same reasoning that makes `customers/` and `revenue/` canonical in ADR-183.

**Entity structure (markets/):**
```
/workspace/context/markets/
├── _tracker.md                      # Watchlist coverage, data freshness per asset
├── _analysis.md                     # Cross-asset synthesis (sector rotation, correlation)
├── {ticker-slug}/                   # e.g., aapl/, btc-usd/, spy/
│   ├── profile.md                   # Fundamentals: sector, market cap, key metrics, description
│   ├── price_history.md             # Accumulated daily data (append newest-first)
│   ├── signals.md                   # Signal history with outcomes (append newest-first)
│   └── news.md                      # Recent news/events affecting this asset (append newest-first)
```

**Entity structure (portfolio/):**
```
/workspace/context/portfolio/
├── _tracker.md                      # Account value, cash, buying power, total P&L
├── _analysis.md                     # Portfolio-level synthesis (concentration, risk, performance attribution)
├── positions/
│   └── {ticker-slug}.md             # Per-position: entry price, current price, P&L, size, thesis
├── history/
│   └── {YYYY-MM}.md                 # Monthly trade log (all executions, chronological)
└── performance/
    └── {YYYY-MM}.md                 # Monthly performance snapshot (returns, benchmark comparison, signal accuracy)
```

**File write modes** (per workspace-conventions.md v8):
- `profile.md` — **overwrite** each cycle (current state)
- `price_history.md`, `signals.md`, `news.md` — **append newest-first** (temporal log, capped at 90 days)
- `_analysis.md` — **overwrite** each cycle (synthesis)
- `positions/{ticker}.md` — **overwrite** (current position state; file deleted when position closed)
- `history/{YYYY-MM}.md` — **append newest-first** (trade execution log)
- `performance/{YYYY-MM}.md` — **overwrite** weekly (running monthly snapshot)

### 3. Trading Bot owns the trading context

Same pattern as platform bots (ADR-158): one bot, one platform, owned directories.

| Agent | Platform | Directories | Task types |
|---|---|---|---|
| Slack Bot | Slack | `slack/` | `slack-digest`, `slack-respond` |
| Notion Bot | Notion | `notion/` | `notion-digest`, `notion-update` |
| GitHub Bot | GitHub | `github/` | `github-digest` |
| Commerce Bot | Lemon Squeezy | `customers/`, `revenue/` | `commerce-digest`, `commerce-create-product`, etc. |
| **Trading Bot** | Alpaca | `markets/`, `portfolio/` | `trading-digest`, `trading-signal`, `trading-execute`, `portfolio-review` |

Trading Bot is NOT scaffolded at signup. Created when the user connects an Alpaca account — same lazy-creation pattern as Commerce Bot (ADR-183 Decision 3).

**Agent template:**
```python
"trading_bot": {
    "class": "platform-bot",
    "domain": "trading",
    "platform": "trading",
    "display_name": "Trading Bot",
    "tagline": "Tracks markets, generates signals, executes trades",
    "capabilities": [
        "read_trading", "write_trading",
        "summarize", "produce_markdown",
    ],
    "description": (
        "Monitors trading account activity, positions, and market data. "
        "Generates trading signals and executes orders via Alpaca API."
    ),
    "default_instructions": (
        "Monitor trading account and market data. Track positions, generate "
        "signals based on accumulated market intelligence, execute approved trades."
    ),
    "methodology": {
        "_playbook-outputs.md": (
            "# Trading Output Conventions\n\n"
            "## Signal Format\n"
            "Every signal entry must include: ticker, direction (buy/sell/hold), "
            "confidence (high/medium/low), reasoning (2-3 sentences), "
            "and suggested position size (% of portfolio).\n\n"
            "## Execution Log Format\n"
            "Every execution entry must include: timestamp, ticker, side, quantity, "
            "price, order_type, status, and link to originating signal.\n\n"
            "## Position Format\n"
            "Every position file must include: entry_date, entry_price, current_price, "
            "quantity, unrealized_pnl, thesis (why entered), and exit_criteria.\n"
        ),
    },
}
```

### 4. Market data via separate data API (not Alpaca)

Alpaca provides account/portfolio data (positions, orders, history). Market intelligence — daily prices, fundamentals, news — comes from a dedicated market data API.

| Provider | Free tier | Rate limit | Data |
|---|---|---|---|
| Alpha Vantage | 25 req/day | Per-key | Daily OHLCV, fundamentals, earnings, news sentiment |
| Finnhub | Generous free | 60 req/min | Real-time quotes, company profiles, news, filings |

Alpha Vantage for daily batch data (25 requests = 25 tickers/day, sufficient for a focused watchlist). Finnhub as supplementary for real-time quotes and news when needed.

Market data credentials stored in `platform_connections` with `platform="market_data"`, not conflated with the Alpaca trading connection. Separate concern: data observation vs. trade execution.

### 5. Four trading task types

| Task type | Output kind | Agent | Default schedule | Domains |
|---|---|---|---|---|
| `trading-digest` | `accumulates_context` | Trading Bot | Daily (market close) | reads: `markets/`, `portfolio/` · writes: `markets/`, `portfolio/` |
| `trading-signal` | `produces_deliverable` | Analyst + Researcher | Daily (pre-market or post-digest) | reads: `markets/`, `portfolio/`, `signals/` · writes: signals to task output |
| `trading-execute` | `external_action` | Trading Bot | Reactive (triggered by signal) | reads: signal output · writes: `portfolio/` |
| `portfolio-review` | `produces_deliverable` | Analyst | Weekly | reads: `portfolio/`, `markets/` · writes: performance report to task output |

**Step instructions:**

```python
STEP_INSTRUCTIONS = {

    "trading-digest": (
        "You are the Trading Bot. Your job is to sync your trading account "
        "and market data into the workspace.\n\n"
        "Steps:\n"
        "1. Read account status: platform_trading_get_account\n"
        "2. Read current positions: platform_trading_get_positions\n"
        "3. Read recent orders: platform_trading_get_orders\n"
        "4. For each asset on the watchlist, read market data: "
        "platform_trading_get_market_data\n"
        "5. Update portfolio/ domain:\n"
        "   - WriteFile: _tracker.md (account snapshot)\n"
        "   - WriteFile: positions/{ticker}.md for each open position\n"
        "   - WriteFile: history/{YYYY-MM}.md (append new executions)\n"
        "6. Update markets/ domain:\n"
        "   - WriteFile: {ticker}/price_history.md (append today's data)\n"
        "   - WriteFile: {ticker}/news.md (append notable items)\n"
        "   - WriteFile: _tracker.md (freshness update)\n\n"
        "Your output: digest of account state and market observations."
    ),

    "trading-signal": (
        "You are generating trading signals based on accumulated market "
        "intelligence and portfolio context.\n\n"
        "IMPORTANT: Read the workspace FIRST. Your value comes from "
        "accumulated context — price history, prior signal outcomes, "
        "portfolio performance, and market patterns observed over time.\n\n"
        "Steps:\n"
        "1. ReadFile: /workspace/context/portfolio/_tracker.md (current state)\n"
        "2. ReadFile: /workspace/context/portfolio/_analysis.md (portfolio assessment)\n"
        "3. For each watchlist asset:\n"
        "   - ReadFile: /workspace/context/markets/{ticker}/price_history.md\n"
        "   - ReadFile: /workspace/context/markets/{ticker}/signals.md (prior signals + outcomes)\n"
        "   - ReadFile: /workspace/context/markets/{ticker}/news.md\n"
        "4. Analyze: trend direction, momentum, support/resistance, news catalysts, "
        "prior signal accuracy for this asset\n"
        "5. Generate signals with format:\n"
        "   - Ticker, Direction (buy/sell/hold), Confidence (high/medium/low)\n"
        "   - Reasoning (2-3 sentences referencing accumulated data)\n"
        "   - Suggested position size (% of portfolio)\n"
        "   - Risk note (what would invalidate this signal)\n"
        "6. WriteFile: update /workspace/context/markets/{ticker}/signals.md "
        "(append this signal for future outcome tracking)\n\n"
        "Your output: today's signal report with actionable recommendations."
    ),

    "trading-execute": (
        "You are the Trading Bot. Your job is to execute trades based on "
        "approved trading signals.\n\n"
        "IMPORTANT: This task places real orders (or paper orders). "
        "Execute ONLY signals marked as approved in the signal output.\n\n"
        "Steps:\n"
        "1. Read the latest signal output from the trading-signal task\n"
        "2. Read current positions: platform_trading_get_positions\n"
        "3. Read account status: platform_trading_get_account\n"
        "4. For each approved signal:\n"
        "   - Validate: sufficient buying power, position size within limits\n"
        "   - Execute: platform_trading_submit_order\n"
        "   - Log: WriteFile to portfolio/history/{YYYY-MM}.md (append execution)\n"
        "   - Update: WriteFile to portfolio/positions/{ticker}.md\n"
        "5. Update portfolio/_tracker.md with new account state\n\n"
        "Position sizing rules:\n"
        "- Never exceed 10% of portfolio in a single position\n"
        "- Never exceed 5 open positions simultaneously\n"
        "- Always use limit orders (not market orders)\n"
        "- Set stop-loss at 5% below entry for all new positions\n\n"
        "Your output: execution confirmation with order details."
    ),

    "portfolio-review": (
        "You are producing a weekly portfolio performance review.\n\n"
        "Steps:\n"
        "1. ReadFile: /workspace/context/portfolio/_tracker.md\n"
        "2. ReadFile: /workspace/context/portfolio/history/{YYYY-MM}.md\n"
        "3. ReadFile: /workspace/context/portfolio/performance/{YYYY-MM}.md (if exists)\n"
        "4. For each position, read signals.md to correlate signal → outcome\n"
        "5. Compute:\n"
        "   - Weekly return (% and $)\n"
        "   - Signal accuracy (% of signals that were profitable)\n"
        "   - Best/worst trades with reasoning\n"
        "   - Benchmark comparison (SPY buy-and-hold equivalent)\n"
        "   - Portfolio concentration and risk assessment\n"
        "6. Produce report with:\n"
        "   - Section kind: metric-cards (portfolio KPIs)\n"
        "   - Section kind: trend-chart (cumulative return vs benchmark)\n"
        "   - Section kind: data-table (trade log with outcomes)\n"
        "   - Section kind: narrative (weekly commentary)\n"
        "7. WriteFile: /workspace/context/portfolio/performance/{YYYY-MM}.md\n"
        "8. WriteFile: /workspace/context/portfolio/_analysis.md (updated synthesis)\n\n"
        "Your output: weekly performance report with charts and metrics."
    ),
}
```

### 6. Platform tools: read and write separation

**Read tools (TRADING_TOOLS):**

```python
TRADING_TOOLS = [
    {
        "name": "platform_trading_get_account",
        "description": "Get trading account details: equity, cash, buying power, portfolio value, account status.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "platform_trading_get_positions",
        "description": "Get all current open positions with unrealized P&L, market value, cost basis.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "platform_trading_get_orders",
        "description": "Get recent orders (last 7 days) with status, fill price, and timestamps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by order status: open, closed, all. Default: all.",
                    "enum": ["open", "closed", "all"],
                },
                "limit": {
                    "type": "integer",
                    "description": "Max orders to return. Default: 50.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "platform_trading_get_market_data",
        "description": "Get daily price data for a ticker: open, high, low, close, volume. Returns last 30 trading days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, SPY, BTC/USD).",
                },
                "timeframe": {
                    "type": "string",
                    "description": "Data granularity: 1Day, 1Hour, 1Min. Default: 1Day.",
                    "enum": ["1Day", "1Hour", "1Min"],
                },
            },
            "required": ["ticker"],
        },
    },
    {
        "name": "platform_trading_get_portfolio_history",
        "description": "Get portfolio value history over time for performance tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "description": "History period: 1W, 1M, 3M, 6M, 1A. Default: 1M.",
                    "enum": ["1W", "1M", "3M", "6M", "1A"],
                },
            },
            "required": [],
        },
    },
]
```

**Write tools (TRADING_WRITE_TOOLS):**

```python
TRADING_WRITE_TOOLS = [
    {
        "name": "platform_trading_submit_order",
        "description": "Submit a trading order. Returns order ID and status. Use limit orders for controlled execution.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, SPY).",
                },
                "side": {
                    "type": "string",
                    "description": "Order side: buy or sell.",
                    "enum": ["buy", "sell"],
                },
                "qty": {
                    "type": "number",
                    "description": "Number of shares (supports fractional, e.g., 0.5).",
                },
                "order_type": {
                    "type": "string",
                    "description": "Order type: market, limit, stop, stop_limit. Prefer limit.",
                    "enum": ["market", "limit", "stop", "stop_limit"],
                },
                "limit_price": {
                    "type": "number",
                    "description": "Limit price. Required for limit and stop_limit orders.",
                },
                "stop_price": {
                    "type": "number",
                    "description": "Stop price. Required for stop and stop_limit orders.",
                },
                "time_in_force": {
                    "type": "string",
                    "description": "Time in force: day, gtc (good til cancelled). Default: day.",
                    "enum": ["day", "gtc"],
                },
            },
            "required": ["ticker", "side", "qty", "order_type"],
        },
    },
    {
        "name": "platform_trading_cancel_order",
        "description": "Cancel an open order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The Alpaca order ID to cancel.",
                },
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "platform_trading_close_position",
        "description": "Close an entire position for a ticker (sells all shares).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker to close position for.",
                },
            },
            "required": ["ticker"],
        },
    },
]
```

**Capability mapping:**
```python
# In PLATFORM_TOOLS_BY_CAPABILITY:
"read_trading": ["platform_trading_get_account", "platform_trading_get_positions",
                  "platform_trading_get_orders", "platform_trading_get_market_data",
                  "platform_trading_get_portfolio_history"],
"write_trading": ["platform_trading_submit_order", "platform_trading_cancel_order",
                   "platform_trading_close_position"],

# In CAPABILITY_PROVIDER_MAP:
"read_trading": "trading",
"write_trading": "trading",
```

### 7. Connect endpoint: API key auth (same pattern as Commerce)

```
POST /integrations/trading/connect
```

Request body:
```json
{
    "api_key": "...",
    "api_secret": "...",
    "paper": true
}
```

Flow:
1. Validate credentials via `alpaca_client.get_account()`
2. Encrypt and store in `platform_connections` with `platform="trading"`
3. Store `paper` flag in connection metadata (determines base URL)
4. Create Trading Bot agent (lazy scaffold — same as Commerce Bot)
5. Register `markets/` and `portfolio/` context domains
6. Create default `trading-digest` task (daily, essential=false)
7. Return account details (equity, cash, account number — masked)

**Paper-to-live transition**: Update the connection's `metadata.paper` flag and `metadata.base_url`. Same API key pair works for both environments. No code changes, no new connection — single flag flip via:

```
PATCH /integrations/trading/connect
{ "paper": false }
```

### 8. Graduated execution model

Trading writes have real financial consequences. The execution model graduates:

| Phase | Mode | Execution behavior |
|---|---|---|
| **Phase 0: Observation** | Paper, no execution | `trading-digest` + `trading-signal` only. Signals produced but not executed. Human reviews signal quality. |
| **Phase 1: Paper execution** | Paper, automated | `trading-execute` task enabled. Full loop runs on paper account. P&L tracked in workspace. Zero financial risk. |
| **Phase 2: Live execution** | Live, automated | Connection flipped to live. Same code, real money. Position sizing guardrails enforced. |

Phase transitions are manual (user flips `paper` flag and enables/disables `trading-execute` task). No automated graduation — the user decides when signal quality justifies real capital.

**Guardrails (enforced in `trading-execute` step instructions + client-side validation):**
- Max 10% of portfolio per position
- Max 5 simultaneous open positions
- Limit orders only (no market orders) — prevents slippage
- Stop-loss required on all new positions (5% default)
- Daily loss limit: if portfolio drops >3% in a day, `trading-execute` skips remaining signals and logs escalation

---

## Implementation

### Phase 1: Client + read tools + context domains (8h)

**New files:**
- `api/integrations/core/alpaca_client.py` — Alpaca Direct API client following `github_client.py` pattern
  - Singleton via `get_alpaca_client()`
  - `async def _request()` with retry logic (exponential backoff)
  - Rate limiting: 200 req/min (check response headers)
  - Methods: `get_account()`, `get_positions()`, `list_orders()`, `get_bars()`, `get_portfolio_history()`
  - Paper/live base URL switching via connection metadata

**Modified files:**
- `api/services/platform_tools.py` — Add `TRADING_TOOLS`, `PLATFORM_TOOLS_BY_PROVIDER["trading"]`, `PLATFORM_TOOLS_BY_CAPABILITY["read_trading"]`, `CAPABILITY_PROVIDER_MAP["read_trading"]`, `_handle_trading_tool()` handler
- `api/services/directory_registry.py` — Add `markets/` and `portfolio/` domain entries (canonical, not temporal)
- `api/services/agent_framework.py` — Add `trading_bot` to `AGENT_TEMPLATES`, `CAPABILITIES["read_trading"]`
- `api/routes/integrations.py` — Add `POST /integrations/trading/connect` endpoint

**Dependencies:** `pip install alpaca-py` on API + Scheduler services. Alpha Vantage client: lightweight HTTP wrapper, no library needed (JSON REST API).

### Phase 2: Digest + signal task types (4h)

**Modified files:**
- `api/services/task_types.py` — Add `trading-digest`, `trading-signal`, `portfolio-review` task type definitions + step instructions
- `api/services/workspace_init.py` — Trading Bot + default tasks scaffolded on connect (not at signup)

**Validation:** Run `trading-digest` task, verify market data and portfolio state written correctly to context domains.

### Phase 3: Write tools + execution task (4h)

**Modified files:**
- `api/integrations/core/alpaca_client.py` — Add write methods: `submit_order()`, `cancel_order()`, `close_position()`
- `api/services/platform_tools.py` — Add `TRADING_WRITE_TOOLS`, `PLATFORM_TOOLS_BY_CAPABILITY["write_trading"]`, extend `_handle_trading_tool()` for write operations
- `api/services/agent_framework.py` — Add `CAPABILITIES["write_trading"]`
- `api/services/task_types.py` — Add `trading-execute` task type + step instructions

**Validation:** Run full loop on Alpaca paper account. Verify: signal generated → order placed → position appears → portfolio updated.

### Phase 4: Portfolio review + performance tracking (3h)

**Modified files:**
- `api/services/task_types.py` — Finalize `portfolio-review` step instructions with section kind guidance (metric-cards, trend-chart, data-table)
- Workspace: verify performance/{YYYY-MM}.md and _analysis.md are written correctly

**Validation:** After 5+ paper trades, `portfolio-review` produces a meaningful performance report with signal accuracy metrics and benchmark comparison.

### Phase 5: Live trading (1h)

- `PATCH /integrations/trading/connect` endpoint for paper-to-live transition
- Verify guardrails fire correctly (position limits, stop-loss, daily loss limit)
- Fund Alpaca account, flip the switch

---

## Registry updates summary

| Registry | Addition |
|---|---|
| `WORKSPACE_DIRECTORIES` | `markets/` (canonical), `portfolio/` (canonical) |
| `AGENT_TEMPLATES` | `trading_bot` (class: platform-bot) |
| `CAPABILITIES` | `read_trading`, `write_trading` |
| `TASK_TYPES` | `trading-digest`, `trading-signal`, `trading-execute`, `portfolio-review` |
| `PLATFORM_TOOLS_BY_PROVIDER` | `trading: TRADING_TOOLS + TRADING_WRITE_TOOLS` |
| `PLATFORM_TOOLS_BY_CAPABILITY` | `read_trading: [...]`, `write_trading: [...]` |
| `CAPABILITY_PROVIDER_MAP` | `read_trading: "trading"`, `write_trading: "trading"` |

DB migration: Add `trading_bot` to `agents_role_check` constraint. (Migration 148.)

---

## Cost model

### Infrastructure costs

| Component | Cost | Notes |
|---|---|---|
| Alpaca account | $0 | No fees, no minimum, commission-free |
| Alpha Vantage | $0 | Free tier: 25 req/day — see watchlist constraint below |
| Alpaca market data | $0 | Basic plan included; real-time requires $9/mo upgrade (defer) |

### Alpha Vantage free tier constraint

25 req/day total. Each ticker needs at minimum 1 call for daily OHLCV. Fundamentals + news = 2-3 calls/ticker. Practical watchlist sizes:

| Calls/ticker/day | Max tickers | Use case |
|---|---|---|
| 1 (price only) | 25 | Broad price monitoring, no fundamentals |
| 2 (price + fundamentals) | 12 | Standard tracking with company data |
| 3 (price + fundamentals + news) | 8 | Full intelligence per ticker |

**Recommendation:** Start with 8-12 tickers at 2 calls/ticker. Reserve 1-3 daily calls for ad-hoc Researcher queries. If the watchlist needs to grow beyond 12, upgrade to Alpha Vantage Premium ($50/mo, 75 req/min) or switch primary data source to Finnhub (free 60 req/min, more generous for bulk daily pulls).

### LLM costs per task run

Costs estimated at Sonnet $3/$15 MTok (input/output). Token counts account for cumulative input across tool rounds (each round re-sends the system prompt + conversation history).

| Task | Input tokens | Tool rounds | Est. cost/run | Frequency | Notes |
|---|---|---|---|---|---|
| `trading-digest` | 8-15K cumulative | 3-5 | ~$0.04-0.06 | Daily | Scales with watchlist size: 5 platform read calls + N ticker data pulls + 6+ WriteFile calls. 10 tickers ≈ $0.05, 20 tickers ≈ $0.08. |
| `trading-signal` | 15-25K cumulative | 1-2 | ~$0.06-0.10 | Daily (trading days) | Reads accumulated context: price_history + signals + news per ticker. 90-day price history per ticker is ~500-1K tokens. 10 tickers × 3 files = substantial context even when pre-gathered. |
| `trading-execute` | 3-5K cumulative | 1-3 | ~$0.01 | Triggered | Small: reads signal output + positions + account, places 1-5 orders. Cheapest task. |
| `portfolio-review` | 15-20K cumulative | 1-2 | ~$0.08-0.12 | Weekly | Full month's trade history + positions + market context. Generates charts via RuntimeDispatch (section-kind rendering, ADR-177). |

### Monthly projection (10-ticker watchlist)

| Task | Runs/month | Cost/run | Monthly |
|---|---|---|---|
| `trading-digest` | 30 | $0.05 | $1.50 |
| `trading-signal` | 22 (trading days) | $0.08 | $1.76 |
| `trading-execute` | ~15 (not every signal fires) | $0.01 | $0.15 |
| `portfolio-review` | 4 | $0.10 | $0.40 |
| **Total** | | | **~$3.80/mo** |

**Scaling with watchlist size:** At 20 tickers, digest and signal costs roughly double → ~$6-7/mo. At 25 tickers (AV free tier max with price-only), ~$7-8/mo. The dominant cost driver is `trading-signal` because it reads the most accumulated context per run.

---

## What this validates

If the full loop runs successfully for 30 days on paper trading:

1. **Framework proof**: File-system-native agents can close a complete loop — observe → analyze → decide → execute → measure
2. **Accumulation proof**: Signal accuracy should improve as the workspace accumulates more price history, prior signal outcomes, and pattern data
3. **Multi-agent proof**: Different agents (Trading Bot for data, Analyst for signals, Trading Bot for execution) coordinate through workspace files, not direct communication
4. **Quality signal**: P&L vs. buy-and-hold benchmark provides an objective, non-gameable quality metric

If signal accuracy exceeds 55% and portfolio returns beat SPY buy-and-hold over 30 days of paper trading, proceed to Phase 5 (live). If not, the workspace files reveal exactly where the analysis is failing — which signals were wrong, what data was missing, what patterns the agents missed — providing concrete direction for improvement.
