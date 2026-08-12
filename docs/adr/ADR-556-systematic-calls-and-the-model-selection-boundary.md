# ADR-556 — Systematic calls and the model-selection boundary

> **Status**: **Accepted + Implemented** (2026-08-12, operator-ratified). Phase 1 (the systematic track) ships in this commit: the `SYSTEM_CALLS` registry, nine literals migrated, two never-executed calls fixed, one ungated passthrough closed, gate `api/test_adr556_system_calls.py` 75/75 with four falsifiers verified red. Phase 2 (the user-facing track) is **deliberately not decided here** — §7.
> **Date**: 2026-08-12
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5). Two populations of LLM call were being reasoned about as one; this separates them and gives the machinery population a declared home.

**Amends**:
- [ADR-402](ADR-402-model-routing-as-kernel-data.md) — extends its "routing is kernel DATA" ruling from the steward to the machinery. ADR-402's table stays **separate and untouched** (§4): one table per routing key, and the steward's key is the trigger shape, not the call type.
- [ADR-463](ADR-463-capability-not-vendor-the-model-agnostic-carve.md) **D1** — the provider-prefix carve is applied to the nine machinery literals it did not reach. "A dial whose every position is the same vendor is not a dial" was true of them too.

**Preserves** (load-bearing, untouched): [ADR-460](ADR-460-agents-one-concept-independent-facts-one-gate.md) (the member picks WHO, not which engine — this ADR *defends* it by keeping machinery off the picker), [ADR-467](ADR-467-app-residency-and-the-cast.md) D2 (chat's roster door has no default), [ADR-463](ADR-463-capability-not-vendor-the-model-agnostic-carve.md) D3 (Freddie is Anthropic-direct for prompt caching), [ADR-396](ADR-396-the-pricing-model-type-b-subscription-over-the-metered-balance.md) (one meter, one ledger), [ADR-439](ADR-439-byok-key-scope-and-the-enterprise-tier-gate.md) §4 (an unpriced model never routes).

---

## 1. Context — the audit that surfaced the wrong cut first

An audit was asked for on "the chat surface and our LLM calling strategy", opening from the premise that the chat surface has *pre-scaffolded agents* where *model optionality* is wanted, and that apps (radar, docs, studio) may have a model wrongly bolted on.

The first pass answered by inventory: grep for anything shaped like a model id, find nine hardcoded literals plus two tables, and propose unifying them. **That was the wrong directional audit, and the operator named why**: a search-shaped method lets the *set of strings that look like model ids* define the problem, which flattens two populations that are not the same kind of fact.

The operator's cut:

> "systematic llm calls and user facing features like chats, lanes, and APPs related where routing and optionality is one of the key features (while considering defaults and costing, alike) BUT systematic is more about scalability, stability, and cost implications per the type of llm calls"

That is an Axiom-0 diagnosis. The proposed "unify the nine literals into one table" would have put `web_search`'s continuation engine on the same footing as a member choosing Critic — i.e. rebuilt the spec sheet [ADR-460](ADR-460-agents-one-concept-independent-facts-one-gate.md) deleted, from the other direction.

## 2. D1 — Two populations, and the boundary between them

| | **Systematic** | **User-facing** |
|---|---|---|
| Who picks | the SYSTEM | the MEMBER |
| Governed by | cost · stability · scalability, **per call type** | choice · defaults · visible cost |
| Optionality is | a liability | the feature |
| Home | **`services/system_calls.py`** (this ADR) | `lane_runner.LANE_MODELS` + `agents_registry.KERNEL_AGENTS` |

A third population is named so it is not mistaken for a gap: **the steward** (Freddie), whose engine lives in `services/model_selection.py` keyed by trigger shape, Anthropic-direct by ADR-463 D3 because `model_router.py` carries neither `cache_control: ephemeral` nor beta `context_management`. Routing it would silently drop prompt caching on the system's most frequent LLM call.

**The boundary is the decision.** A member must never see a machinery engine on a picker; a machinery call must never take its engine from a member's preference.

## 3. D2 — The unit of declaration is the CALL TYPE, not the tier

Both were viable and the operator delegated the choice. **Call type wins**, for three reasons:

1. **The reasoning already exists and had no home.** Every literal carried its judgment as prose above the constant — *"Haiku is sufficient for fact extraction"*, *"reuses the specialist bounded-loop model"*. Keying on tier throws that away; keying on call type gives it a `reason` field.
2. **A tier is a value, not an identity.** You cannot attribute a cost to "cheap". You can attribute one to `fact_extraction`. `execution_events.model` records what ran; the call type is what was missing to answer *what did extraction cost us this month?*
3. **It is the ratified registry shape, a fourth time** — `LANE_MODELS` (ADR-411 D5), `DERIVE_RECIPES` (ADR-450), `KERNEL_AGENTS` (ADR-460 D4). This is hardening, not a new mechanism.

Tier rides along as an attribute (`cheap` | `standard`) — the cost dial, without pretending to be an identity.

Nine rows ship: `wake_triage`, `fact_extraction`, `session_summary`, `web_search_continuation`, `repurpose`, `identity_inference`, `recurrence_prompt_inference`, `harvest`, `specialist_dispatch`.

## 4. D3 — What the registry does NOT absorb

- **The steward's table stays separate** (gate-asserted). One table per routing key.
- **`LANE_MODELS` stays the member's whitelist.** Sharing an engine is fine; sharing a *table* would leak machinery onto the picker.
- **Embeddings stay out.** `services/embeddings.py` is a bare OpenAI dependency with no ledger write and no provider-blindness. Real, and a *different* defect (ADR-396-shaped, not routing-shaped). Folding it in here would smuggle an unmetered call into a table whose gate asserts every row is priced. Named, deferred, not silently absorbed.
- **The `images` raster driver stays out.** `services/images/generate.py` calls Gemini REST directly, priced by `IMAGES_GENERATION_COST_USD` — a rented generation engine (ADR-417), not a routed completion.

## 5. The three defects the migration surfaced

These are the argument for the registry: **the constants were in the places nobody read.**

**F1 — the wake funnel's cheap tier never ran once.** `wake_evaluation.tier_2_decision` called `chat_completion` with a `user_id`/`caller` metering API **that never existed on any wrapper**, omitted the required `system` arg, and unpacked two values from a `-> str`. Born broken at `37426c5` (ADR-296 v2). Every invocation raised `TypeError` into a bare `except` and returned `("escalate", "tier_2_exception_fail_open")`. **So every idle-tick wake that ADR-296 built the funnel to triage away escalated to a full Sonnet wake at `max_rounds=20`.** The funnel's entire cost argument was inert for its whole life. Proven by AST diff against the real signature, by executing the old call (`TypeError: got an unexpected keyword argument 'user_id'`), and by `git log -L`.

**F2 — a registered primitive with the same shape.** `repurpose` read `response.text` off a `-> str`. `RepurposeOutput` is live in the registry. Same class: a call nobody executed.

**F3 — a user-facing input reaching a systematic path.** `routes/images.py::ComposeRequest.model` let a client name any engine straight into `route_completion` with neither the `LANE_MODELS` membership check nor the ADR-439 §4 billing gate — the only routed path missing that guard, so an unpriced model priced silently at the Sonnet default. **This was D1's boundary being crossed in code**, which is why it is fixed here rather than filed as a separate bug. The override is removed, not gated: layer planning is machinery, and machinery does not take an engine from a caller.

**Why every existing gate was green through all three.** F1 and F2 are calls whose *signature* nobody executed — Python resolves free names at call time, so import gates, type checks, and the whole battery pass. This is the recorded `feedback_gate_tests_helper_not_its_callers` shape. Hence the gate **executes** the tier-2 path with a stubbed SDK and **AST-checks every wrapper call against its real signature**, rather than grepping.

## 6. The env-var collision

`MEMORY_EXTRACTION_MODEL` bound **two unrelated call types** — fact extraction and session summaries. Moving one moved the other, silently. Two call types, two rows, two dials (`YARNNN_SYSCALL_FACT_EXTRACTION` / `YARNNN_SYSCALL_SESSION_SUMMARY`); gate-asserted independent.

## 7. What this ADR deliberately does NOT decide

**The user-facing track is untouched and still open.** The audit's original question — *can a member override the engine behind a named agent, and should there be a workspace-level default?* — is a product decision that would amend [ADR-467](ADR-467-app-residency-and-the-cast.md) D2 ("the faces picker at the chat door is the correct architecture *as shipped*, not a gap awaiting a default"). It is not hardening, so it is not here.

Three facts that decision should carry, established by this audit:

1. **A member-level engine override already exists** — `AGENT_MANIFEST_KEYS` includes `model`, so a member's `_agent.yaml` can already pin an engine over a kernel capability. The capability is built; only its UI affordance is missing.
2. **The engine is already legible** — `Critic · GPT-5` renders on conversation headers, roster rows, and agent cards. The gap is override, not visibility.
3. **A workspace default would reach less than it appears to.** It could not include the steward (prompt caching), radar (`_radar.yaml` deliberately refuses a model key), embeddings, or the images raster driver. Its true reach is lane turns — which is exactly what the per-agent `model` key already reaches.

**Gating unknown, unresolved**: `MODEL_ROUTER_ENABLED` is documented OFF in production (ADR-439 status). If it is off, lanes, agents, Studio's authoring pane, and radar's derive are all dark, and the user-facing track's ranked problem is a rollout, not an architecture. This must be checked on the Render dashboard before Phase 2 is scoped.

## 8. Consequences

**Good.** The funnel's cheap tier actually runs (a real, ongoing cost reduction — every triaged idle tick is a full Sonnet wake avoided). A registered primitive stops raising. One metering hole closed. Nine literals get one home, provider-prefixed so the table can *name* an engine it does not yet call. The judgment behind each engine choice is recorded rather than lost.

**Cost.** One new kernel module and one gate. A new machinery call is now a row plus a rate row, not a local constant — deliberate friction.

**Behavioral change, flagged.** Fixing F1 changes production behavior: wakes that currently all escalate will start being triaged to `wait`/`observe`. That is the ADR-296 design finally operating, but it is not a no-op refactor, and the first days of telemetry (`funnel_decision` on `execution_events`) should be watched.

---

**One line**: systematic calls are machinery keyed by call type with one declared home, user-facing calls are the member's choice keyed by colleague, the steward keeps its own table for prompt caching, and the boundary between them is enforced — because collapsing them once let a member's input reach a routing path ungated, and let the wake funnel's cheap tier fail open into a Sonnet wake for its entire life.
