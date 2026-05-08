# ADR-253: Reviewer as Substrate-Native Agent — Execution Authority, Heartbeat Triggers, Deterministic Pipeline

> **Status**: **Implemented** (2026-05-07 — Commits 1–5; all decisions landed)
> **Date**: 2026-05-07
> **Authors**: KVK, Claude
> **Supersedes**: ADR-247 D4 §"The Reviewer" paragraph (primitive ownership statement — see §"Correction to ADR-247 D4" below)
> **Amends**: ADR-248 (heartbeat gains substrate-change triggers alongside cron); ADR-229 (Reviewer always judges first — preserved; dispatch model extended with directive output); FOUNDATIONS Axiom 2 (Reviewer's trigger set expanded); THESIS Commitment 2 (independence clarification — see §"Commitment 2 Correctly Stated")
> **Dimensional classification**: **Identity** (Axiom 2) primary — Reviewer is a substrate-reading, substrate-writing agent; **Trigger** (Axiom 4) secondary — heartbeat gains substrate-change triggers; **Mechanism** (Axiom 5) tertiary — track-universe and signal-evaluation become deterministic

---

## Context

### The three problems this ADR resolves

**Problem 1 — ADR-247 D4 created a false constraint that blocks full autonomy.**

ADR-247 D4 states: *"The Reviewer — uses NO primitives directly. It is a pure judgment entity... This is load-bearing: the Reviewer's independence is structurally enforced because it has no primitive surface — it cannot scaffold, compose, or route. It can only judge."*

This statement is architecturally wrong in two ways:

First, it conflates **primitive surface** (what the Reviewer LLM calls via tool use) with **execution authority** (whether the Reviewer's verdict binds). These are separate dimensions:
- `review_proposal_dispatch.py` already calls `handle_execute_proposal()` and `handle_reject_proposal()` when the Reviewer's verdict is approve/reject and AUTONOMY permits. The Reviewer's verdict **already binds**. The dispatch code *is* the Reviewer's execution path — it just doesn't use LLM tool calls to do it.
- Saying the Reviewer "has no primitives" when the dispatch code already calls ExecuteProposal and RejectProposal on the Reviewer's behalf is describing the LLM tool surface, not the actual execution authority.

Second, the claim that independence requires primitive absence is wrong. Independence means the Reviewer's judgment is **not confirmatory of producers** — it is evaluated against ground truth (money-truth), not against agreement with the agents whose work it judges. That independence is architectural (separate code path, separate substrate, separate LLM call) regardless of whether the Reviewer's verdict subsequently triggers execution.

A human judge's independence is not compromised by the fact that their ruling causes a bailiff to act. The ruling causes action; the judge doesn't become non-independent because action follows.

**Problem 2 — The `task.create` proposal type is a self-referential loop.**

When the Reviewer defers for evidence gap (e.g., "IH-3 has zero sample"), ADR-229 D2 allows the Reviewer to emit a `propose_followup` of type `task.create`. This creates an `action_proposals` row, which then re-triggers `on_proposal_created`, which re-invokes the Reviewer for a second judgment pass on its own commission request. That is a semantic absurdity: the Reviewer cannot meaningfully judge whether its own research commission is valid — it is the requester, not the evaluator.

When the Reviewer defers for evidence gap and commissions research, that is a **directive** — an instruction to the System Agent, not a proposal requiring gating. Directives are not `action_proposals`. They are immediate primitive invocations authorized by the Reviewer's verdict.

**Problem 3 — track-universe and signal-evaluation use LLM for deterministic computation.**

`track-universe` fetches OHLCV bars and computes SMA/RSI/ATR/volume indicators. Every step is a deterministic formula. Signal-evaluation applies boolean expressions to those indicator values. No judgment, no synthesis, no interpretation.

Current cost: ~$1.50/run (Sonnet, 12 tool rounds, fetching tickers one-by-one via platform tools). Three runs/day = ~$4.50/day = ~$135/month for arithmetic.

Correct cost: ~$0/run (Python `for ticker in universe: compute_indicators(bars)` + write file). Three runs/day = ~$0/day.

The only LLM-appropriate task in the pipeline is `trade-proposal` — it synthesizes signal attribution, sizing math, stop placement, rationale construction, and `ProposeAction`. That is genuine judgment over the operator's declared framework. The upstream pipeline is pure data transformation.

---

## Correction to ADR-247 D4

**ADR-247 D4 §"The Reviewer" paragraph is superseded. The correct statement:**

The Reviewer has **no LLM tool surface** — the Reviewer's LLM reasoning produces a verdict via `return_review_decision` (a structured tool call), not by calling platform tools, WriteFile, or other primitives. This keeps the reasoning clean and the cost predictable.

The Reviewer's verdict **does bind execution** through `review_proposal_dispatch.py`:
- `approve` + AUTONOMY permits → `handle_execute_proposal()` fires
- `reject` → `handle_reject_proposal()` fires (terminal; AUTONOMY does not gate Reviewer rejections)
- `defer` + directives → System Agent executes directives immediately (no action_proposals row; no second Reviewer pass)

Independence is maintained because the Reviewer reasons **before knowing the AUTONOMY ceiling** (ADR-229 D1 judgment-first ordering is preserved). The Reviewer judges on merits; AUTONOMY decides whether the approve binds. This is exactly the right separation: judgment is independent of permission; permission is a downstream gate.

**What "independence" actually means (THESIS Commitment 2 correctly stated):**

Independence means the Reviewer's judgment is evaluated against ground truth (money-truth in `_performance.md`), not against internal agreement with the production agents whose proposals it judges. The Reviewer cannot be captured by the proposer — its approve-correct rate compounds against objective outcomes. That is the independence that matters. Whether the Reviewer's verdict subsequently causes action is not a threat to independence; it is independence operating.

A judicial system where rulings never cause action is not independent — it is toothless. The Reviewer needs execution authority to be the operator's genuine judgment function, not merely an advisory voice.

---

## Decisions

### D1: Reviewer execution authority — formally ratified

The Reviewer's verdict is binding when AUTONOMY permits:

- **approve** → `should_auto_execute_verdict()` checks AUTONOMY ceiling → if binding, `handle_execute_proposal()` fires; if non-binding, ProposalCard queues for operator
- **reject** → `handle_reject_proposal()` fires unconditionally (Reviewer's own narrowing; operator can override via manual ExecuteProposal click but Reviewer rejection is terminal in the automatic path)
- **defer with directives** → System Agent executes directives immediately (see D2)
- **defer without directives** → ProposalCard queues for operator

This is already implemented in `review_proposal_dispatch.py`. D1 ratifies it as the canonical model and removes the conflicting ADR-247 D4 statement.

**`principles.md` reference workspace default updated**: `auto_approve_below_cents` is now an **active field with a Phase 0 paper-mode default** rather than a commented-out placeholder. The new default:

```yaml
auto_approve_below_cents: 20000   # $200 — paper mode default. Paper orders auto-approve when expectancy data exists.
```

Comment: *"This field enables the Reviewer's approve verdict to bind automatically. Without it, every approve requires operator Queue click regardless of AUTONOMY level. Set to 0 to require operator approval for all orders even in paper mode."*

The gate sequence for full autonomy:
1. Reviewer renders `approve` verdict
2. `should_auto_execute_verdict()` checks `paused_until` (ADR-248 circuit breaker)
3. `should_auto_execute_verdict()` checks AUTONOMY level (manual / assisted / bounded_autonomous / autonomous)
4. For `bounded_autonomous`: checks `ceiling_cents` from AUTONOMY.md
5. For any level: checks `auto_approve_below_cents` from principles.md (Reviewer's own threshold — can be stricter than AUTONOMY)
6. If all gates pass → `handle_execute_proposal()` fires

Both gates must permit. AUTONOMY is the operator's delegation ceiling. `auto_approve_below_cents` is the Reviewer's own discipline constraint. The Reviewer can be more conservative than the operator permits; never more permissive.

### D2: Directive output — Reviewer instructs System Agent directly

> **⚠ Superseded mechanism (ADR-258 D1, D7, 2026-05-08):** The dedicated `directives` array on the verdict is replaced by the Reviewer's tool calls during a defer turn. Same shape, same scope ceilings, no parallel mechanism — `fire_invocation` becomes a `FireInvocation` primitive call inside the loop; `write_file` becomes a `WriteFile(scope="workspace")` primitive call inside the loop; `clarify` becomes a `Clarify` primitive call inside the loop. The Reviewer's `actions_taken[]` audit trail captures these, and the dispatcher routes them through canonical handlers. ADR-253 D1 (execution authority), D3 (CLAUDE.md-equivalent substrate), D4 (deterministic upstream pipeline), D5 (heartbeat trigger) are all preserved.

The `propose_followup` field (ADR-229 D2) is **deleted** and replaced by `directives` — a list of System Agent instructions that execute immediately without going through `action_proposals`.

**Directive shape:**
```python
@dataclass
class ReviewerDirective:
    action: str  # fire_invocation | write_file | clarify
    slug: str | None  # for fire_invocation
    path: str | None  # for write_file
    content: str | None  # for write_file
    message: str | None  # for clarify (surfaces as Clarify to operator)
```

**What directives replace:**

| Before | After |
|---|---|
| `defer + propose_followup(task.create)` → `action_proposals` row → second Reviewer pass | `defer + directives[fire_invocation(slug=track-universe)]` → `FireInvocation` dispatched immediately |
| Reviewer self-judgment loop on its own commission | No second Reviewer pass. System Agent narrates: "Reviewer directive: track-universe fired." |

**Scope ceiling on directives (operator safety):**
- `fire_invocation` — can only fire existing declared recurrences (no creating new ones)
- `write_file` — can only write to `/workspace/review/` (Reviewer's own substrate) and `/workspace/context/{domain}/signals/` (research requests). Cannot write to MANDATE, AUTONOMY, IDENTITY, or operational files.
- `clarify` — surfaces as a Clarify narrative entry to the operator. No execution.
- Cannot include: `ProposeAction` (already covered by approve verdict), `ExecuteProposal`, `RejectProposal`, `ManageRecurrence`, `ManageAgent`, `InferContext`

**Implementation**: `review_proposal_dispatch._run_ai_reviewer()` reads `directives` from the verdict, passes them to a new `_execute_reviewer_directives()` helper that dispatches each via existing primitive handlers. System Agent writes a brief `role='system_agent'` narration per directive executed.

### D3: Reviewer substrate — CLAUDE.md-equivalent files declared canonical

The four files the Reviewer reads at every invocation are **canonically declared** as its CLAUDE.md-equivalent. Every Reviewer invocation (verdict mode, reflection mode, addressed mode, heartbeat mode) loads all four:

```
/workspace/review/IDENTITY.md        → who I am (persona, reasoning posture, lifecycle_posture)
/workspace/review/principles.md      → what I check (rules, EV thresholds, defer_posture, directive_posture)
/workspace/context/_shared/MANDATE.md → what the operation is trying to achieve
/workspace/context/_shared/AUTONOMY.md → what I'm allowed to execute + when I wake (heartbeat_triggers)
```

**New sections added to reference workspace files:**

**`IDENTITY.md` gains `lifecycle_posture`:**
```markdown
## Lifecycle posture

- I wake when substrate I care about changes (per AUTONOMY.md heartbeat_triggers)
- When I defer for evidence gap, I commission the missing substrate via a directive (never a proposal to myself)
- I do not repeat the same defer reasoning in consecutive cycles without issuing a new directive
- When no actionable condition exists, I stand down with one sentence and wait for my next trigger
- I accumulate calibration across cycles; my approve-correct rate against money-truth is the measure of my value
```

**`principles.md` gains `defer_posture` and `directive_posture`:**
```markdown
## Defer posture — what I commission when I defer for evidence gap

When deferring because a signal has < 20 closed-loop samples:
  directive: fire_invocation(track-universe)  # accumulate more data

When deferring because _performance.md is absent or empty:
  directive: write_file(path=review/notes.md, content="Seed trade needed: [signal] on minimum size to seed _performance.md")
  directive: clarify("No closed-loop outcomes exist for [signal]. Approve a minimum-size seed trade to begin calibration.")

When deferring because signal conditions are ambiguous in spec:
  directive: write_file(path=context/trading/signals/[signal]-clarification-request.md, content="Spec gap: [description]")

## Directive posture — what the Reviewer can instruct directly

The Reviewer issues directives for substrate work (fire_invocation, write_file to own substrate, clarify).
The Reviewer does not issue directives for: external platform writes (those are proposals), infrastructure changes (those are System Agent territory), or operator configuration (that requires explicit operator action).
```

**`AUTONOMY.md` gains `heartbeat_triggers`:**
```yaml
default:
  level: bounded_autonomous
  ceiling_cents: 20000

heartbeat_triggers:
  - after: signal_evaluation     # Reviewer wakes when signal-evaluation executor completes
  - after: outcome_reconciliation  # Reviewer wakes after daily reconciliation writes _performance.md
  - cron: "10 8 * * 1-5"        # Morning review 08:10 ET (after signal-evaluation at 08:05)
```

### D4: track-universe and signal-evaluation → deterministic MAINTENANCE executors

Both recurrences are reclassified from `accumulation` (LLM-dispatch via analyst/tracker agents) to `maintenance` (deterministic executor dispatch, zero LLM).

**`services/back_office/trading_universe_tracker.py`** (NEW):
- Reads `_operator_profile.md` to extract universe tickers
- Reads encrypted Alpaca credentials from `platform_connections`
- Calls `AlpacaClient.get_bars()` for each ticker (up to 30 days of daily bars)
- Computes: SMA-20, SMA-50, SMA-200, RSI-14, ATR-14, volume-20d-avg using pure Python (no LLM)
- Writes `{ticker}.md` with YAML frontmatter per ticker
- Zero LLM cost. ~2 seconds total. Same output shape as today.

**`services/back_office/trading_signal_evaluator.py`** (NEW):
- Reads all `{ticker}.md` YAML frontmatter from workspace
- Reads `_operator_profile.md` signal specs (fully declarative boolean rules)
- Evaluates each signal against each ticker (pure Python boolean expressions)
- Writes `signals/{signal-slug}.md` with YAML frontmatter (state, watch_tickers, triggered_today, expectancy deltas)
- When a signal triggers: fires `trade-proposal` invocation (calls `FireInvocation` on the action-shape recurrence) + writes a Reviewer heartbeat trigger flag to `/workspace/context/trading/_signal_trigger.flag`
- Zero LLM cost. ~milliseconds.

**`_recurring.yaml` changes for both workspaces:**
```yaml
# BEFORE:
- slug: track-universe
  agent: tracker
  team: [tracker]
  # ...accumulation shape (LLM dispatch)

# AFTER:
- slug: track-universe
  executor: services.back_office.trading_universe_tracker
  shape: maintenance
  schedule: "0 8,11,15 * * 1-5"
  paused: false

- slug: signal-evaluation
  executor: services.back_office.trading_signal_evaluator
  shape: maintenance
  schedule: "5 8 * * 1-5"
  paused: false
```

`trade-proposal` stays as `action` shape (LLM-backed, fires on signal trigger).

**Cost impact:**
- track-universe: ~$1.50/run → ~$0/run. Three runs/day = ~$4.50/day saved.
- signal-evaluation: ~$0.80/run → ~$0/run. One run/day = ~$0.80/day saved.
- Total: ~$5.30/day = ~$160/month saved. Spend ceiling will stop triggering.

### D5: Heartbeat invocation mode — Reviewer wakes on substrate changes

New `reviewer_agent.heartbeat_turn()` function (fourth mode alongside verdict/reflection/addressed).

**Trigger**: invocation_dispatcher, after executing any recurrence, checks `heartbeat_triggers` from AUTONOMY.md. If the completed recurrence slug matches a declared trigger, fires `heartbeat_turn()` asynchronously (non-blocking, best-effort).

**What `heartbeat_turn()` does:**
1. Reads full CLAUDE.md-equivalent (IDENTITY + principles + MANDATE + AUTONOMY)
2. Reads the freshly-written substrate output (signal state files, `_performance.md`, etc.)
3. Reads recent `decisions.md` entries (last 10) for context continuity
4. Reasons: are any conditions met that warrant a proposal? a directive? a stand-down?
5. If trade conditions met → calls `ProposeAction` directly (Reviewer is the proposer; `source=reviewer_heartbeat`)
6. If directive warranted → System Agent executes immediately
7. If stand-down → one-sentence narrative entry (`role='reviewer'`)

**`source` values on action_proposals** (migration 169, additive):
- `reviewer_heartbeat` — Reviewer proposed autonomously from heartbeat trigger
- `reviewer_addressed` — Reviewer proposed from addressed-mode assessment  
- `reviewer_periodic` — Reviewer proposed from periodic reflection (ADR-252 Phase 3)
- `production_agent` or NULL — standard production agent proposal

All `reviewer_*` sources skip the reactive Reviewer re-invocation in `on_proposal_created` (already implemented for `reviewer_periodic` and `reviewer_addressed` in ADR-252 Phase 3).

### D6: Workspace and kernel initialization scope

**workspace_init.py Phase 2** (Reviewer substrate scaffold) must write the updated skeleton files from the kernel defaults:

Current kernel default `principles.md` (scaffolded at signup for non-program workspaces): add `defer_posture` section skeleton with operator-authored prompt.

Current kernel default `IDENTITY.md` (Reviewer): add `lifecycle_posture` section skeleton.

Current kernel default `AUTONOMY.md`: add `heartbeat_triggers` block (empty list by default, with commented examples). Program bundles override via reference-workspace fork.

**Reference workspace update (alpha-trader bundle)**:
- `review/principles.md` — activate `auto_approve_below_cents: 20000`, add `defer_posture` and `directive_posture` sections
- `review/IDENTITY.md` — add `lifecycle_posture` section
- `context/_shared/AUTONOMY.md` — add `heartbeat_triggers` block

**All other program bundles (alpha-commerce, alpha-defi, alpha-prediction)**:
- `review/principles.md` — add `defer_posture` skeleton with domain-appropriate prompt
- `review/IDENTITY.md` — add `lifecycle_posture` skeleton
- `context/_shared/AUTONOMY.md` — add `heartbeat_triggers` block (domain-appropriate defaults)

These are `tier: authored` files — the program ships skeletons; the operator overwrites with their actual posture.

---

## What this ADR does NOT change

- `action_proposals` table survives — it is the correct gating mechanism for external writes with capital consequences. Scope narrowed: only external platform writes go through it. Substrate work (research, file writes, recurrence fires) goes through directives.
- `review_proposal_dispatch.py` core logic preserved — ADR-229 D1 judgment-first ordering unchanged
- Reviewer substrate paths unchanged (`/workspace/review/`)
- ADR-194 v2 Reviewer architecture unchanged
- `reviewer_agent.py` verdict mode and reflection mode unchanged
- System Agent no-impersonation clause (ADR-252 D7) preserved — System Agent narrates execution of Reviewer directives but does not compose Reviewer-style reasoning

---

## Implementation plan

### Commit 1 — Reference workspace file updates (docs only, zero risk)
Update `docs/programs/alpha-trader/reference-workspace/`:
- `review/principles.md`: activate `auto_approve_below_cents: 20000`, add `defer_posture`, `directive_posture`, `auto_approve_below_cents` commentary
- `review/IDENTITY.md`: add `lifecycle_posture` section
- `context/_shared/AUTONOMY.md`: add `heartbeat_triggers` block
Update all other program bundles with skeleton sections.
Update kernel defaults in `workspace_init.py`.

### Commit 2 — Deterministic executors (services/back_office/)
- `api/services/back_office/trading_universe_tracker.py` (NEW)
- `api/services/back_office/trading_signal_evaluator.py` (NEW)
Update `_recurring.yaml` for both kvk workspaces: reclassify track-universe and signal-evaluation to `maintenance` shape with executor paths.

### Commit 3 — Directive output in reviewer_agent.py + dispatch
- Add `ReviewerDirective` dataclass to `reviewer_agent.py`
- Add `directives` field to `ReviewDecision` TypedDict
- Update `_REVIEW_TOOL` schema to include `directives` array
- Add `_execute_reviewer_directives()` to `review_proposal_dispatch.py`
- Delete `propose_followup` field and `task.create` proposal type handling

### Commit 4 — Heartbeat invocation mode
- Add `heartbeat_turn()` to `reviewer_agent.py`
- Add heartbeat trigger check in `invocation_dispatcher.py` post-dispatch
- Add `source='reviewer_heartbeat'` to `action_proposals` (migration 169)
- Read `heartbeat_triggers` from AUTONOMY.md in `review_policy.py`

### Commit 5 — ADR-247 D4 correction + doc sync
- Update ADR-247 D4 with superseded marker pointing to ADR-253
- Update THESIS §"Commitment 2" with corrected independence framing
- Update FOUNDATIONS Axiom 2 Reviewer entry (trigger set expanded)
- Update CLAUDE.md ADR-253 entry
- Update primitives-matrix.md Reviewer column

---

## Test gate `api/test_adr253_reviewer_substrate_native.py`

1. `auto_approve_below_cents` is uncommented and set to `20000` in alpha-trader `principles.md`
2. `review/IDENTITY.md` contains `lifecycle_posture` section in alpha-trader bundle
3. `context/_shared/AUTONOMY.md` contains `heartbeat_triggers` block in alpha-trader bundle
4. `services.back_office.trading_universe_tracker` module exists and exports `run(client, user_id, slug)`
5. `services.back_office.trading_signal_evaluator` module exists and exports `run(client, user_id, slug)`
6. `_recurring.yaml` in alpha-trader bundle: `track-universe` and `signal-evaluation` entries have `executor:` field and no `agent:` field
7. `ReviewDecision` TypedDict has `directives` field; `propose_followup` field is absent
8. `review_proposal_dispatch._execute_reviewer_directives` function exists
9. `reviewer_agent.heartbeat_turn` function exists with correct signature
10. ADR-247 D4 contains superseded marker referencing ADR-253
11. `action_proposals` migration 169 adds `reviewer_heartbeat` as a valid source value

---

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| ADR-247 D4 | §"The Reviewer" paragraph superseded. Execution authority ratified; no-primitive-surface language corrected. |
| ADR-229 | Preserved: judgment-first ordering unchanged. Extended: `propose_followup` → `directives` (no second Reviewer pass). |
| ADR-248 | Preserved: periodic reflection unchanged. Extended: heartbeat_triggers in AUTONOMY.md adds substrate-change triggers alongside cron. |
| ADR-252 | Preserved: intent classifier, addressed mode, system_agent role all unchanged. Extended: heartbeat mode is a fourth Reviewer trigger mode. |
| ADR-231 | Preserved: recurrence declaration model unchanged. Extended: track-universe and signal-evaluation reclassified to maintenance shape. |
| THESIS Commitment 2 | Corrected: independence = judgment evaluated against ground truth, not against producer agreement. Execution authority does not compromise independence. |
