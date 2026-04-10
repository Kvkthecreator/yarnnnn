# ADR-171: Token Spend Metering — Universal Usage-Based Pricing

> **Status**: Implemented
> **Date**: 2026-04-10
> **Replaces**: Work credits model — `work_credits` table, `CREDIT_COSTS`, `check_credits()`, `record_credits()`, `get_monthly_credits_used()`, `monthly_credits` on `PlatformLimits`

---

## Context

YARNNN currently meters autonomous work via a fictional "work credits" currency (`task_execution = 3 credits`, `render = 1 credit`). Three problems:

1. **Arbitrary abstraction** — credits have no grounding in actual cost. A user cannot reason about "3 credits" relative to the value they received.
2. **Incomplete scope** — only task execution is metered. Chat turns, system inference, web search synthesis, and session summaries all consume Anthropic API tokens but are invisible to the billing model.
3. **Misaligned incentives** — flat credit cost per task run doesn't capture real cost variance. A 1-step slack digest is not the same cost as a 5-step market research run with 8 WebSearch rounds.

Claude's pricing model is the right reference: one universal meter (tokens consumed), one published rate, no surface carveouts.

---

## Decisions (all locked)

### 1. Universal unit: `cost_usd`

Every LLM call is reduced to one number: `cost_usd = (input_tokens × input_rate) + (output_tokens × output_rate)`. Computed at write time. Monthly spend = `SUM(cost_usd)` for a user this calendar month. No credits, no surface carveouts, no weighted task costs.

### 2. User-facing billing rates: 2x markup on Anthropic API rates

YARNNN publishes its own rates, decoupled from Anthropic's rates. If Anthropic cuts prices, YARNNN's rates stay until explicitly updated.

```python
# User-facing billing rates (2x Anthropic published API rates, April 2026)
# These are the rates charged to users — not Anthropic's cost to YARNNN.
BILLING_RATES = {
    "claude-sonnet-4-20250514":  {"input_per_mtok": 6.00,  "output_per_mtok": 30.00},
    "claude-opus-4-6":           {"input_per_mtok": 30.00, "output_per_mtok": 150.00},
    "claude-haiku-4-5-20251001": {"input_per_mtok": 1.60,  "output_per_mtok": 8.00},
}
DEFAULT_BILLING_RATE = BILLING_RATES["claude-sonnet-4-20250514"]
```

**What users see**: Sonnet rates only (the default model). Haiku is an internal model — never user-selectable, never shown in billing UI. Opus rates are shown if/when model selection is exposed.

**Transparency statement** (shown in settings/billing UI):
> "YARNNN uses Claude Sonnet. We charge $6/million input tokens and $30/million output tokens — a 2× markup on Anthropic's published API rate to cover infrastructure, hosting, and platform costs."

### 3. Scope: all LLM call surfaces

| Surface | File | Model | Currently captured |
|---|---|---|---|
| TP chat turns | `routes/chat.py` → `session_messages.metadata` | Sonnet | ✅ token fields exist |
| Task execution | `task_pipeline.py` → `agent_runs.metadata` | Sonnet | ✅ full breakdown |
| WebSearch synthesis | `primitives/web_search.py` | Sonnet | ❌ add recording |
| Context inference | `context_inference.py` | Sonnet | ❌ add recording |
| Task deliverable inference | `task_deliverable_inference.py` | Sonnet | ❌ add recording |
| ManageTask evaluate | `primitives/manage_task.py` | Haiku | ❌ add recording |
| Session continuity | `session_continuity.py` | Haiku | ❌ add recording |

All surfaces write to `token_usage`. The existing `agent_runs.metadata` and `session_messages.metadata` token fields are preserved as-is — `token_usage` is the unified ledger, not a replacement.

### 4. WebSearch: token-only, no per-search fee

Web search results are returned as input tokens in the API response. No separate per-search fee from Anthropic (confirmed). Charged at standard input token rate for the model used. A search-heavy task run naturally costs more — no special-casing needed.

### 5. Cache discount: not passed through

Anthropic charges ~10% of normal input rate for cache reads on the API. YARNNN charges users at full non-cached rates regardless of actual cache hit/miss. Cache efficiency is platform margin — consistent with how Anthropic handles it for Claude.ai subscribers (no cache line items visible to users). Simplifies the meter: one rate per model, no cache tracking in billing.

### 6. Overage model: hard stop

When a user's monthly `SUM(cost_usd)` reaches their tier limit, further LLM calls are blocked until the next calendar month. No soft overage, no Stripe metered billing, no spending caps. Revisit when users are actively churning due to limits.

### 7. Tier allocations

| Tier | Monthly fee | Included `cost_usd` (at user-facing rates) | Approx. Anthropic cost covered |
|---|---|---|---|
| Free | $0 | $3.00 | ~$1.50 |
| Pro | $19/mo | $20.00 | ~$10.00 |

Free ~$3 = roughly 40 avg chat turns + 10 task runs at Sonnet rates. Pro ~$20 = meaningful autonomous workload. Allocations are starting assumptions — adjustable once empirical data exists.

### 8. Future model selection (flagged, not implemented)

The `model` column on `token_usage` and model-keyed `BILLING_RATES` are designed to support per-task or per-agent model selection (e.g., "this research agent uses Opus"). Model selection surface — whether per-workspace, per-agent-type, or per-task — is deferred. Infrastructure supports it without changes.

---

## Implementation

### New table: `token_usage`

```sql
CREATE TABLE token_usage (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES auth.users(id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    caller        text NOT NULL,
    -- 'chat' | 'task_pipeline' | 'web_search' | 'inference' | 'evaluation' | 'session_summary'
    model         text NOT NULL,
    input_tokens  int NOT NULL DEFAULT 0,
    output_tokens int NOT NULL DEFAULT 0,
    cost_usd      numeric(10,6) NOT NULL,
    ref_id        uuid,     -- agent_runs.id or session_messages.id for traceability
    metadata      jsonb     -- task_slug, session_id, caller-specific context
);

CREATE INDEX token_usage_user_month ON token_usage (user_id, created_at);
```

### Deletions

| What | Where | Replaced by |
|---|---|---|
| `work_credits` table | DB migration | `token_usage` table |
| `CREDIT_COSTS` dict | `platform_limits.py` | `BILLING_RATES` dict |
| `check_credits()` | `platform_limits.py` | `check_spend_budget()` |
| `record_credits()` | `platform_limits.py` | `record_token_usage()` |
| `get_monthly_credits_used()` | `platform_limits.py` | `get_monthly_spend_usd()` |
| `monthly_credits` on `PlatformLimits` | `platform_limits.py` | `monthly_spend_usd_limit` |
| `get_monthly_credits` RPC | Supabase | `get_monthly_spend_usd` RPC |

### New functions in `platform_limits.py`

```python
BILLING_RATES = { ... }  # as above

def compute_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost at published user-facing billing rates. Cache-agnostic."""

def record_token_usage(
    client, user_id: str, caller: str, model: str,
    input_tokens: int, output_tokens: int,
    ref_id: str = None, metadata: dict = None,
) -> None:
    """Write one row to token_usage. Called at every LLM call site."""

def get_monthly_spend_usd(client, user_id: str) -> float:
    """SUM(cost_usd) for user this calendar month."""

def check_spend_budget(client, user_id: str) -> tuple[bool, float, float]:
    """(allowed, spent_usd, limit_usd). Hard stop when spent >= limit."""
```

### Call sites to wire up

| File | Where to add `record_token_usage()` | Caller tag |
|---|---|---|
| `routes/chat.py` | After `append_message()` with assistant metadata (~L1352) | `'chat'` |
| `task_pipeline.py` | After `update_version_for_delivery()` single-step (~L1515), after multi-step total_usage (~L2104) | `'task_pipeline'` |
| `primitives/web_search.py` | After final response, accumulate across rounds | `'web_search'` |
| `context_inference.py` | After `chat_completion()` returns | `'inference'` |
| `task_deliverable_inference.py` | After inference call | `'inference'` |
| `primitives/manage_task.py` | After evaluate LLM call | `'evaluation'` |
| `session_continuity.py` | After `messages.create()` | `'session_summary'` |

### `get_usage_summary()` update

Replace `credits_used` / `monthly_credits` fields with `spend_usd` / `monthly_spend_usd_limit` in the response shape consumed by `/api/user/limits`.

### `admin.py` update

`PRICING` dict in `admin.py` → replaced by import of `BILLING_RATES` from `platform_limits.py`. Single source of truth.

---

## What Does Not Change

- `session_messages.metadata` and `agent_runs.metadata` token fields — preserved
- `monthly_messages` limit — preserved as independent gate
- `active_tasks` limit — preserved
- Source limits (Slack, Notion, GitHub) — preserved

---

## Revision History

| Date | Change |
|---|---|
| 2026-04-10 | v0.1 — Initial proposal |
| 2026-04-10 | v1.0 — All decisions locked: 2x markup, Sonnet user-facing rate, $3/$20 tier allocations, hard stop overage, full call site scope, cache not passed through, model-keyed rates for future Opus support. Ready for implementation. |
| 2026-04-10 | v1.1 — Implemented. Migration 143: `token_usage` table + `get_monthly_spend_usd` RPC + drop `work_credits`. `platform_limits.py`: `BILLING_RATES`, `compute_cost_usd`, `record_token_usage`, `check_spend_budget`, `get_monthly_spend_usd`. All 7 call sites wired: `routes/chat.py` (chat), `task_pipeline.py` (task_pipeline ×3), `primitives/web_search.py` (web_search), `context_inference.py` + `primitives/update_context.py` (inference), `task_deliverable_inference.py` (inference), `primitives/manage_task.py` (evaluation), `session_continuity.py` (session_summary). `services/anthropic.py`: added `chat_completion_with_usage()`. `admin.py`: `PRICING` dict replaced by derived `_ANTHROPIC_RATES` from `BILLING_RATES`. |
