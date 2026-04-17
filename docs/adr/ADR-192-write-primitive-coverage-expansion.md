# ADR-192: Write Primitive Coverage Expansion — Trading Sophistication + Risk Gate + Commerce Ops + Email Send

> **Status**: Implemented (2026-04-17, five phases all on main)
> **Date**: 2026-04-17
> **Authors**: KVK, Claude
> **Extends**: ADR-183 (Commerce Substrate), ADR-187 (Trading Integration Alpaca), ADR-191 (Polymath Operator ICP + Domain Stress Discipline)
> **Depended on by**: ADR-193 (ProposeAction + approval loop — needs complete write surface to approve), ADR-195 (TP autonomous decision loop — needs risk gate to be safe)

---

## Context

### Where we are

ADR-183 shipped commerce write primitives (`create_product`, `update_product`, `create_discount`). ADR-187 shipped trading write primitives (`submit_order`, `cancel_order`, `close_position`). Both are **wired live** — verified against platform_tools.py dispatch and the underlying Alpaca + Lemon Squeezy clients. An alpha operator connecting either integration today has YARNNN capable of real operations.

This is the baseline. Alpha can start today on the baseline.

### The gaps ADR-192 closes

Gaps fall into four categories, derived from the `DOMAIN-STRESS-MATRIX.md` audit (v1.1):

1. **Trading sophistication** — bracket orders, trailing stops, stop-loss modification, partial position close, watchlist mutation, bulk cancel. Alpaca API supports all of these; they're simply not wired into YARNNN's tool surface.
2. **Trading risk-gating** — the load-bearing safety primitive. Today `submit_order` executes any LLM-proposed order with no pre-trade validation against trader-declared risk parameters. An autonomous loop (ADR-195) calling `submit_order` without a risk gate is unsafe.
3. **E-commerce operational tools** — refund, inventory mutation, bulk price update, product variant creation, customer tagging. LS API supports; not wired.
4. **Email send capability** — YARNNN has zero email-send primitive today. Needed for e-commerce autonomous customer communication (transactional + campaign). Introduces a new provider integration (Resend proposed).

### Why this ADR matters now

ADR-191 committed to polymath-operator ICP with conglomerate alpha across structurally different domains. The alpha launches on baseline primitives, but:

- The **day-trader alpha friend must supervise every trade manually** until risk-gating ships. This blocks trusted autonomy claims.
- The **e-commerce alpha friend cannot autonomously respond to customers or send campaigns** without email capability. This blocks a core operational workflow.

ADR-192 closes both, unblocking ADR-193 (approval loop) and ADR-195 (autonomous decision loop).

---

## Decision

### Phase 1 — Trading sophistication (new Alpaca primitives)

Wire the following Alpaca API capabilities as YARNNN platform tools. All exist on Alpaca's side; pure tool-surface extension.

| Tool name | Maps to | Description |
|-----------|---------|-------------|
| `platform_trading_update_order` | Alpaca PATCH /v2/orders/{id} | Modify an open order (e.g., update stop price on existing stop order) without cancel+resubmit race |
| `platform_trading_submit_bracket_order` | Alpaca submit_order with order_class="bracket" | Atomic entry + target + stop-loss in one call. Reduces race conditions on position entry. |
| `platform_trading_submit_trailing_stop` | Alpaca submit_order with trail_percent or trail_price | Stop that follows price automatically |
| `platform_trading_partial_close` | Alpaca submit_order(side=opposite, qty=partial) | Close N shares of a position, not all. Wrapper for clarity + safety (prevents accidental full close). |
| `platform_trading_add_to_watchlist` / `platform_trading_remove_from_watchlist` | Alpaca POST/DELETE /v2/watchlists/{id}/{symbol} | Mutate watchlist. Needed for YARNNN-proposed tracking additions. |
| `platform_trading_cancel_all_orders` | Alpaca DELETE /v2/orders | Bulk cancel. Needed for "get flat" scenarios. |

Added to `TRADING_WRITE_TOOLS` list in `api/services/platform_tools.py`. Handlers extended in `handle_platform_tool` dispatch. Alpaca client extended in `api/integrations/core/alpaca_client.py`.

**Net new primitives for YARNNN: 7.** All mechanical. Low architectural risk.

### Phase 2 — Trading risk-gate primitive (CRITICAL)

**New internal primitive:** `check_risk_limits(proposed_order, user_id)` — pure Python, no LLM, runs before any `submit_order` or `submit_bracket_order` call in autonomous mode.

**Storage:** risk parameters live at `/workspace/context/trading/_risk.md` as structured markdown (key: value pairs parseable by existing `UserMemory._parse_memory_md`).

Example `_risk.md`:
```markdown
# Risk Parameters

max_position_size_usd: 5000
max_position_percent_of_portfolio: 10
max_daily_loss_usd: 500
max_day_trades: 3
max_order_size_shares: 1000
require_stop_loss: true
allowed_tickers: [AAPL, MSFT, GOOGL, NVDA, SPY, QQQ]
blocked_tickers: []
trading_hours_only: true
```

**Gate logic:**
```
check_risk_limits(proposed_order, user_id) returns:
  {
    "approved": bool,
    "reason": str,       # human-readable; shown to user on rejection
    "warnings": [str],   # non-blocking cautions
  }
```

Evaluation steps:
1. Load `_risk.md` from user's workspace. If absent, default to **fail-closed** (approved=false, reason="no risk parameters declared; user must set risk limits before autonomous trading").
2. Load current account state (positions, buying power, day-trade count, P&L) via `alpaca_client.get_account()`.
3. Evaluate proposed order:
   - Is ticker in `allowed_tickers` (if set) and not in `blocked_tickers`?
   - Is proposed position size within `max_position_size_usd`?
   - Would execution exceed `max_position_percent_of_portfolio`?
   - Has trader hit `max_daily_loss_usd` threshold today?
   - Has trader hit `max_day_trades` under PDT rules?
   - Does order size exceed `max_order_size_shares`?
   - If `require_stop_loss: true`, does the order include a stop or is it a bracket?
   - If `trading_hours_only: true`, are we in market hours?
4. Return approved/rejected with reason + any warnings.

**Invocation modes:**
- **Autonomous mode** (TP/agent calling via scheduled task or autonomous loop, ADR-195): `submit_order` handler ALWAYS calls `check_risk_limits` first. Rejection blocks execution.
- **Supervised mode** (user in chat requests a specific order): `check_risk_limits` runs as advisory; warnings shown to user; user can override (but rejection for hard-block rules like "above max_position_size" should still refuse — the risk params are the trader's own declared limits).
- **Manual override** — trader can execute via Alpaca directly outside YARNNN. This is expected and correct.

**New file:** `api/services/risk_gate.py` implementing `check_risk_limits`.

**Integration in `handle_platform_tool`:** `submit_order`, `submit_bracket_order`, `submit_trailing_stop` handlers all check risk first before calling Alpaca.

### Phase 3 — E-commerce operational primitives (new LS primitives)

| Tool name | Maps to | Description |
|-----------|---------|-------------|
| `platform_commerce_issue_refund` | LS POST /v1/refunds | Refund an order (full or partial amount). Essential for autonomous customer support. |
| `platform_commerce_update_inventory` | LS PATCH /v1/products/{id} (quantity field) | Adjust stock level. Needed for out-of-stock reactions + restock automation. |
| `platform_commerce_bulk_update_prices` | Iterates update_product | Atomic-ish bulk price change across SKUs. Seasonal pricing, competitor matching. |
| `platform_commerce_create_variant` | LS POST /v1/variants | Create a product variant (size/color/tier). Expands SKU portfolio. |
| `platform_commerce_update_customer` | LS PATCH /v1/customers/{id} | Mutate customer metadata — tags, segment, notes. Needed for targeting + segmentation. |

Added to `COMMERCE_WRITE_TOOLS`. Handlers extended. LS client extended if methods missing.

**Net new primitives for YARNNN: 5.** Some require LS API sections not yet implemented in `lemonsqueezy_client.py` — those are included in this phase.

### Phase 4 — Email send capability (new provider integration)

**Decision: Resend as provider.** Reasons:
- Developer-first, simple API (POST /emails with from/to/subject/html)
- Free tier (3k emails/mo) covers alpha + early users
- No OAuth required (API key in workspace-stored config)
- React Email support if we want richer templates later
- Fair pricing at scale vs. SendGrid/Mailgun

Rejected alternatives:
- LS's transactional email (too narrow — only LS-account customers)
- SendGrid (heavier integration, requires sender verification process)
- AWS SES (lowest cost but steepest ops burden)

**New platform class:** `email` (alongside `slack`, `notion`, `github`, `commerce`, `trading`).

**New integration file:** `api/integrations/core/resend_client.py` — thin HTTP client wrapping Resend API.

**New write primitives:**

| Tool name | Description |
|-----------|-------------|
| `platform_email_send` | Send a single email. Args: to, subject, html, reply_to, from_name. |
| `platform_email_send_bulk` | Send to a list of recipients (each receives a personalized copy). Args: list of recipients, subject, html template with `{{ placeholders }}`. |

**Storage:** Resend API key stored in `platform_connections` table (`platform='email'`, `access_token=<api_key>`, encrypted via existing Fernet layer). User connects via a settings page action.

**Sender-identity model:** Single verified domain per workspace. User verifies their sending domain in Resend; YARNNN sends as `noreply@<their-domain>` or a user-configured address. Alpha can run on Resend's shared `onboarding@resend.dev` sender for fastest setup — no production-quality sender until user verifies domain.

**Rate limits:** Resend enforces per-account; YARNNN doesn't need additional rate limiting in Phase 4. Can add later if abuse pattern emerges.

**No inbound email in this phase.** Resend supports inbound routing, but consuming customer replies / building an inbox is out of scope. For now, email is send-only; replies go to the user's actual inbox (via `reply_to` header) and they handle manually or forward signals to YARNNN via text.

### Phase 5 — Prompt + capability registry updates

Prompts updated to teach YARNNN about the new primitives:
- `api/agents/yarnnn_prompts/platforms.py` — add new trading + commerce + email tool descriptions
- `api/services/agent_framework.py` — extend `CAPABILITIES` or capability mapping for the new tools if agent roles should be gated (e.g., only `writer` role gets `platform_email_send`? or `tracker` gets `platform_trading_add_to_watchlist`? — TBD per alpha observation)

`api/prompts/CHANGELOG.md` — entry per phase.

---

## Impact table (per ADR-191 matrix gate rule)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | **Helps** | Phase 3 adds refund + inventory + bulk-price + variant + customer-tagging. Phase 4 adds email send. Operator can autonomously run refunds, campaigns, support replies. |
| **Day trader** | **Helps** | Phase 1 adds bracket + trailing stop + partial close + watchlist mutation + order modification. Phase 2's risk-gate is THE primitive that unlocks trusted trading autonomy (ADR-195 cannot ship without it). |
| **AI influencer** (scheduled) | **Neutral + forward-helps** | No AI influencer integration shipped yet. But Phase 4 email-send is platform-class new; AI influencer alpha can reuse Resend for newsletter / audience campaigns when it spins up. Email isn't a verticalization — it's generalizable infra. |
| **International trader** (scheduled) | **Neutral + forward-helps** | Same reasoning. When trade integration spins up, email-send infra will be available for compliance notices + counterparty communications. |

**Verdict:** helps two active domains, neutral-but-forward-helps two scheduled. No domain hurt. Gate passes cleanly. Not verticalization.

---

## What doesn't change

- Primitive atomicity (ADR-168). All new tools are atomic. Bulk operations (`bulk_update_prices`, `send_bulk`) are atomic at the "one tool call, many underlying API calls" level; either the loop completes or partial progress is returned — no transactional rollback, by design.
- Three-layer cognition (ADR-189). YARNNN / Specialists / Agents unchanged. New primitives appear in all three layers' tool surfaces when appropriate.
- Inference-driven scaffold depth (ADR-190). Not touched.
- Task pipeline / execution model. Not touched.
- DB schema. No new tables. New rows in `platform_connections` for `platform='email'` connections.
- Existing tools (`submit_order`, `create_product`, etc.) — unchanged except that `submit_order` now invokes `check_risk_limits` in autonomous mode.

---

## Implementation sequence (phased commits, directly to main)

Five commits, sequenced:

| Commit | Phase | Scope | Risk |
|--------|-------|-------|------|
| 1 | Phase 1 | 7 new trading tools — Alpaca client methods + platform_tools entries + handler dispatch | Low. Pure API wiring. |
| 2 | Phase 2 | Risk gate primitive — `risk_gate.py` + `_risk.md` schema + handler integration | Medium. New semantics for autonomous vs. supervised mode. Needs testing against real trader workflows. |
| 3 | Phase 3 | 5 new commerce tools — LS client extensions + platform_tools + handlers | Low. Same pattern as Phase 1. |
| 4 | Phase 4 | Email-send integration — new `resend_client.py` + 2 platform tools + `platform_connections` support for `email` provider + settings-page connect flow | Medium-high. New platform class. Requires frontend connect UX. |
| 5 | Phase 5 | Prompt updates + capability registry updates + CHANGELOG entries consolidating Phases 1–4 | Low. Documentation + prompt wiring. |

**Parallel-safe:** Phases 1 and 3 are independent (trading vs. commerce). Phase 2 depends on Phase 1's tools being in place (so it can intercept them). Phase 4 is independent of all prior. Phase 5 depends on all prior.

Order in practice: 1 → 2 → 3 → 4 → 5, each as a separate commit pushed directly to main per ADR-191 pre-launch workflow.

---

## Consequences

### Positive

1. **Trusted trading autonomy becomes achievable.** Without the risk gate, autonomous execution of `submit_order` is unsafe. With it, ADR-195's autonomous loop can propose + validate + execute trades within declared parameters.
2. **E-commerce operational coverage matches a real operator's actual job.** Refund + inventory + campaigns are table-stakes for "yarnnn runs my store."
3. **Email-send is a foundation capability, not a vertical feature.** It opens up autonomous customer communication for e-commerce, audience comms for future AI influencer domain, counterparty notices for future international trader, and general notification patterns for all domains.
4. **Alpha can graduate from supervised to autonomous per domain.** E-commerce first (ADR-193 approval loop + these primitives), trading next (same loop + risk gate + primitives). Clear sequencing.

### Costs

1. **Phase 4 introduces a new third-party dependency (Resend).** Adds one more vendor to the ops surface. Mitigation: Resend is small-surface (send endpoint + minimal config); migration to alternative providers later is mechanical if needed.
2. **Risk gate is testable but LLM-behavior-dependent.** The gate's logic is pure Python and unit-testable. But validating that YARNNN respects the gate's rejection (rather than "helpfully" retrying with altered parameters) requires prompt-level discipline. Scope for Phase 5 prompt guidance: "If check_risk_limits rejects, surface to user; do not retry with reduced size unless user approves."
3. **Email provider ops burden.** Domain verification, sender reputation, abuse monitoring. Mostly on Resend, some on yarnnn. Worth explicit monitoring from alpha onward.
4. **17 new tool definitions to maintain.** Every new tool is a doc + test + prompt surface to keep current. Total surface post-ADR-192: ~40 platform tools across all providers. Approaching the practical upper bound for LLM context; may force scope review on future platform additions.

### Deferred

- **Email inbound routing.** Parsing customer replies back into YARNNN's context. Out of scope. Revisit when alpha signal shows operators manually forwarding replies frequently.
- **Risk gate for non-trading domains.** E-commerce doesn't need a risk gate for refunds (they're reversible and bounded). Revisit if a high-stakes commerce action emerges.
- **Multi-broker trading support.** Alpaca only for now. A broker abstraction layer is a future ADR, triggered when a second broker alpha operator appears.
- **Multi-provider email.** Resend only for now. Abstraction behind a `MailProvider` interface can land if Resend becomes limiting.

---

## Open questions

1. **Risk param UX.** Users declare risk via `_risk.md` file or via a settings UI? Phase 2 implementation assumes file-based; a settings UI is a later UX polish. The file is the canonical source regardless — settings UI writes to the file.
2. **Default `_risk.md` at trading-connect time.** Should connecting Alpaca auto-scaffold a conservative-default `_risk.md` the user can edit? Strongly leaning yes — fail-closed default without parameters is too abrupt. Scaffold with commented-out conservative defaults.
3. **Email sender verification flow.** Alpha uses Resend shared sender (`onboarding@resend.dev`) — fine for testing. Production-quality alpha: prompt operator to verify their domain before first campaign send. Implementation detail for Phase 4.
4. **Capability-class gating.** Should `writer` role agents have `platform_email_send`? `tracker` have `add_watchlist`? Default for Phase 4: all platform write tools available to all agent types that have the corresponding `write_<platform>` capability. Refinement based on alpha observation.
5. **Autonomous-mode signaling.** How does `submit_order`'s handler know it's being called autonomously vs. from user chat? Cleanest: `tool_input` includes a `mode: "autonomous" | "supervised"` flag set by the caller (TP in autonomous loop sets autonomous; chat handler sets supervised). Phase 2 adds this flag.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial proposal. Five phases: trading sophistication (7 tools), risk gate (critical), commerce ops (5 tools), email-send (2 tools + Resend integration), prompt + registry updates. Total: 14 new platform tools + 1 new internal primitive + 1 new platform class. Scope verified against DOMAIN-STRESS-MATRIX v1.1 audit of shipped state. |
