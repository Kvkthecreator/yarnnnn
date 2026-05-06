# ADR-252: Reviewer as Primary Intelligence — Chat Routing Inversion

> **Status**: **Phase 1 Implemented** (2026-05-06 — intent classifier, Reviewer addressed mode, system_agent role, three-party narrative rendering, no-impersonation prompt clause)
> **Date**: 2026-05-06
> **Authors**: KVK, Claude
> **Supersedes**: ADR-249 D2 partial (System Agent posture sharpened further — executor/narrator, not co-reasoner, now structural not just prompt-layer)
> **Amends**: ADR-247 (three-party narrative model — `role='assistant'` becomes `role='system_agent'`; roles split more crisply); ADR-249 D7 (Mode 3 scoped here, not as a separate ADR); FOUNDATIONS Axiom 2 + Axiom 4 + Axiom 5 (Reviewer trigger gains addressed sub-shape; System Agent shifts toward deterministic end of Mechanism spectrum)
> **Dimensional classification**: **Identity** (Axiom 2) primary — restructures which identity handles which invocation class; **Mechanism** (Axiom 5) secondary — System Agent moves toward deterministic end of spectrum; **Trigger** (Axiom 4) tertiary — Reviewer gains addressed trigger sub-shape alongside its existing reactive + periodic

---

## Context

### The architectural gap this ADR resolves

Every prior ADR correctly named the Reviewer as the operator's judgment function (ADR-249 D3) and the System Agent as executor/narrator (ADR-249 D2). But the implementation left chat routing unchanged: every user message goes to the System Agent (Sonnet), which reasons, executes, and — critically — impersonates the Reviewer when the user asks a judgment question.

This produces three observable failures:

1. **Identity violation**: The System Agent composes Reviewer-style assessments in its own bubble. The operator cannot tell who is speaking — the executor or their judgment delegate. The narrative is one actor performing two roles.

2. **Quality failure**: The System Agent does not have the Reviewer's persona (`IDENTITY.md`), the Reviewer's framework (`principles.md`), or the Reviewer's accumulated calibration (`calibration.md`). Its "judgment" is improvised from workspace state. It is unaccountable — no decisions.md entry, no revision attribution, no calibration feedback loop.

3. **Cost misallocation**: Execution requests ("fire signal-evaluation") burn full Sonnet context to dispatch a mechanical operation. Judgment requests ("what do you think about holding NVDA?") get a less-qualified reasoner than the Reviewer would provide. Wrong model for wrong job in both directions.

### What the foundations say this should look like

**Axiom 2 (Identity)**: The Reviewer's distinctness is in Purpose + Trigger. Purpose: independent judgment on the operator's behalf. Trigger: currently reactive only. The operator's judgment-seeking messages are addressed invocations — a third trigger sub-shape the Reviewer should own.

**Axiom 4 (Trigger)**: Three sub-shapes — periodic, reactive, addressed. The Reviewer has periodic (reflection, ADR-248) and reactive (per-proposal, ADR-229). It is missing addressed. This ADR wires the third.

**Axiom 5 (Mechanism spectrum)**: The Reviewer belongs at the judgment end of the spectrum. The System Agent belongs at the deterministic end. Today both are LLM calls (Sonnet) at the same point on the spectrum. The correct trajectory: Reviewer moves toward richer judgment context (full substrate + conversation); System Agent moves toward deterministic dispatch (no LLM for execution requests).

**Derived Principle 11**: Substrate tightens, Mechanism loosens — gated by the Reviewer. "Loosening" means more Reviewer judgment, less procedural scaffolding. This ADR is that loosening applied to the chat surface.

---

## Decisions

### D1: Intent classifier gate — per-turn, Haiku, near-zero cost

Every user message passes through a lightweight intent classifier before routing. The classifier is a single Haiku call (~200 input tokens) that returns one of two classes:

| Class | Definition | Examples |
|---|---|---|
| `execution` | Imperative commands with no judgment content — the operator wants the system to do something mechanically | "Fire signal-evaluation", "Pause the recurrence", "Show me what happened", "Read my AUTONOMY.md" |
| `judgment` | Requests that invoke the operator's judgment character — opinion, assessment, strategy, principle application, configuration decisions with capital or behavioral consequences | "What do you think about holding NVDA?", "Is this trade consistent with my principles?", "Should I widen my ceiling?", "Review the signal results" |

**Gate implementation**: `api/services/intent_classifier.py` — `classify_intent(user_message: str, context_hint: str) -> Literal["execution", "judgment"]`. Haiku call with a 5-sentence prompt + 2-example few-shot. Cached for identical messages within a session. Falls back to `"judgment"` on any failure (safe default — Reviewer speaking when uncertain is never wrong).

**The classifier does not replace judgment**: it routes. The Reviewer always receives the full substrate regardless of what the classifier predicted. If the classifier mislabels a judgment question as execution, the System Agent's narration will be thin and the operator can rephrase — the cost is one cheap misrouted turn, not a missed verdict.

### D2: Judgment turns route to the Reviewer — addressed trigger, full substrate

When `classify_intent() == "judgment"`:

1. System Agent **does not respond** with prose. It calls `ProposeAction` or returns a brief execution narration only if a mechanical action was also requested alongside the judgment query.
2. `reviewer_agent.address_turn()` is invoked — a new third mode alongside `review_proposal()` (reactive) and `run_reflection()` (periodic).
3. The Reviewer reads:
   - `/workspace/review/IDENTITY.md` — who they are
   - `/workspace/review/principles.md` — their framework
   - `/workspace/context/_shared/PRECEDENT.md` — operator rulings on edge cases
   - `/workspace/context/_shared/MANDATE.md` — the operation's declared intent
   - `/workspace/context/{domain}/_performance.md` — relevant track record
   - `/workspace/context/{domain}/_operator_profile.md` + `_risk.md` — declared strategy + floors
   - Conversation window (last 5 turns) — what was just discussed
   - The user's message — what is being asked
4. The Reviewer responds in persona (Simons, Buffett, or operator-original) directly to the operator's question. Output shape: `return_addressed_assessment` tool — `response` (first-person persona voice), `implications` (optional: structured actions or changes the response implies), `confidence`.
5. `write_reviewer_message()` surfaces the response as `role='reviewer'` in the narrative.
6. If `implications` contains executable instructions (e.g., "propose IH-3 on NVDA"), the System Agent reads them and dispatches the corresponding primitives mechanically — no further LLM call.

**What `address_turn()` is NOT**:
- Not a proposal gate (no approve/reject/defer — those are for reactive proposals from production agents)
- Not a re-render of the conversation (no YARNNN-style "let me help you with that")
- Not a planning session (no "here's what we should do next" scaffolding)
- It is the Reviewer speaking on the operator's question, in their voice, from their declared framework

### D3: Execution turns route to the System Agent dispatcher — deterministic, thin or no LLM

When `classify_intent() == "execution"`:

The System Agent handles the turn. **For Phase 1**, this is unchanged from today — Sonnet handles execution with full context. **For Phase 2** (sequenced separately): execution turns use a structured pattern-match router before any LLM call. Common patterns:

| Pattern | Resolution |
|---|---|
| "Fire [recurrence-slug]" | `FireInvocation(slug=...)` — zero LLM |
| "Pause [recurrence-slug]" | `ManageRecurrence(action="pause", slug=...)` — zero LLM |
| "Show me [file-path]" | `ReadFile(path=...)` — zero LLM |
| "What happened since [time]" | compact index + loop events read — zero LLM |
| "Read/check [substrate]" | `ReadFile(...)` — zero LLM |
| Complex routing | Thin Sonnet call (stripped context — no substrate, just command + file index) |

Phase 2 is the progressive elimination of Sonnet from execution turns. The direction is set in Phase 1 via prompt posture; the deterministic router lands in Phase 2.

### D4: Narrative role split — `role='system_agent'` replaces `role='assistant'`

The current `role='assistant'` maps to `'system-bubble'` in `MessageDispatch.tsx` and is labeled `"system"` in the narrative. This is the right concept but the wrong implementation: `assistant` is a Claude API artifact, not an architectural identity.

**D4 changes**:

1. `session_messages.role` constraint widened: `'assistant'` remains valid (backwards-compat for existing rows) but new System Agent writes use `'system_agent'`. Migration 167 adds `'system_agent'` to the CHECK constraint.
2. `MessageDispatch.tsx`: new shape `'system-agent-bubble'` for `role='system_agent'`. The label renders as **"System Agent"** (not "system", not "YARNNN"). Visually distinct from the Reviewer card — muted background, left-aligned, brief narration style.
3. `resolveMessageShape()`: `r === 'system_agent' → 'system-agent-bubble'`.
4. `role='assistant'` continues to resolve to `'system-bubble'` for historical messages — no retroactive migration, no visual change for existing rows.
5. The Reviewer renders as today (`role='reviewer'` → `ReviewerCard` with persona name). The visual distinction is now fully three-party:
   - **Operator** (right-aligned, primary tint): user messages
   - **System Agent** (left-aligned, muted, brief): execution narration — "Fired signal-evaluation. Results written to trading domain."
   - **Reviewer** (full-width card, rose tint, persona name): judgment — "IH-3/NVDA is the closest setup. RSI depth met, but the reversal candle needs live session confirmation. Standing by for tomorrow's open."

**The operator can literally watch System Agent and Reviewer speak in the same scroll, clearly attributed.**

### D5: Compound turns — execution then judgment, same HTTP response

When the operator requests both ("fire signal-evaluation and tell me what Simons thinks about the results"):

1. Intent classifier → `judgment` (judgment intent subsumes execution when both present)
2. System Agent executes the mechanical portion first (`FireInvocation`) — results written to workspace
3. Reviewer reads fresh workspace state (results just written) + conversation + user message
4. Reviewer responds as Simons with the assessment
5. Two `session_messages` entries in the same turn: `role='system_agent'` (execution narration) + `role='reviewer'` (Simons' assessment)
6. Frontend renders both sequentially — System Agent bubble followed by Reviewer card in the same turn

**No double-Reviewer loop for operator-addressed turns**: when the operator addresses the Reviewer directly and the Reviewer outputs implications including a `ProposeAction`, the System Agent dispatches it with `source="reviewer_addressed"` on the `action_proposals` row. The reactive Reviewer dispatcher checks this flag and skips re-invocation — the Reviewer already judged, the proposal is pre-reviewed. The ProposalCard still shows in the Queue for AUTONOMY-gated approval if required.

### D6: Full autonomy — Reviewer-initiated invocations at declared cadence

At `autonomy: autonomous` (or `bounded_autonomous` within ceiling), the Reviewer does not passively wait for operator messages or production proposals. It operates at its declared cadence as a fully active principal:

**Cadence-based invocations** (`back-office-reviewer-reflection`, ADR-248 — already declared in `back-office.yaml`):
- Daily at 07:00 UTC: Reviewer reads `_performance.md` + `calibration.md` + `decisions.md`, assesses pattern drift, writes `reflections.md` entry, emits `role='reviewer'` narrative entry
- If drift detected → writes `paused_until` to `AUTONOMY.md` (circuit breaker)

**NEW: Reviewer-initiated action proposals** (D6, this ADR):
When autonomy is `autonomous` and the Reviewer's reflection produces a verdict of `generate_proposal` (new verdict type alongside existing `no_change` / `narrow` / `relax` / `character_note` / `pause_autonomy`):

1. Reflection produces a `generate_proposal` verdict with `action_type` + `inputs` + `rationale`
2. `reflection_writer.apply_reflection_writes()` calls `handle_propose_action()` with the Reviewer as proposer (`authored_by="reviewer:{occupant}"`)
3. `action_proposals` row created with `source="reviewer_periodic"` — marks this as Reviewer-initiated, not production-agent-sourced
4. **Auto-approve gate**: since the Reviewer both generated and would judge this proposal, `source="reviewer_periodic"` skips the reactive Reviewer pass (no self-judgment loop). AUTONOMY.md ceiling still gates auto-execution.
5. If within ceiling → `ExecuteProposal` fires automatically. Narrative entry: `role='reviewer'` — "Generated and executed: [action]. Rationale: [summary]."
6. If above ceiling → ProposalCard surfaces in Queue. Reviewer has already provided reasoning in the proposal's rationale field.

**This is the full autonomy loop**: Reviewer reflects → detects signal → proposes → executes (within ceiling) → outcome recorded → next reflection reads the outcome → loop closes.

**Cost of full autonomy cycle**: calibration (zero LLM, nightly) + reflection (Haiku, ~$0.002) + proposal generation (zero LLM, from reflection verdict) + execution (zero LLM, deterministic dispatch). Total: ~$0.002/day at full cadence. The Reviewer's autonomous operation is nearly free.

### D7: System Agent prompt posture — no Reviewer impersonation, structural not just directive

The System Agent prompt posture change from ADR-249 Layer 1 was prompt-layer only. D7 makes it structural:

1. System Agent prompt: new explicit clause — *"You do not hold judgment. You do not compose assessments of signals, positions, or principles. If the operator's question is judgment-seeking, your only response is to narrate what the system did and indicate the Reviewer will assess. Example: 'Signal-evaluation fired. Results written. Simons will assess.' Then stop."*

2. System Agent prompt: `role='assistant'` label in streaming header changed to `role='system_agent'` so the DB write uses the new role.

3. System Agent prompt: tool surface stripped for pure execution turns (Phase 2 prep) — `ProposeAction`, `ExecuteProposal`, `RejectProposal` removed from System Agent tool surface for `execution`-classified turns. System Agent cannot propose on execution turns — proposals only come from production agents (headless) or the Reviewer (D6).

### D8: Primitive registry split — Class A (System Agent) vs Class B (Reviewer-gated)

The 26 chat primitives are formally annotated with their intended caller class:

**Class A — System Agent execution primitives** (dispatched by System Agent on Reviewer instructions or direct execution commands):
`ReadFile`, `WriteFile`, `ListFiles`, `SearchFiles`, `FireInvocation`, `ManageRecurrence`, `LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity`, `GetSystemState`, `ListRevisions`, `ReadRevision`, `DiffRevisions`, `WebSearch`, `ListIntegrations`, `InferContext`, `InferWorkspace`, `ManageDomains`, `ManageAgent`, `RepurposeOutput`, `RuntimeDispatch`, `Clarify`

**Class B — Judgment primitives** (only invokable by the Reviewer or in response to explicit operator binding):
`ProposeAction`, `ExecuteProposal`, `RejectProposal`

`Clarify` is Class A but Reviewer can also issue it — same primitive, the Reviewer includes a clarification request in its `implications` field and the System Agent surfaces it via `Clarify`.

**Registry annotation**: `CHAT_PRIMITIVES` entries gain a `caller_class: "system_agent" | "judgment" | "both"` field. No handler changes — handlers don't care who calls them. This annotation drives the Phase 2 context stripping (judgment-class tools removed from System Agent's tool surface on execution turns).

---

## Implementation plan

### Phase 1 — Intent classifier + Reviewer addressed mode (this ADR, immediate)

**Files:**
- `api/services/intent_classifier.py` (NEW) — `classify_intent()` Haiku gate
- `api/agents/reviewer_agent.py` — `address_turn()` third mode + `return_addressed_assessment` tool + `generate_proposal` reflection verdict type
- `api/routes/chat.py` — classifier call + routing fork + compound turn handling
- `supabase/migrations/167_system_agent_role.sql` — add `'system_agent'` to `session_messages.role` CHECK
- `api/services/narrative.py` — write System Agent turns as `role='system_agent'`
- `web/components/tp/MessageDispatch.tsx` — `'system-agent-bubble'` shape + `resolveMessageShape` update
- `web/types/desk.ts` — add `'system_agent'` to role union
- `api/agents/prompts/base.py` + `prompts/chat/workspace.py` — no-impersonation structural clause
- `api/prompts/CHANGELOG.md` — prompt change entry
- `docs/adr/ADR-252-reviewer-primary-intelligence.md` — this document → Implemented

**Test gate** `api/test_adr252_reviewer_primary.py`:
1. `classify_intent()` returns `"judgment"` for known judgment phrases
2. `classify_intent()` returns `"execution"` for known execution phrases
3. `reviewer_agent.address_turn()` exists and accepts `(client, user_id, user_message, conversation_window)` signature
4. `session_messages.role` CHECK includes `'system_agent'`
5. `resolveMessageShape()` maps `role='system_agent'` to `'system-agent-bubble'`
6. `MessageDispatch.tsx` renders `'system-agent-bubble'` with "System Agent" label (not "system", not "YARNNN")
7. `reviewer_agent` reflection verdict schema includes `generate_proposal` type
8. `CHAT_PRIMITIVES` entries have `caller_class` annotation field

### Phase 2 — Deterministic execution router + System Agent context strip

**Files:**
- `api/services/execution_router.py` (NEW) — pattern-match router for common execution commands
- `api/routes/chat.py` — router-first dispatch before any LLM call on execution turns
- `api/services/primitives/registry.py` — `caller_class` annotation on all entries; stripped tool surface for execution turns

### Phase 3 — Full autonomy Reviewer-initiated proposals + narrative hardening

**Files:**
- `api/services/reflection_writer.py` — `generate_proposal` verdict handler
- `api/services/review_proposal_dispatch.py` — `source` flag skip logic for `reviewer_periodic` + `reviewer_addressed`
- `api/services/primitives/propose_action.py` — `source` field on `action_proposals`
- `supabase/migrations/168_action_proposals_source.sql` — add `source` column
- `web/components/tp/MessageDispatch.tsx` — full visual polish for three-party narrative; `role='assistant'` historical rows fade to muted-er style; `role='system_agent'` narration uses brief prose style

---

## What this does NOT do

- Does not remove the System Agent's LLM capability entirely (Phase 2 is progressive; complex execution still needs thin LLM)
- Does not give the Reviewer write primitives directly (it outputs `implications`; System Agent executes — independence preserved)
- Does not change the headless production agent pipeline (agent task execution is unchanged)
- Does not change the reactive Reviewer path (ProposeAction → review_proposal_dispatch → reviewer_agent.review_proposal remains identical)
- Does not retroactively change `role='assistant'` historical rows

---

## Token economics

| Turn type | Current | Phase 1 target | Phase 2 target |
|---|---|---|---|
| Execution ("fire X", "pause Y") | Sonnet ~$0.048 | Sonnet ~$0.048 (unchanged Phase 1) | Deterministic ~$0.0003 |
| Judgment ("what do you think") | Sonnet ~$0.048 (wrong reasoner) | Haiku $0.0003 + Reviewer Sonnet ~$0.06 | Same |
| Narration ("what happened") | Sonnet ~$0.036 | Haiku $0.0003 + deterministic | Deterministic ~$0.0003 |
| Compound (exec + judgment) | Sonnet ~$0.048 | Haiku $0.0003 + Reviewer Sonnet ~$0.07 | Same |
| Autonomous Reviewer cycle | Reflection Haiku ~$0.002/day | + Proposal generation $0 | Same |

**Phase 1 cost**: judgment turns ~25% more expensive (Haiku + Reviewer Sonnet vs single Sonnet), but correct reasoner. Execution + narration turns identical cost. Net roughly flat.

**Phase 2 cost**: execution + narration turns drop ~160×. Overall session cost drops ~45%.

**Phase 3 cost**: near-zero for autonomous Reviewer cycles.

---

## Relationship to existing ADRs

| ADR | Relationship |
|---|---|
| ADR-247 | Three-party narrative ratified — this ADR makes it structurally enforced, not just named. `role='system_agent'` replaces `role='assistant'` for new writes. |
| ADR-249 | D2 (executor/narrator posture) made structural. D7 (Mode 3) implemented here. |
| ADR-248 | Periodic Reviewer pulse preserved. D6 adds `generate_proposal` verdict to reflection output — extends ADR-248, not replaces. |
| ADR-229 | Reactive Reviewer path (judgment-first dispatch) preserved unchanged. |
| ADR-194 v2 | Reviewer substrate unchanged. `address_turn()` is a third invocation mode, same seat, same substrate. |
| ADR-245 | Three-layer content rendering — `system-agent-bubble` is a new L3 shape for the `system_agent` content class. |
| ADR-231 | Recurrence execution (FireInvocation, ManageRecurrence) handled by System Agent execution class — unchanged in handler, classified in D8. |
| FOUNDATIONS Axiom 4 | Reviewer now has all three trigger sub-shapes: reactive (review_proposal), periodic (run_reflection), addressed (address_turn). Complete. |
