# ADR-229: Judgment-First Dispatch + Generative Defer + Universal Narrative Coverage

> **Status:** **Phase 1 Implemented 2026-04-28** (gate inversion + Reviewer prompt v6 with `propose_followup` shape + narrative emission widened to non-delivered runs).
> **Authors:** KVK, Claude
> **Supersedes:** the pre-judgment ordering of `is_eligible_for_auto_approve` in `services/review_proposal_dispatch.py`. The autonomy gate is renamed to `should_auto_execute_verdict` and runs *after* judgment, not before.
> **Amends:** ADR-194 v2 §1 (Reviewer purpose widens — generative defer is a first-class verdict outcome), ADR-217 D5 (the eligibility computation runs as a post-judgment binding gate, not a pre-judgment dispatch gate), ADR-219 D2 (narrative coverage invariant extends to failed and skipped task invocations, not just `delivered`).
> **Depends on:** ADR-194 v2 (Reviewer layer), ADR-216 (orchestration vs judgment-persona), ADR-217 (autonomy ladder), ADR-219 (invocation/narrative substrate), FOUNDATIONS Axioms 5 (Mechanism), 6 (Channel), 7 (Recursion), 9 (Invocation atom).
> **Related:** Today's session — Phase B (operator-click execution validation) + Path C (autonomous Reviewer defer), surfaced the structural property this ADR addresses.

---

## Context

Today's two end-to-end validations on alpha-trader-1 (seulkim88) closed the upstream loop chain (AGENT.md staleness fix, Pydantic field-drop on `required_capabilities`, output-kind-aware `max_tokens`, AUTONOMY.md schema rewrite). Path B (operator-click) executed cleanly — Alpaca paper order `9b8879fe-1af5-46e5-bbc3-bea2e8e585c5` accepted. Path C (autonomous AI Reviewer) ran Sonnet on a small reversible SPY proposal and returned `defer` with high-confidence reasoning. The Reviewer's verdict (verbatim from `/workspace/review/decisions.md`):

> *"Check 1 fires structurally: this proposal names no signal from `_operator_profile.md`... Check 4 independently requires deferral: `_performance.md` is empty, which triggers the 'sparse data < 5 trades → defer with thin_track_record reason' rule... The correct resolution is to surface this tension via the Queue so the operator can either (a) add a PRECEDENT.md carve-out explicitly exempting paper-validation bootstrap orders from Check 1 and Check 4, or (b) manually click through the first trade to seed `_performance.md`."*

The Reviewer correctly identified what the audit chain has been circling: **the system is correctly conservative when track record is thin, but it cannot autonomously generate the track record that would make it less conservative**. Every cold-start workspace is structurally locked into "human-clicks-everything" until either operator-authored carve-outs or operator-clicked trades fill `_performance.md` past the sparse-data threshold.

Three claims emerged from the post-validation discourse, each tested in stress-audit:

1. **Autonomy and judgment are conflated in the dispatch path** (correct in symptom, the cleanest fix is gate-ordering inversion, not loop-separation).
2. **Work isn't actually chat-native** (correct symptom, mechanism is implementation gap against ADR-219 canon — narrative emission gate excludes failed/skipped runs, session resolver returns None for autonomous-only workspaces).
3. **The Reviewer is the true actor on behalf** (deeply right in spirit; ADR-216 already says this, more cautiously; the natural endpoint is "Reviewer is the actor for consequence-bearing writes; production roles are the actors for substrate accumulation").

The bootstrap paradox dissolves under Claim 3 — but only because `defer` becomes generative. Today's `defer` writes to `decisions.md` and exits (terminal node). If `defer` can carry a follow-up proposal — *"I need 60 days of IH-1-vs-AAPL performance; create a research task"* — the Reviewer is no longer stuck. It asks for what it needs, the proposed task fires, substrate accumulates, the next similar proposal has the data the Reviewer asked for.

The infrastructure already exists (`ProposeAction`, `ManageTask(action="create")`, Reviewer Sonnet tool-use). What's missing is (a) gate ordering that lets judgment run before autonomy filters its outcome, (b) a Reviewer prompt that includes `defer + propose_followup` as a tool-call shape, (c) narrative emission coverage that doesn't silently swallow failed runs.

---

## Decision

### D1 — Gate inversion: judgment runs first, autonomy filters its outcome

The dispatch ordering changes from `eligibility → judgment → action` to `judgment → eligibility → action-or-queue`.

**Today (rejected):**

```
on_proposal_created → load AUTONOMY → is_eligible_for_auto_approve(autonomy, action_type, estimated_cents, reversibility)
  if NOT eligible → observe-only path (defer to human, AI never runs)
  if eligible    → AI Reviewer runs → approve/reject/defer
```

**Under D1 (this ADR):**

```
on_proposal_created → AI Reviewer runs ALWAYS (when domain has reviewable substrate)
  Reviewer returns verdict + reasoning + (optional) propose_followup
  → load AUTONOMY → should_auto_execute_verdict(autonomy_policy, verdict, action_type, estimated_cents, reversibility)
    if verdict == approve AND should_auto_execute_verdict → handle_execute_proposal (binding)
    if verdict == approve AND NOT should_auto_execute_verdict → queue (advisory; operator clicks)
    if verdict == reject  → handle_reject_proposal (Reviewer is master of its own narrowing)
    if verdict == defer   → write decisions.md entry; if propose_followup present, dispatch as fresh ProposeAction
```

**Why this is the right cut, not "separate autonomy from judgment into two loops":**

- Judgment is *who acts on behalf*. Autonomy is *whether the operator's standing intent permits the action to bind*. They are different layers of the same decision; they do not need to be separate loops, they need to be in the right order.
- Today's pre-judgment gate forfeits Reviewer calibration on the proposals where calibration matters most (the ones outside the autonomy ceiling — the operator NEEDS the Reviewer's read on those before clicking).
- ADR-217 D4 ("the servant can be more conservative than the master permits, never more permissive") is preserved: the Reviewer's verdict is the *upper bound* on what executes; AUTONOMY is the *upper bound on whether that verdict binds*. Strictest of the two wins.
- The bootstrap paradox dissolves: a Reviewer that *always runs* always produces reasoning, and reasoning can carry follow-up. Today's gate produces silent observe-only entries that do nothing.

The function is renamed `is_eligible_for_auto_approve → should_auto_execute_verdict` (ADR-217 D5 amendment). Same parameters, different semantic position in the dispatch chain. The signature accepts `verdict` so `reject` and `defer` always route to non-binding paths regardless of autonomy.

### D2 — Generative defer: Reviewer can return `propose_followup`

The Reviewer's tool contract widens. Today's `return_review_decision` accepts `decision`, `reasoning`, `confidence`. Under D2 it accepts an optional fourth field:

```json
{
  "decision": "defer",
  "reasoning": "...",
  "confidence": "high",
  "propose_followup": {
    "action_type": "task.create",
    "inputs": {
      "title": "60-day IH-1 vs AAPL backtest",
      "agent_slug": "researcher",
      "mode": "goal",
      "objective": "Compute hit-rate and expectancy of IH-1 (5-day RSI < 25) on AAPL over the last 60 trading days.",
      "context_reads": ["trading"],
      "context_writes": ["trading"]
    },
    "rationale": "I cannot evaluate this proposal because _performance.md is empty for IH-1. Run this backtest to seed the track record."
  }
}
```

When `propose_followup` is present on a `defer` verdict, `_run_ai_reviewer` dispatches it as a fresh `ProposeAction`. The new proposal goes through D1's full dispatch: Reviewer reasons on it (recursive, but the reviewer-of-the-reviewer's-followup runs against simpler substrate — task creation is reversible and cheap, almost always auto-approves under any non-`manual` autonomy posture).

**Constraints on `propose_followup`:**

1. Only emitted on `decision="defer"`. Not valid on `approve` (the Reviewer cannot bypass operator approval through follow-up) or `reject` (the Reviewer's own narrowing is its final word; rejection is terminal).
2. The follow-up's `action_type` must be reversible AND have neutral capital impact. Practical scope: `task.create`, `context.read_more`, `signal.observe`, `position.review`. Trading writes are NOT permitted as follow-ups (the Reviewer cannot side-channel into capital action).
3. Reasoning must explicitly justify why the follow-up is needed AND what evidence shape would let the Reviewer reconsider the original proposal.
4. The original proposal stays `pending` (or expires per its TTL) — the follow-up does not auto-resolve it. The operator can still click Approve/Reject; the Reviewer is asking for evidence, not blocking.

**Why this dissolves the bootstrap paradox:** the Reviewer's `defer` is no longer a terminal node. It becomes the *recursion engine* (FOUNDATIONS Axiom 7) that pulls the loop forward. Cold-start workspaces are still conservative — the Reviewer correctly defers — but defer now generates the substrate-building work that warms the start.

### D3 — Universal narrative coverage: failed and skipped invocations also emit

The narrative-emission gate at `task_pipeline.py:2438` changes from:

```python
if final_status == "delivered" and task_slug != "daily-update" and not task_slug.startswith("back-office-"):
```

to:

```python
if final_status in ("delivered", "failed") and task_slug != "daily-update" and not task_slug.startswith("back-office-"):
```

(Skipped runs that don't reach this point — balance-gate skips, capability-gate skips — get their own narrative entry from the `_fail` path; see implementation note.)

The narrative envelope already supports `weight: "material" | "routine" | "housekeeping"`. Failed runs get `weight: "routine"` (operator should know but it isn't material to the operation's status). Successful delivery stays `weight: "material"`. The shape is unchanged — only the gate widens.

**Why:** Per Axiom 9 D2, every invocation emits exactly one narrative entry. Pre-ADR-229 a failed task run is invisible to the operator's chat surface; the operator only learns from the cockpit's task-detail page that the task ran and failed. This violates "chat is the narrative substrate." Under D3, every invocation (success, failure, skip) lands a narrative line.

### D4 — Session resolver tolerates autonomous-only workspaces

`services.narrative.find_active_workspace_session` today returns None when no `chat_sessions` row has been opened in the workspace's recency window. This is correct behavior for "is there an active operator session to surface to" — but it makes autonomous-only workspaces structurally invisible.

Under D4, when the resolver returns None during a narrative-emission attempt, the writer falls back to creating a fresh `chat_sessions` row (system-initiated, `metadata.session_origin: "narrative_autopromote"`). This is the same shape as ADR-219 Commit 3's session-promotion idea, applied at the writer level rather than during operator chat.

**Why:** Without D4, D3's widened narrative emission still loses entries for the long-running autonomous workspaces that need it most. The auto-promoted session is the operator's chat surface waiting to be opened; opening it the next time they visit `/chat` reveals the full narrative log of the autonomous loop's activity.

### D5 — Reviewer prompt v6: `propose_followup` invariants in the system prompt

`api/agents/reviewer_agent.py::_SYSTEM_PROMPT` gets a new section explicitly declaring D2's contract:

> **Generative defer (ADR-229).** When you defer because evidence is insufficient (sparse `_performance.md`, ambiguous signal, missing context), you may include a `propose_followup` field naming a research/observation task that would let you reconsider. Constraints: (a) only on `defer`, never on `approve` or `reject`; (b) follow-up `action_type` must be reversible and capital-neutral (`task.create`, `context.read_more`, `signal.observe`, `position.review` — no trading writes); (c) reasoning must specify what evidence shape would unblock the original proposal. The follow-up is NOT a workaround for autonomy — if AUTONOMY.md narrows the original proposal, your defer remains a defer regardless of whether you also propose evidence-gathering. The follow-up is *recursion*, not *bypass*.

`REVIEWER_MODEL_IDENTITY` bumps `v5 → v6`. Token budget is unchanged (~1–2K per review).

---

## Trade-offs

**Cost:** Reviewer Sonnet now runs on every proposal regardless of eligibility. For workspaces with `level: manual` autonomy, this is pure overhead — the verdict is advisory and never binds. Estimated worst case: ~$0.05 per proposal × proposal frequency × user count. For alpha-1 cohort (≤10 personas, ≤50 proposals/day total) this is ≤$2.50/month. For broad rollout this needs revisiting; D1 includes a knob (`reviewer_advisory_only_threshold` in AUTONOMY.md) deferred to ADR-229 Phase 2 for tier-gating advisory reviews under cost pressure.

**Recursion safety:** D2's `propose_followup` is a recursion mechanism. Two safety properties:

1. **Bounded depth:** the follow-up's reviewer call is itself bounded by the same dispatch — there is no infinite recursion possible because the follow-up's `action_type` set is restricted to reversible/capital-neutral actions whose own reviews terminate quickly (no further `propose_followup` chains).
2. **Bounded breadth:** a Reviewer cannot emit multiple `propose_followup` entries from one verdict (the schema is singular). One defer = one follow-up max. This prevents "Reviewer asks for ten things, ten more reviewers fire."

**Chat-volume impact:** D3 + D4 mean every autonomous invocation surfaces in `/chat`. For a busy alpha-trader workspace with 6 recurring tasks firing 3-5x/day, this is ~25 narrative entries/day. The operator's chat becomes a true log of the workspace's life. UX implication: `/chat` rendering needs to render `weight: "routine"` entries differently from `material` (already supported per ADR-219; this ADR makes the differentiation load-bearing).

**Operator authoring touchpoints:** D2 directly addresses the audit's count of 10 authoring touchpoints. Most touchpoints exist because the Reviewer can't currently *ask for* what it needs (PRECEDENT.md carve-outs, AUTONOMY ceiling adjustments, additional `_operator_profile.md` declarations). Under D2 with `propose_followup`, the operator authors mandate + identity + initial autonomy + initial principles, and the Reviewer surfaces all subsequent gaps as proposals. ~6 of 10 touchpoints become Reviewer-initiated proposals over time.

---

## What this ADR does NOT do

- Does NOT collapse all autonomous activity into Reviewer-acting (rejected the most aggressive form of Claim 3). Production roles remain the actors for substrate accumulation; Reviewer is the actor for consequence-bearing writes. The split is by Purpose (Axiom 3), not by entity type.
- Does NOT delete tasks (ADR-138 holds). Tasks remain nameplate + pulse + contract per Axiom 9. What changes is attribution: Reviewer-initiated follow-up tasks are attributed `proposed_by: ai:reviewer-sonnet-v6` in their TASK.md.
- Does NOT introduce a `bootstrap` autonomy posture. The audit recommended one; this ADR makes it unnecessary because generative defer addresses the bootstrap paradox at the right altitude (the recursion mechanism, not a separate posture).
- Does NOT change the Sonnet model or persona. The Reviewer is the same persona, with the same principles + PRECEDENT + IDENTITY substrate — just with one more verdict shape.

---

## Phase 1 implementation (this commit)

1. `api/services/review_policy.py`: rename `is_eligible_for_auto_approve` → `should_auto_execute_verdict`. Add `verdict` parameter; return `(False, "verdict is reject — never executes")` for non-approve verdicts; preserve all existing logic for `approve`.
2. `api/services/review_proposal_dispatch.py`: invert `on_proposal_created`. AI Reviewer runs first; verdict-then-autonomy gate decides binding/advisory. Observe-only path retained ONLY for: domains without reviewable substrate (no `_performance.md`/`_operator_profile.md` ever) AND no Reviewer principles authored. Single fallback condition, not the default.
3. `api/agents/reviewer_agent.py`: tool schema gains optional `propose_followup` object. System prompt gains the D5 section. `REVIEWER_MODEL_IDENTITY` v5 → v6.
4. `api/services/review_proposal_dispatch.py::_run_ai_reviewer`: when verdict is `defer` AND `propose_followup` is present, dispatch as fresh `ProposeAction` via `handle_propose_action`. Restrict `action_type` to allow-list. Log refusal if outside allow-list.
5. `api/services/task_pipeline.py:2438`: gate widens from `final_status == "delivered"` to `final_status in ("delivered", "failed")`. `weight` derives from status.
6. `api/services/narrative.py::find_active_workspace_session`: D4 fallback — when None and writer is autonomous (system-class), create a fresh `chat_sessions` row with `metadata.session_origin = "narrative_autopromote"` and return its id.
7. `api/prompts/CHANGELOG.md`: entry for `2026.04.28.1` documenting v5 → v6 prompt change.
8. ADR-194 v2, ADR-217, ADR-219 get amended-by notes pointing to this ADR.

## Phase 2 (deferred)

- Cost-gated advisory mode for `level: manual` workspaces (skip Sonnet review when verdict will never bind, when token cost exceeds tier budget).
- Frontend rendering refinement: `weight: "routine"` and "material" visibly different in `/chat` (today they're stylistically identical).
- Reviewer-initiated `propose_followup` UI: cockpit shows the original deferred proposal AND the follow-up research task as a linked pair, so the operator can see "the Reviewer asked for X to evaluate Y."
- Allow-list expansion: if Phase 1 validates, consider adding `domain.observe_more` and `risk.tighten` as follow-up action_types (still capital-neutral, but more expressive for the Reviewer's narrowing-loop).

## Validation

The next track-universe + signal-evaluation cycle on alpha-trader-1 during US RTH should produce:

1. Tracker writes per-ticker context files (max_tokens fix from earlier today)
2. Signal-evaluation either fires a signal proposal (production case) OR doesn't (no signal triggered)
3. If a proposal fires: Reviewer runs (D1), returns `approve` (auto-executes if within AUTONOMY ceiling) or `defer + propose_followup` (research task gets dispatched, dispatched task fires next cycle, accumulated substrate makes future similar proposals approvable)
4. Every invocation in (1)-(3) lands a narrative entry in the workspace's chat session (D3 + D4)

The success metric is not "first paper trade lands" — that already happened today via Path B. The success metric is **the Reviewer asking for evidence and the system producing it**, which today's defer reasoning explicitly invited.

---

## What this validates from today's session

- **Path B + Path C empirical results** flow into D1: judgment ran (Path C Sonnet), produced reasoning that named the bootstrap paradox, and was correctly conservative. That conservatism is preserved; it is no longer terminal.
- **The 4 schema mismatches** validated the principle that operator-authored substrate must match runtime parser shape. This ADR doesn't fix the schema mismatches directly — that's the validator-script work scoped in the audit recommendations — but D2's `propose_followup` reduces the surface of operator pre-authorization needed (fewer schema files to author = fewer mismatches possible).
- **The 10 authoring touchpoints** reduce by ~6 under D2 over time. Cold-start is still cold; warm-start is shorter.
- **ADR-219's narrative-coverage promise** is finally enforced under D3 + D4. The "I don't see this in chat" symptom that triggered the stress-test discourse becomes structurally impossible.

This ADR is the rationalization of canon already written. ADR-216 said the Reviewer is the persona-bearing systemic Agent. ADR-217 said autonomy is operator-declared standing intent. ADR-219 said every invocation produces a narrative entry. ADR-194 v2 said `defer` is a valid verdict. This ADR puts them in the right *order* and adds the *recursion shape* (`propose_followup`) that lets the Reviewer's defer be productive instead of terminal. The architecture was right; the dispatch ordering and one prompt shape were wrong.
