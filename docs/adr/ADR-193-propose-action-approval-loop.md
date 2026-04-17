# ADR-193: ProposeAction Primitive + Approval Loop

> **Status**: Proposed
> **Date**: 2026-04-17
> **Authors**: KVK, Claude
> **Extends**: ADR-168 (Primitive Matrix), ADR-189 (Three-Layer Cognition), ADR-191 (Polymath Operator ICP), ADR-192 (Write Primitive Coverage Expansion)
> **Depended on by**: ADR-194 (Surface Archetypes — operational pane renders proposals), ADR-195 (TP Autonomous Decision Loop — emits proposals rather than direct writes)

---

## Context

### The problem ADR-193 closes

After ADR-192, YARNNN has 14 new write primitives across trading / commerce / email. Every primitive can execute live operations with real consequences. Two failure modes block trusted autonomy:

1. **Risk-gate rejections are dead-ends.** When `check_risk_limits` rejects an autonomous order, the handler returns `{success: false, error: "risk_limit_violation"}`. YARNNN sees the error, the trader doesn't see the rejection at all. No path to "show the user what YARNNN wanted to do, let them approve or adjust."

2. **Autonomous writes have no approval surface.** Autonomous email campaigns, refunds, product updates, trades — they either execute immediately (unsafe for irreversible ops) or stay as drafts YARNNN never surfaces for approval. The current pattern says "draft by prompt guidance until ADR-193 ships" — we're now shipping 193.

The architectural gap: **YARNNN has no way to *propose* a write and *defer* its execution pending user approval.** Every write is either execute-now or don't-execute.

### The principle

Trusted autonomy lives between "always execute" (unsafe) and "always manual" (defeats the purpose). The middle path is **structured proposal + explicit approval**:

- YARNNN *proposes* the action with its rationale.
- The user sees the proposal with enough context to judge (what would happen, why, what's reversible).
- User approves → YARNNN executes. User modifies → YARNNN re-proposes adjusted. User rejects → proposal dies, reason captured for learning.

This is the pattern that lets operators delegate without surrendering control. It's what makes "run my e-commerce autonomously" viable.

---

## Decision

### 1. New primitive: `ProposeAction`

A chat primitive YARNNN can call instead of directly executing a write. Creates a persisted proposal artifact, renders in the chat stream as an approve/modify/reject card, and returns the proposal_id for YARNNN's narrative.

**Tool signature:**

```python
ProposeAction(
    action_type: str,              # e.g., "trading.submit_bracket_order"
    inputs: dict,                  # kwargs that would pass to execute_primitive
    rationale: str,                # why YARNNN proposes this
    expected_effect: str,          # human-readable preview of what would happen
    reversibility: str,            # "reversible" | "soft-reversible" | "irreversible"
    risk_warnings: list[str] = [], # from risk_gate or similar pre-validation
    task_slug: str = None,         # task that originated the proposal (optional)
    agent_slug: str = None,        # agent that originated (optional)
    expires_in_hours: int = None,  # override default TTL
)
```

**Returns:**

```python
{
    "success": True,
    "proposal_id": "<uuid>",
    "status": "pending",
    "expires_at": "<iso>",
}
```

**Example usage (YARNNN reasoning):**

> *"Competitor dropped price 10% on matching SKU. I'd match by updating the variant price from $1999 to $1799. This is reversible — I can revert anytime. Let me propose this."*
>
> ```
> ProposeAction(
>     action_type="commerce.update_variant",
>     inputs={"variant_id": "var_abc", "price_cents": 1799},
>     rationale="Competitor ACME dropped price to $17.99; matching to preserve market position.",
>     expected_effect="Product 'Widget Pro' price changes from $19.99 to $17.99. Future purchases at new price.",
>     reversibility="reversible",
> )
> ```

### 2. New primitive: `ExecuteProposal`

Takes a `proposal_id`, validates still-pending + not-expired, dispatches the action via `execute_primitive`, updates proposal status to `executed`, stores the result.

**Tool signature:**

```python
ExecuteProposal(
    proposal_id: str,
    modified_inputs: dict = None,  # user may modify before approving
)
```

**Behavior:**

1. Load proposal row. If status != "pending" → return `{success: False, error: "proposal_not_pending", status}`. If expired → return `{success: False, error: "proposal_expired"}`.
2. Resolve action handler from `action_type` (e.g., `"trading.submit_bracket_order"` → `_handle_trading_tool` with tool=`submit_bracket_order`).
3. Merge `modified_inputs` over `proposal.inputs` if provided (user adjustments).
4. Re-run any pre-validation (e.g., risk gate for trading) against merged inputs. Failure → return `{success: False, error, message}` + mark proposal as `rejected_at_execution`.
5. Dispatch via existing `execute_primitive` path. Capture result.
6. Update proposal: status=`executed`, executed_at=now, execution_result=<result>, approved_by=`user` (for now, always user until ADR-195 adds `auto_reversible` etc.).
7. Return `{success: True, proposal_id, execution_result}`.

### 3. New primitive: `RejectProposal`

User-triggered rejection (via approve/reject UX). Captures rejection reason for learning.

```python
RejectProposal(
    proposal_id: str,
    reason: str = "",  # optional; "user declined" if empty
)
```

Updates proposal: status=`rejected`, rejection_reason=`<reason>`. Used by the chat card's Reject button; can also be called directly by YARNNN on behalf of user.

### 4. New DB table: `action_proposals`

```sql
CREATE TABLE action_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    inputs JSONB NOT NULL,
    rationale TEXT,
    expected_effect TEXT,
    reversibility TEXT NOT NULL,  -- 'reversible' | 'soft-reversible' | 'irreversible'
    status TEXT NOT NULL DEFAULT 'pending',
        -- 'pending' | 'approved' | 'rejected' | 'executed'
        -- | 'expired' | 'rejected_at_execution'
    task_slug TEXT,
    agent_slug TEXT,
    risk_warnings JSONB,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    execution_result JSONB,
    rejection_reason TEXT,
    approved_by TEXT,  -- 'user' | 'auto_reversible' | (ADR-195 will add)

    CONSTRAINT action_proposals_reversibility_check
        CHECK (reversibility IN ('reversible', 'soft-reversible', 'irreversible')),
    CONSTRAINT action_proposals_status_check
        CHECK (status IN ('pending', 'approved', 'rejected', 'executed', 'expired', 'rejected_at_execution'))
);

CREATE INDEX action_proposals_user_status_idx
    ON action_proposals (user_id, status)
    WHERE status = 'pending';

CREATE INDEX action_proposals_expires_idx
    ON action_proposals (expires_at)
    WHERE status = 'pending';

CREATE INDEX action_proposals_task_idx
    ON action_proposals (task_slug)
    WHERE task_slug IS NOT NULL;

-- RLS: users see only their own proposals
ALTER TABLE action_proposals ENABLE ROW LEVEL SECURITY;
CREATE POLICY action_proposals_user_rw
    ON action_proposals FOR ALL
    USING (user_id = auth.uid());
```

Migration number: next available (check `supabase/migrations/`).

### 5. Default TTLs by reversibility

- `reversible` — 24 hours. Refund, product update, variant update, watchlist add/remove.
- `soft-reversible` — 6 hours. Campaign email send (reputational cost if revoked), order modification.
- `irreversible` — 1 hour. Trading orders (market moves), bulk price updates affecting many SKUs, autonomous send_bulk to a large list.

Rationale: irreversible actions must either be approved quickly or abandoned — market state moves, external effects compound. Override via `expires_in_hours` parameter when context warrants.

### 6. Integration with ADR-192 risk gate

When `check_risk_limits` is called with `mode="autonomous"` and returns rejected, the handler (currently returns a hard error) **emits a proposal instead** with:

- `risk_warnings = [gate.reason, ...gate.warnings]`
- `rationale = "Risk gate rejected this order. Review limits or approve override."`
- `reversibility = "irreversible"` (trading)
- `expires_in_hours = 1` (market urgency)

This turns the risk gate's rejection from a dead-end into a user-reviewable proposal. User can adjust `_risk.md` limits, approve override explicitly, or reject.

**Supervised-mode rejections remain hard errors** — the trader is in chat and can adjust inline without a proposal intermediary.

### 7. Execution dispatch mapping

`action_type` strings map to `execute_primitive` calls via a new `ACTION_DISPATCH_MAP`:

```python
ACTION_DISPATCH_MAP = {
    "trading.submit_order":              "platform_trading_submit_order",
    "trading.submit_bracket_order":      "platform_trading_submit_bracket_order",
    "trading.submit_trailing_stop":      "platform_trading_submit_trailing_stop",
    "trading.update_order":              "platform_trading_update_order",
    "trading.partial_close":             "platform_trading_partial_close",
    "trading.close_position":            "platform_trading_close_position",
    "trading.cancel_order":              "platform_trading_cancel_order",
    "trading.cancel_all_orders":         "platform_trading_cancel_all_orders",
    "commerce.create_product":           "platform_commerce_create_product",
    "commerce.update_product":           "platform_commerce_update_product",
    "commerce.create_discount":          "platform_commerce_create_discount",
    "commerce.issue_refund":             "platform_commerce_issue_refund",
    "commerce.update_variant":           "platform_commerce_update_variant",
    "commerce.bulk_update_variant_prices": "platform_commerce_bulk_update_variant_prices",
    "commerce.create_variant":           "platform_commerce_create_variant",
    "commerce.update_customer":          "platform_commerce_update_customer",
    "email.send":                        "platform_email_send",
    "email.send_bulk":                   "platform_email_send_bulk",
}
```

`ExecuteProposal` looks up the primitive name from this map, then calls `execute_primitive(auth, tool_name, merged_inputs)` — reuses the existing dispatch path.

### 8. Prompt guidance (when to propose vs execute)

YARNNN chooses between `ProposeAction` and directly calling a platform tool based on three conditions:

| Context | User present? | Risk/reversibility | Default choice |
|---------|--------------|--------------------|----------------|
| Chat, user explicitly asked for the action ("refund this order") | Yes | Any | Execute directly |
| Chat, YARNNN's own initiative ("I noticed X, want to do Y?") | Yes | Reversible | Execute directly if low-stakes; propose if irreversible |
| Chat, YARNNN's own initiative + irreversible | Yes | Irreversible | **Propose** |
| Autonomous (scheduled task / ADR-195 loop) + reversible | No | Reversible | Execute directly |
| Autonomous + soft-reversible or irreversible | No | Soft-reversible or irreversible | **Propose** |
| Autonomous + risk-gate rejection | No | Any | **Propose** (auto, per #6) |

Prompt section in `yarnnn_prompts/platforms.py` encodes this decision tree.

### 9. Inline chat artifact card

When `ProposeAction` executes successfully, the LLM's tool result includes a structured `proposal` object. The frontend `ChatPanel` / `InlineActionCard` renders it as:

```
┌─ Proposal ──────────────────────────────┐
│ Update variant price                    │
│ Widget Pro: $19.99 → $17.99            │
│                                         │
│ Why: Competitor ACME dropped to $17.99. │
│      Match to preserve market position. │
│ Reversibility: reversible               │
│ Expires: in 23h 42m                     │
│                                         │
│ [ Approve ] [ Modify ] [ Reject ]       │
└─────────────────────────────────────────┘
```

Approve button → calls `ExecuteProposal(proposal_id)` via existing TP chat API. Reject → `RejectProposal(proposal_id)`. Modify → opens a small form pre-filled with `inputs`; submit calls `ExecuteProposal(proposal_id, modified_inputs=<new>)`.

This is the minimum viable surface for ADR-193. A richer dedicated operational-pane surface for managing many pending proposals lives in ADR-194.

---

## What doesn't change

- **Primitive atomicity (ADR-168).** `ProposeAction` is a new atomic primitive; `ExecuteProposal` is a new atomic primitive; the underlying write primitives they defer are unchanged.
- **Risk gate (ADR-192 Phase 2).** Same rules, same `_risk.md` schema. Only the rejection *handling* changes for autonomous mode — rejections become proposals rather than errors.
- **Direct tool calls still work.** YARNNN can still call `platform_trading_submit_bracket_order` directly (bypassing `ProposeAction`) — appropriate when user is present and the action is explicitly requested. The approval loop is additive, not a wrapper.
- **Existing primitives — unchanged signatures.** `execute_primitive` dispatch unchanged. `ExecuteProposal` calls through the same path.
- **Supervised-mode risk-gate rejections remain hard errors.** No proposal layer for supervised — user is in chat and can adjust immediately.

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | **Helps** | Autonomous refunds + campaigns + bulk price updates become safe via approval loop. Operator sees what YARNNN wants to do before it happens. |
| **Day trader** | **Helps** | Risk-gate rejections in autonomous mode become approval proposals rather than silent errors. Trader reviews + approves override, or adjusts `_risk.md` limits. Load-bearing for trusted autonomous trading. |
| **AI influencer** (scheduled) | **Forward-helps** | Content publishing proposals will use the same primitive when that domain's alpha spins up. No special-casing needed. |
| **International trader** (scheduled) | **Forward-helps** | Compliance notices, counterparty comms, shipment actions — all autonomous proposals reuse the same flow. |

No domain hurt. No verticalization. Gate passes cleanly.

---

## Implementation sequence (five commits, direct to main)

| # | Phase | Scope |
|---|-------|-------|
| 1 | Migration + core primitives | SQL migration for `action_proposals` table. `ProposeAction` + `ExecuteProposal` + `RejectProposal` primitives + handlers. `ACTION_DISPATCH_MAP`. Primitive registry entries. |
| 2 | Frontend chat artifact card | `InlineActionCard` variant for proposals. Approve/Modify/Reject wiring. Reads proposal on server via existing chat API. |
| 3 | Risk-gate → proposal integration | `check_risk_limits` rejections in autonomous mode emit a proposal; handler returns proposal reference rather than hard error. Supervised mode unchanged. |
| 4 | Prompt guidance | `yarnnn_prompts/platforms.py` decision-tree for propose vs execute. Explicit autonomous-default rules. |
| 5 | Expiration cleanup | Back-office task (`back-office-proposal-cleanup`) runs daily, sets expired proposals to `status='expired'`. Deterministic Python executor per ADR-164. |

Order matters: Phase 1 must land before 2, 3, or 4 (they all need the primitives). Phase 2 and 3 independent of each other. Phase 4 depends on all prior. Phase 5 is closer + runs on schedule independently.

---

## Consequences

### Positive

1. **Trusted autonomy becomes real.** The combination of ADR-192 risk gate + ADR-193 approval loop is the minimum viable surface for "YARNNN acts autonomously within bounds, with the user reviewing only what matters."
2. **User supervision becomes scalable.** Instead of eyeballing every write, the operator reviews proposals — a small subset of "things worth a human decision."
3. **Learning loop.** Rejected proposals with reasons become training data for which autonomous patterns actually match operator intent. Can feed back into YARNNN's prompt refinement.
4. **Clean architectural split with ADR-194 + ADR-195.** ADR-193 is the primitive + minimal surface. ADR-194 renders proposals richly across `/work`, `/agents`, `/context`. ADR-195 generates proposals autonomously from signals. Each ADR has one clear job.
5. **Reversibility-aware TTLs.** Irreversible actions can't linger as stale proposals. Reversible actions get generous review windows.

### Costs

1. **New DB table + migration.** One-time schema addition. RLS + indexes + check constraints standard.
2. **Prompt complexity.** The propose-vs-execute decision tree adds cognitive load to YARNNN's tool use. Mitigation: clear rules in prompt, biased toward propose-when-in-doubt for autonomous paths.
3. **User-facing UX surface.** Inline card is the minimum; a flood of proposals (e.g., bulk_price_update proposed per variant) would overwhelm chat. Mitigation: `bulk_*` primitives propose the BATCH as one proposal, not per-item. Alternatively, ADR-194's operational pane aggregates many pending proposals cleanly.
4. **Approval-bypass risk.** A careless LLM implementation could skip `ProposeAction` when it should have proposed. Mitigation: prompt guidance + eval harness in Phase 4 that checks YARNNN uses `ProposeAction` appropriately across sample scenarios.

### Deferred

- **Auto-approval for repeated-pattern proposals.** "Always approve refunds under $50 from repeat customers." Belongs to ADR-195 (autonomous decision loop) — user declares approval rules, YARNNN auto-approves matching proposals.
- **Proposal batching / bundling.** "Here are 12 proposals at once; approve/reject in bulk." Defer to ADR-194 operational pane.
- **Proposal history + analytics.** Approval rates, rejection reasons by action type, time-to-approval distributions. Valuable for ADR-195 tuning; defer to post-195 observability pass.
- **Modify UX sophistication.** Phase 2 ships with a basic form-based modify. A richer diff-view (show what changes) is a later polish.
- **Cross-domain approval policies.** E.g., "always propose email sends, never refunds." Per-user policy config in `_approvals.md` workspace file. Defer until observed friction surfaces the need.

---

## Open questions

1. **Approval source of truth: DB vs workspace file.** Chose DB (`action_proposals` table) for: fast status queries, indexable expires_at, RLS. Could alternatively live in `/workspace/proposals/*.md` for filesystem-native consistency with rest of YARNNN. DB wins on ergonomics for now; revisit if filesystem-first philosophy (ADR-159) demands migration.
2. **Who can approve.** Today: only the user. Future: delegated approval (e.g., via MCP to a second LLM, or time-based auto-approve). Out of scope for 193.
3. **Proposal notifications.** If YARNNN proposes at 3am while user is asleep, should they get an email? Probably yes for trading (market urgency); probably no for e-commerce (can wait). Config via `_approvals.md` later.
4. **Proposal UX in non-chat surfaces.** Operational pane (ADR-194) is the natural home. Settings page could show "12 pending proposals" badge. Defer to ADR-194.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial proposal. Three new primitives (ProposeAction, ExecuteProposal, RejectProposal), new `action_proposals` DB table, integration with ADR-192 risk gate, five-phase implementation plan, reversibility-aware TTLs. |
