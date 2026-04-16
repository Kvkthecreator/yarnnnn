# ADR-187: Trading Integration — Alpaca as Execution Platform

> **Status**: Proposed
> **Date**: 2026-04-16
> **Related**: ADR-138 (Agents as Work Units), ADR-141 (Unified Execution), ADR-151/152 (Context Domains / Directory Registry), ADR-153 (Platform Content Sunset — live API reads, no mirrored cache), ADR-158 (Platform Bot Ownership), ADR-176 (Work-First Agent Model), ADR-183 (Commerce Substrate — fourth platform class pattern)
> **Extends**: ADR-147 (GitHub Platform Integration — Direct API client pattern), ADR-166 (Registry Coherence Pass — output_kind taxonomy)

---

## Context

### The closed-loop thesis

YARNNN's agent framework — persistent workspace, recurring task execution, accumulating context domains, multi-agent coordination — can be validated most rigorously by closing the loop against a domain with objective, measurable outcomes. Financial markets provide that: agents gather data, produce analysis, generate trading signals, execute trades, and measure results in dollars. The P&L is the feedback signal. No subjectivity, no "did the user find this useful" ambiguity.

This ADR adds trading as the fifth platform class. The integration follows the same architectural patterns as Slack, Notion, GitHub, and Commerce (ADR-183): Direct API client, platform tools in `platform_tools.py`, platform bot ownership (ADR-158), context domains in the directory registry (ADR-152), and task types in the task type registry (ADR-166).

**This is a full system test.** The integration is product-grade — same registries, same scaffolding paths, same initialization flows as every other platform. The trading domain stress-tests the framework on closed-loop execution with real-world consequences: data → analysis → decision → execution → measurement → learning. If the framework handles this without special-casing, it can handle any domain.

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

### Regulatory constraint (not scope limiter)

The integration is architecturally product-grade. The regulatory constraint is: trading writes have irreversible financial consequences. If multi-user exposure introduces regulatory burden that outweighs the value, the platform connection stays private (never exposed in public onboarding). Users who want trading bring their own Alpaca API key, at their own risk — same model as Commerce (bring your own Lemon Squeezy key). The code doesn't know the difference between one user and many.

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

### 2. Two context domains: `trading/` and `portfolio/`

Following directory registry conventions (ADR-152). Both canonical (not temporal) — same reasoning that makes `customers/` and `revenue/` canonical in ADR-183. Market intelligence and portfolio history are permanent accumulated knowledge.

**`trading/` domain** — per-asset entity files tracking price, fundamentals, and signal history:

```python
"trading": {
    "type": "context",
    "path": "context/trading",
    "display_name": "Trading",
    "description": "Market data, signals, and analysis for tracked financial instruments",
    "managed_by": "agent",
    "entity_type": "instrument",
    "entity_structure": {
        "profile.md": (
            "# {name}\n\n"
            "## Price & Volume\n\n"
            "## Fundamentals\n\n"
            "## Signal History\n"
        ),
        "analysis.md": (
            "# Analysis — {name}\n\n"
            "<!-- Latest analysis with reasoning, newest first -->\n"
        ),
    },
    "assets_folder": False,
    "synthesis_file": "overview.md",
    "synthesis_template": (
        "# Trading Overview\n\n"
        "## Watchlist Status\n\n"
        "## Cross-Asset Patterns\n\n"
        "## Active Signals\n"
    ),
    "tracker_file": "_tracker.md",
}
```

**`portfolio/` domain** — account state, positions, trade history, performance:

```python
"portfolio": {
    "type": "context",
    "path": "context/portfolio",
    "display_name": "Portfolio",
    "description": "Trading account state — positions, trade history, performance metrics",
    "managed_by": "agent",
    "entity_type": "position",
    "entity_structure": {
        "profile.md": (
            "# {name}\n\n"
            "## Entry\n\n"
            "## Current State\n\n"
            "## Thesis & Exit Criteria\n"
        ),
    },
    "assets_folder": False,
    "synthesis_file": "summary.md",
    "synthesis_template": (
        "# Portfolio Summary\n\n"
        "## Account State\n\n"
        "## Position Mix\n\n"
        "## Performance & Attribution\n"
    ),
    "tracker_file": "_tracker.md",
}
```

**Naming rationale**: `trading` (not `markets`) avoids collision with the existing `market` domain (business/industry market research, entity_type=segment). `trading` describes the concern (financial instrument observation), `portfolio` describes the account state. Same naming logic as `customers` (entity observation) + `revenue` (aggregate metrics) in commerce.

**File write modes** (per workspace-conventions.md):
- `profile.md` (both domains) — **overwrite** each cycle (current state snapshot)
- `analysis.md` (trading) — **append newest-first** (signal + reasoning history, capped 90 days)
- `overview.md` / `summary.md` (synthesis) — **overwrite** each cycle
- `_tracker.md` — **overwrite** each cycle (freshness + coverage)

**Additional workspace files** (not in entity_structure, written by tasks):
- `/workspace/context/portfolio/history/{YYYY-MM}.md` — Monthly trade execution log (append newest-first)
- `/workspace/context/portfolio/performance/{YYYY-MM}.md` — Monthly performance snapshot (overwrite weekly)

### 3. Trading Bot owns the trading context

Same pattern as platform bots (ADR-158): one bot, one platform, owned directories.

| Agent | Platform | Directories | Task types |
|---|---|---|---|
| Slack Bot | Slack | `slack/` | `slack-digest`, `slack-respond` |
| Notion Bot | Notion | `notion/` | `notion-digest`, `notion-update` |
| GitHub Bot | GitHub | `github/` | `github-digest` |
| Commerce Bot | Lemon Squeezy | `customers/`, `revenue/` | `commerce-digest`, `commerce-create-product`, etc. |
| **Trading Bot** | Alpaca | `trading/`, `portfolio/` | `trading-digest`, `trading-signal`, `trading-execute`, `portfolio-review` |

Trading Bot created paused at signup, activated when the user connects an Alpaca account — same pattern as Commerce Bot (ADR-183).

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

### 4. Market data via trading connection metadata (not separate connection)

Alpaca provides account/portfolio data (positions, orders, history). Market intelligence — daily prices, fundamentals, news — comes from a supplementary market data API.

| Provider | Free tier | Rate limit | Data |
|---|---|---|---|
| Alpha Vantage | 25 req/day | Per-key | Daily OHLCV, fundamentals, earnings, news sentiment |

Alpha Vantage for daily batch data (25 requests = 25 tickers/day, sufficient for a focused watchlist).

Market data API key stored in the trading connection's `metadata.market_data_key` field — not a separate `platform_connections` entry. One connection, one concern. The Alpaca client reads both keys from the same connection record: `credentials_encrypted` for trading API, `metadata.market_data_key` for Alpha Vantage. Same pattern as commerce storing `metadata.provider` alongside the encrypted LS key.

### 5. Four trading task types

| Task type | Output kind | Agent | Default schedule | Domains |
|---|---|---|---|---|
| `trading-digest` | `accumulates_context` | Trading Bot | Daily (market close) | reads: `trading`, `portfolio` · writes: `trading`, `portfolio` |
| `trading-signal` | `produces_deliverable` | Analyst | Daily (post-digest) | reads: `trading`, `portfolio` · writes: — (signals written to task output + `trading/{ticker}/analysis.md`) |
| `trading-execute` | `external_action` | Trading Bot | Daily (post-signal, skip if no approved signals) | reads: signal task output, `portfolio` · writes: `portfolio` |
| `portfolio-review` | `produces_deliverable` | Analyst | Weekly | reads: `portfolio`, `trading` · writes: `portfolio` (performance files) |

**Agent assignment rationale**: Each process step maps to exactly one `agent_type` per codebase convention. `trading-signal` is Analyst (signal generation is analysis of accumulated context). If multi-agent signal generation is needed later (Researcher gathers → Analyst analyzes), the process step list grows — but starts with one.

**Trigger model**: No task-triggers-task mechanism exists in the codebase. All three daily tasks (`trading-digest`, `trading-signal`, `trading-execute`) run on schedule with staggered times. `trading-execute` includes a "skip if no new approved signals" check in its step instructions — deterministic, zero LLM cost when nothing to do. During validation phase, `trading-execute` can be left paused and triggered manually by TP after human signal review.

**Step instructions:**

```python
STEP_INSTRUCTIONS = {

    "trading-digest": (
        "You are the Trading Bot. Your job is to sync your trading account "
        "and market data into the workspace.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "Steps:\n"
        "1. Read account status: platform_trading_get_account\n"
        "2. Read current positions: platform_trading_get_positions\n"
        "3. Read recent orders: platform_trading_get_orders\n"
        "4. For each asset on the watchlist, read market data: "
        "platform_trading_get_market_data\n"
        "5. Update portfolio/ domain:\n"
        "   - WriteFile: _tracker.md (account snapshot: equity, cash, buying power)\n"
        "   - WriteFile: {ticker}/profile.md for each open position\n"
        "   - WriteFile: history/{YYYY-MM}.md (append new executions)\n"
        "6. Update trading/ domain:\n"
        "   - WriteFile: {ticker}/profile.md (price + volume update)\n"
        "   - WriteFile: _tracker.md (freshness update per asset)\n\n"
        "Quantification rules:\n"
        "- All figures precise: $10,450.23 equity, 47.5 shares (not ~50)\n"
        "- Always include period comparison (vs last cycle)\n"
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
        "2. ReadFile: /workspace/context/portfolio/summary.md (portfolio assessment)\n"
        "3. For each watchlist asset:\n"
        "   - ReadFile: /workspace/context/trading/{ticker}/profile.md\n"
        "   - ReadFile: /workspace/context/trading/{ticker}/analysis.md (prior signals + outcomes)\n"
        "4. Analyze: trend direction, momentum, support/resistance, news catalysts, "
        "prior signal accuracy for this asset\n"
        "5. Generate signals with format:\n"
        "   - Ticker, Direction (buy/sell/hold), Confidence (high/medium/low)\n"
        "   - Reasoning (2-3 sentences referencing accumulated data)\n"
        "   - Suggested position size (% of portfolio)\n"
        "   - Risk note (what would invalidate this signal)\n"
        "6. WriteFile: update /workspace/context/trading/{ticker}/analysis.md "
        "(append this signal for future outcome tracking)\n\n"
        "Your output: today's signal report with actionable recommendations."
    ),

    "trading-execute": (
        "You are the Trading Bot. Your job is to execute trades based on "
        "approved trading signals.\n\n"
        "IMPORTANT: This task places real orders (or paper orders). "
        "Execute ONLY signals marked as approved in the signal output.\n\n"
        "Pre-check: Read the latest signal output from the trading-signal task. "
        "If no new approved signals exist since last execution, SKIP — produce "
        "a brief 'no signals to execute' output and exit.\n\n"
        "Steps:\n"
        "1. Read the latest signal output from the trading-signal task\n"
        "2. Read current positions: platform_trading_get_positions\n"
        "3. Read account status: platform_trading_get_account\n"
        "4. For each approved signal:\n"
        "   - Validate: sufficient buying power, position size within limits\n"
        "   - Execute: platform_trading_submit_order\n"
        "   - Log: WriteFile to portfolio/history/{YYYY-MM}.md (append execution)\n"
        "   - Update: WriteFile to portfolio/{ticker}/profile.md\n"
        "5. Update portfolio/_tracker.md with new account state\n\n"
        "Position sizing rules:\n"
        "- Never exceed 10% of portfolio in a single position\n"
        "- Never exceed 5 open positions simultaneously\n"
        "- Always use limit orders (not market orders)\n"
        "- Set stop-loss at 5% below entry for all new positions\n\n"
        "Daily loss limit: if portfolio drops >3% in a day, skip remaining "
        "signals and log escalation to portfolio/_tracker.md.\n\n"
        "Your output: execution confirmation with order details."
    ),

    "portfolio-review": (
        "You are producing a weekly portfolio performance review.\n\n"
        "Steps:\n"
        "1. ReadFile: /workspace/context/portfolio/_tracker.md\n"
        "2. ReadFile: /workspace/context/portfolio/history/{YYYY-MM}.md\n"
        "3. ReadFile: /workspace/context/portfolio/performance/{YYYY-MM}.md (if exists)\n"
        "4. For each position, read trading/{ticker}/analysis.md to correlate signal → outcome\n"
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
        "8. WriteFile: /workspace/context/portfolio/summary.md (updated synthesis)\n\n"
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

# In PLATFORM_TOOLS_BY_PROVIDER:
"trading": TRADING_TOOLS + TRADING_WRITE_TOOLS,

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
    "paper": true,
    "market_data_key": "..."
}
```

Flow (mirrors `connect_commerce` in `integrations.py`):
1. Validate credentials via `alpaca_client.get_account()`
2. Encrypt API key + secret, store in `platform_connections` with `platform="trading"`
3. Store in connection metadata: `paper` flag (determines base URL), `market_data_key` (Alpha Vantage), `provider: "alpaca"`
4. Activate Trading Bot agent (paused from signup → active)
5. Scaffold `trading/` and `portfolio/` context domains via `scaffold_context_domain()`
6. Create default `trading-digest` task (daily, `essential=false`)
7. Return account details (equity, cash, account number — masked)

**Paper-to-live transition**: Update the connection's `metadata.paper` flag. Same API key pair works for both environments on Alpaca. Single flag flip:

```
PATCH /integrations/trading/connect
{ "paper": false }
```

### 8. Graduated execution model

Trading writes have real financial consequences. The execution model graduates:

| Phase | Mode | Execution behavior |
|---|---|---|
| **Phase 0: Observation** | Paper, no execution task | `trading-digest` + `trading-signal` only. Signals produced but not executed. Human reviews signal quality via TP. |
| **Phase 1: Paper execution** | Paper, execution task enabled | `trading-execute` task enabled (unpaused). Full loop runs on paper account. P&L tracked in workspace. Zero financial risk. |
| **Phase 2: Live execution** | Live, execution task enabled | Connection flipped to live (`PATCH paper=false`). Same code, real money. Position sizing guardrails enforced. |

Phase transitions are manual (user flips `paper` flag and pauses/unpauses `trading-execute` task via TP). No automated graduation — the user decides when signal quality justifies real capital.

**Guardrails (enforced in `trading-execute` step instructions + client-side validation in `alpaca_client.py`):**
- Max 10% of portfolio per position
- Max 5 simultaneous open positions
- Limit orders only (no market orders) — prevents slippage
- Stop-loss required on all new positions (5% default)
- Daily loss limit: if portfolio drops >3% in a day, `trading-execute` skips remaining signals and logs escalation

---

## Implementation

### Phase 1: Client + read tools + context domains

**New files:**
- `api/integrations/core/alpaca_client.py` — Alpaca Direct API client following `github_client.py` / `lemonsqueezy_client.py` pattern
  - `async def _request()` with retry logic (exponential backoff, 3 attempts)
  - Rate limiting: 200 req/min (check response headers)
  - Read methods: `get_account()`, `get_positions()`, `list_orders()`, `get_bars()`, `get_portfolio_history()`
  - Paper/live base URL switching via connection `metadata.paper`
  - Alpha Vantage reads: `get_daily_prices()`, `get_fundamentals()` — separate base URL, uses `metadata.market_data_key`
  - Singleton via `get_trading_client()`

**Modified files:**
- `api/services/platform_tools.py` — Add `TRADING_TOOLS`, `PLATFORM_TOOLS_BY_PROVIDER["trading"]`, `PLATFORM_TOOLS_BY_CAPABILITY["read_trading"]`, `CAPABILITY_PROVIDER_MAP["read_trading"]`, `_handle_trading_tool()` handler
- `api/services/directory_registry.py` — Add `trading/` and `portfolio/` domain entries (canonical, not temporal)
- `api/services/agent_framework.py` — Add `trading_bot` to `AGENT_TEMPLATES` + `DEFAULT_ROSTER` (paused at signup), `CAPABILITIES["read_trading"]`
- `api/routes/integrations.py` — Add `POST /integrations/trading/connect` endpoint

**Migration:** `supabase/migrations/148_add_trading_bot_role.sql` — add `trading_bot` to `agents_role_check` constraint.

**Dependencies:** `pip install alpaca-py` on API + Scheduler services. Alpha Vantage: lightweight HTTP wrapper via `_request()`, no library needed.

### Phase 2: Digest + signal task types

**Modified files:**
- `api/services/task_types.py` — Add `trading-digest`, `trading-signal`, `portfolio-review` task type definitions + step instructions
- `api/services/workspace_init.py` — Trading Bot activation + default task scaffolding on connect (same pattern as commerce connect)

**Validation:** Run `trading-digest` task, verify market data and portfolio state written correctly to `trading/` and `portfolio/` context domains.

### Phase 3: Write tools + execution task

**Modified files:**
- `api/integrations/core/alpaca_client.py` — Add write methods: `submit_order()`, `cancel_order()`, `close_position()` — with client-side guardrail validation (position size, max positions, order type)
- `api/services/platform_tools.py` — Add `TRADING_WRITE_TOOLS`, `PLATFORM_TOOLS_BY_CAPABILITY["write_trading"]`, extend `_handle_trading_tool()` for write operations
- `api/services/agent_framework.py` — Add `CAPABILITIES["write_trading"]`
- `api/services/task_types.py` — Add `trading-execute` task type + step instructions

**Validation:** Run full loop on Alpaca paper account. Verify: signal generated → order placed → position appears → portfolio domain updated.

### Phase 4: Portfolio review + performance tracking

**Modified files:**
- `api/services/task_types.py` — Finalize `portfolio-review` step instructions with section kind guidance (metric-cards, trend-chart, data-table)

**Validation:** After 5+ paper trades, `portfolio-review` produces a meaningful performance report with signal accuracy metrics and benchmark comparison.

### Phase 5: Live trading

- `PATCH /integrations/trading/connect` endpoint for paper-to-live transition
- Verify guardrails fire correctly (position limits, stop-loss, daily loss limit)
- Fund Alpaca account, flip the switch

---

## Registry updates summary

| Registry | Addition |
|---|---|
| `WORKSPACE_DIRECTORIES` | `trading/` (canonical), `portfolio/` (canonical) |
| `AGENT_TEMPLATES` | `trading_bot` (class: platform-bot, platform: trading) |
| `DEFAULT_ROSTER` | `{"title": "Trading Bot", "role": "trading_bot"}` |
| `CAPABILITIES` | `read_trading`, `write_trading` |
| `TASK_TYPES` | `trading-digest`, `trading-signal`, `trading-execute`, `portfolio-review` |
| `PLATFORM_TOOLS_BY_PROVIDER` | `trading: TRADING_TOOLS + TRADING_WRITE_TOOLS` |
| `PLATFORM_TOOLS_BY_CAPABILITY` | `read_trading: [...]`, `write_trading: [...]` |
| `CAPABILITY_PROVIDER_MAP` | `read_trading: "trading"`, `write_trading: "trading"` |

DB migration 148: Add `trading_bot` to `agents_role_check` constraint.

---

## Cost model

| Component | Cost | Notes |
|---|---|---|
| Alpaca account | $0 | No fees, no minimum, commission-free |
| Alpha Vantage | $0 | Free tier: 25 req/day (sufficient for ≤25 ticker watchlist) |
| Alpaca market data | $0 | Basic plan included; real-time upgrade $9/mo (defer) |
| LLM: trading-digest | ~$0.02/run | Sonnet, ~2K input + tools, daily |
| LLM: trading-signal | ~$0.05/run | Sonnet, ~5K input (accumulated context), daily |
| LLM: trading-execute | ~$0.01/run | Sonnet, ~1K input, daily (often skips) |
| LLM: portfolio-review | ~$0.08/run | Sonnet, ~8K input, weekly |
| **Total monthly** | **~$3-5/mo** | At daily signal generation cadence |

---

## What this validates

If the full loop runs successfully for 30 days on paper trading:

1. **Framework proof**: The standard agent framework — registries, scaffolding, task pipeline, context domains — can close a complete loop without special-casing. Observe → analyze → decide → execute → measure, all through existing infrastructure.
2. **Accumulation proof**: Signal accuracy should improve as the workspace accumulates more price history, prior signal outcomes, and pattern data. The `analysis.md` entity files carry forward.
3. **Multi-agent proof**: Different agents (Trading Bot for data/execution, Analyst for signals/review) coordinate through workspace files, not direct communication. Same multi-agent pattern as `revenue-report` (analyst reads commerce-digest output).
4. **Quality signal**: P&L vs. buy-and-hold benchmark provides an objective, non-gameable quality metric for the agent framework's closed-loop capability.
5. **Stress test**: Write-back with consequences (real money) tests guardrail enforcement, graduated capability, and the framework's ability to handle domains where mistakes are irreversible.

If signal accuracy exceeds 55% and portfolio returns beat SPY buy-and-hold over 30 days of paper trading, proceed to Phase 5 (live). If not, the workspace files reveal exactly where the analysis is failing — which signals were wrong, what data was missing, what patterns the agents missed — providing concrete direction for improvement.
