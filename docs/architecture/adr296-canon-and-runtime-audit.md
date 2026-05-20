# ADR-296 Canon + Runtime Audit — Where We Stand Against the Continuous Judgment Cycle Thesis

> **Status**: Hat-A audit, system canon work product
> **Date**: 2026-05-20
> **Authors**: KVK, Claude
> **Scope**: Audit current canon + current runtime against the [ADR-296 Continuous Judgment Cycle thesis](../adr/ADR-296-continuous-judgment-cycle.md). Pure first-principled comparison. No implementation, no canon edits, no ADR revisions in this work product. Output is the gap map the next discourse round reasons against.
> **Companion**: [ADR-296 (Proposed, pure thesis)](../adr/ADR-296-continuous-judgment-cycle.md). This audit is the cross-canon + cross-runtime reading that ADR-296's "what this ADR does not yet say" section deferred.

---

## How to read this audit

ADR-296 made seven thesis claims (T1–T7). For each claim, this audit answers three questions:

1. **What does current canon say** against that claim — alignment, conflict, partial, or absent?
2. **What does current runtime do** against that claim — alignment, conflict, partial, or absent?
3. **Where is the load-bearing gap** between thesis and the canon-and-runtime composition?

I have not pre-resolved any of the conflicts. The audit names them; the next discourse round decides whether each conflict (a) refines the thesis, (b) refines canon, (c) refines runtime, or (d) is a false-alarm and resolves by re-reading.

A 4-category color is used per row:

- **A** Aligned — canon-or-runtime already expresses the thesis, possibly under different vocabulary.
- **P** Partial — canon-or-runtime has the ingredients but does not compose them into the thesis shape.
- **C** Conflict — canon-or-runtime takes a structurally different position from the thesis.
- **U** Underspecified — neither alignment nor conflict; the surface simply does not address the question.

---

## T1 — The Reviewer is a continuous self-pacing judgment cycle, not a trigger-responsive entity

**Thesis target shape**: One continuous loop, always-next-cycle-scheduled, cycles terminate but the loop does not. The Reviewer *is* the system's continuous judgment surface.

### Canon position

| Source | Position | Color |
|---|---|---|
| [FOUNDATIONS Axiom 2 §"The Reviewer seat's distinctness is in Purpose + Trigger, not Identity"](FOUNDATIONS.md) | "The Reviewer seat is... Purpose (independent judgment on proposed writes) and its Trigger (**reactive to proposal creation**)" — explicitly defines Reviewer as *trigger-responsive on proposal arrival*. | **C** |
| [FOUNDATIONS Axiom 4 §"Two Sub-Shapes of Invocation"](FOUNDATIONS.md) | "Trigger is what **begins** a Reviewer session" — explicitly trigger-driven session-start framing. | **C** |
| [FOUNDATIONS Axiom 2 §"The operator is one principal with two runtime embodiments"](FOUNDATIONS.md) | "Operator-as-Reviewer — the personified AI agent that runs the Loop in the human's absence. **Acts continuously while the human sleeps**." — alignment-direction prose but framed as "the Loop" not "a continuous cycle." | **P** |
| [ADR-260 D1 "real-time + synchronous"](../adr/ADR-260-real-time-reviewer-loop.md) | "A Reviewer **session** is one continuous tool-use loop. The Reviewer wakes, reads, decides... until it concludes the work and calls `ReturnVerdict` to close the session." Session is bounded; "the loop" in canon refers to *within a session*, not across sessions. | **C** |
| [ADR-260 D2 "Three triggers, not four"](../adr/ADR-260-real-time-reviewer-loop.md) | "A Reviewer **session** begins for one of three reasons. These are the only three trigger shapes" — three explicit session-start triggers (later collapsed to two by ADR-263). | **C** |
| [GLOSSARY "Reviewer"](GLOSSARY.md) | "distinguished by its Purpose + Trigger cell — independent judgment (Purpose) on proposed-write events (reactive Trigger)" — same trigger-responsive framing. | **C** |

### Runtime position

| Surface | Position | Color |
|---|---|---|
| [`reviewer_agent.py::invoke_reviewer`](../../api/agents/reviewer_agent.py) | Function signature `invoke_reviewer(client, user_id, *, trigger, context, invocation_id)` — explicitly trigger-parameterized entry; called once per "session" and returns `ReviewerOutput | None`. No "next cycle" return value. | **C** |
| `invoke_reviewer` terminus | Function returns at `ReturnVerdict`. No post-terminus continuation hook. The function ends; control returns to caller (`invocation_dispatcher.dispatch` or `routes/feed.py`). | **C** |
| [`invocation_dispatcher.dispatch`](../../api/services/invocation_dispatcher.py) | Each `dispatch()` call is one-shot: claim due row → invoke Reviewer → record execution_events → return. No loop construct *across* dispatches. | **C** |
| [`unified_scheduler.dispatch_due_invocations`](../../api/jobs/unified_scheduler.py) | "for each recurrence in `_recurrences.yaml` that is due and not paused: dispatch" — exactly the trigger-driven polling pseudocode ADR-261 D3 specified. | **C** |

### Verdict on T1

**Canon position is C (Conflict).** Every governing ADR in the ADR-256/260/261/263/274/275/276 lineage frames the Reviewer as a trigger-responsive session-based entity. The "Operator-as-Reviewer acts continuously while the human sleeps" prose in FOUNDATIONS Axiom 2 hardening is aspirational about the *operator-axis* effect (continuous standing intent applied) but does *not* commit to a continuous *runtime cycle* — what continues is the operator's standing intent encoded in substrate, not a running Reviewer process.

**Runtime position is C (Conflict).** The Reviewer is a Python function called on-demand by trigger sources. Between cycles, no Reviewer state runs; only substrate persists.

**Load-bearing gap**: The thesis (T1) says the loop is the architecture. Current canon + runtime say *sessions* are the architecture; *triggers* start sessions; *substrate* connects sessions across time. The thesis claim that "the loop is always running in the sense that there is always a next cycle scheduled" has **no realization in current canon or runtime** — there is no architectural mechanism that schedules a next cycle from a previous cycle's terminus.

This is the largest single conflict the audit surfaces. Every other gap composes downstream of it.

---

## T2 — Worldview unifies all input. Trigger source is not a Reviewer-facing concept.

**Thesis target shape**: The Reviewer reads one thing each cycle — the current worldview (substrate + delta + operating context). Trigger source dissolves as Reviewer-facing concept.

### Canon position

| Source | Position | Color |
|---|---|---|
| [FOUNDATIONS Axiom 4 §"One execution shape under Reactive trigger; mode encodes wake intent"](FOUNDATIONS.md) | "the recurrence carries one shape `{slug, schedule, mode, prompt}`" — recurrence has the prompt; the trigger-axis sub-shape (reactive vs addressed) decides who routes to whom. Trigger persists as kernel concept; the prompt-source is per-trigger. | **P** |
| [ADR-260 D2 "Trigger names exist in code only as context-shape selectors for the user-message envelope"](../adr/ADR-260-real-time-reviewer-loop.md) | "There is no per-trigger system prompt branch beyond pre-loaded substrate selection." This is alignment-direction. Canon explicitly removes trigger from the Reviewer's user-facing surface — but the trigger value still exists as a function parameter and selects what loads into the envelope. | **A** (partial — see below) |
| [ADR-263 D2 "scheduled collapses into reactive"](../adr/ADR-263-recurrence-mode-mechanical-vs-judgment.md) | Trigger taxonomy already collapsed from three to two values. Canon has already taken steps toward trigger-source dissolution at the Reviewer-facing layer. | **A** |
| [ADR-276 envelope pre-load](../adr/ADR-276-reactive-trigger-envelope-governance-preload.md) | Reactive + addressed envelope shapes converge — both pre-load the same 9-file governance envelope via `load_reviewer_governance_envelope`. The trigger-shape divergence shrinks. | **A** |

### Runtime position

| Surface | Position | Color |
|---|---|---|
| [`reviewer_agent.py::_build_user_message`](../../api/agents/reviewer_agent.py) | Persona, principles, PRECEDENT, MANDATE, AUTONOMY, preferences, occupant, standing_intent, operator_profile, risk, ground-truth, operating-context — all pre-loaded into one user message. Trigger differentiates which *additional* slots load (proposal-card for proposal-arrival; recurrence-prompt for recurrence-fire). | **A** (partial) |
| `invoke_reviewer(trigger=...)` | Trigger remains a parameter on the Reviewer's entry point. It selects (a) which slots load, (b) model (Sonnet vs Haiku), (c) round bound (3 vs 12), (d) the trigger-specific framing block at the bottom of the user message. | **P** |
| [`reviewer_envelope.py::load_reviewer_governance_envelope`](../../api/services/reviewer_envelope.py) | Builds the universal envelope (8 universal paths + program-shaped paths via bundle MANIFEST `substrate_abi`) without referencing trigger source. **This is the worldview-read primitive.** | **A** |
| Worldview-delta surface | `standing_intent.md` ("What you were watching for last cycle") is pre-loaded — the previous-cycle anchor exists. But there is no explicit "what changed in substrate since my last cycle" computation; the Reviewer must infer delta from prior `standing_intent.md` vs current substrate state. | **P** |

### Verdict on T2

**Canon and runtime are P (Partial).** The worldview-unification work is already mostly done — `load_reviewer_governance_envelope` is exactly the kernel mechanism the thesis names. The pre-loaded envelope has rich substrate, operating context, persona, principles, standing intent. The Reviewer's user-message is genuinely "read the worldview" in shape.

**But trigger source has not fully dissolved at the Reviewer-facing layer.** Three residuals:
1. `trigger` is still a parameter that selects model + rounds + trigger-specific framing.
2. The user message has a trigger-shaped section at the bottom (proposal-arrival framing vs recurrence-fire framing).
3. The runtime still uses trigger for telemetry (`execution_events.trigger_type` column).

**Load-bearing gap**: The thesis says the Reviewer doesn't reason about trigger source. The runtime largely doesn't either at the prompt-content layer — *except* for the trigger-framing block at the bottom of the user message. To fully realize T2, that framing block dissolves into "here is the worldview; judge."

**Worldview-delta surface is not explicit.** ADR-296 names "Worldview deltas — what changed since my last cycle" as a target. Today the substrate ingredients exist (standing_intent.md from previous cycle, current substrate state, ADR-209 revision chain) but no helper composes them into a delta block in the envelope. The Reviewer is asked to compute the delta in prompt against substrate. This may or may not be sufficient — open question for the next discourse round.

---

## T3 — Cadence is Reviewer-authored at end-of-cycle

**Thesis target shape**: Every cycle ends with the Reviewer authoring the next cycle's scheduled time. Self-pacing. External events nudge cadence by writing to worldview.

### Canon position

| Source | Position | Color |
|---|---|---|
| [FOUNDATIONS Axiom 4 §"Trigger authoring is an Identity-layer responsibility"](FOUNDATIONS.md) | "Standing intent implies Trigger-authoring authority." The Reviewer authors its own cadence per Derived Principle 18. | **A** |
| [ADR-274 D1 + D3 "Schedule + persona-frame cadence-authoring"](../adr/ADR-274-reviewer-cadence-self-awareness.md) | Reviewer can call `Schedule(action="create|update|pause|resume|archive")` mid-loop to author its own future wake-ups. Persona frame instructs cadence-authoring discipline. | **A** |
| [ADR-275 D5 "Reviewer authors cadence from preferences + judgment"](../adr/ADR-275-introspection-cadence-reviewer-authored.md) | "Every wake, the Reviewer... authors new cadences for active preferences not yet honored. Also authors its own introspection cadence from first-principled judgment." | **A** |
| [ADR-260 D5 "Reviewer's mid-loop authority is the `Schedule` primitive"](../adr/ADR-260-real-time-reviewer-loop.md) | "There is no separate concern: a recurrence is a Reviewer-scheduled future wake-up; scheduling one is an ordinary action the Reviewer takes during its loop." | **A** |
| Cycle-terminus contract | **Absent.** No canon names "the Reviewer MUST schedule its next cycle before terminating." Reviewer self-scheduling is authorized capability, not cycle-terminus obligation. | **U** |

### Runtime position

| Surface | Position | Color |
|---|---|---|
| `Schedule` primitive in REVIEWER_PRIMITIVES | Implemented. Reviewer can author recurrences mid-loop. | **A** |
| `_PERSONA_FRAME` cadence-authoring section | Implemented per ADR-274 D3. Reviewer is told it has the authority. | **A** |
| `_preferences.yaml` read at every wake | Implemented. Reviewer perceives operator's deliverable cadence preferences. | **A** |
| Self-scheduling at cycle terminus | **Not enforced.** Reviewer can call Schedule mid-loop; nothing in `invoke_reviewer`'s terminus requires it to author a next-cycle wake before `ReturnVerdict`. | **C** |
| External-event cadence-pull-forward | **Absent.** When operator addresses the feed, the addressed handler invokes Reviewer immediately — that's the right shape. But when substrate changes (a draft transitions state, a position fills) there is no kernel mechanism that re-schedules the Reviewer's "next cycle." The Reviewer's next cycle is whatever cron fires next. | **C** |

### Verdict on T3

**Canon is A on Reviewer's *authority* to self-schedule (ADR-274 + ADR-275) but U on cycle-terminus *obligation*.** The Reviewer can author cadence; the Reviewer is not *required* to do so at the end of every cycle, and there is no canonical statement that the cycle's *next instance* is the responsibility of the cycle that just ran.

**Runtime is partially A but C on the cycle-terminus self-scheduling commitment.** Authority is wired (Schedule in REVIEWER_PRIMITIVES, persona frame guidance, `_preferences.yaml` pre-load). The shape "Reviewer ends cycle by scheduling next cycle" is not architecturally enforced.

**Load-bearing gap**: The thesis (T3) makes self-scheduling *load-bearing* — without it the loop dies. Current canon + runtime make it *optional*. The Reviewer COULD schedule its next cycle, but most cycles today don't — they `ReturnVerdict` and terminate, and the *next* Reviewer wake is determined by cron + bundle-declared recurrences, not by the Reviewer's prior-cycle judgment.

Additionally, the thesis names "external events write to worldview; cadence pulls forward via kernel mechanism detecting worldview-change against Reviewer-authored interest hint." That mechanism does not exist. External substrate-change does not pull cadence forward.

---

## T4 — The Reviewer's actions are worldview-writes, back-edge actions, and cadence-authoring. Nothing else.

**Thesis target shape**: Three action shapes. No "invoke this unit of work" primitive. Stale worldview → next cycle scheduled after worldview-maintainer fires, not direct invocation.

### Canon position

| Source | Position | Color |
|---|---|---|
| [ADR-261 D4 "Schedule primitive"](../adr/ADR-261-recurrences-as-prompts.md) | `Schedule` is in `REVIEWER_PRIMITIVES`. Covers cadence-authoring. | **A** |
| [ADR-193 `ProposeAction`](../adr/ADR-193-action-proposals.md) | Back-edge primitive. Narrow, value-moving, AUTONOMY-gated. | **A** |
| [`WriteFile` in REVIEWER_PRIMITIVES](../../api/services/primitives/workspace.py) | Worldview-writes (substrate). | **A** |
| [`FireInvocation` in REVIEWER_PRIMITIVES](../../api/services/primitives/fire_invocation.py) | **Exists as a Reviewer-facing primitive.** ADR-261 D5 "Reviewer's mid-loop authority is the `Schedule` primitive" framing extended in practice to include `FireInvocation` for "run this recurrence now." | **C** |
| [Reviewer principles.md alpha-trader "Commission substrate via FireInvocation when upstream substrate is missing"](../../docs/programs/alpha-trader/reference-workspace/review/principles.md) | Reviewer is canonized as using `FireInvocation` to commission stale substrate. | **C** |
| `DispatchSpecialist` primitive (ADR-261 D7) | Reviewer can dispatch specialist sub-LLM-calls inline. Narrowed by ADR-272 to designer-only. | **P** (this is a different category from the thesis's three shapes — it's a sub-judgment dispatch, not a worldview-write/back-edge/cadence-author) |

### Runtime position

| Surface | Position | Color |
|---|---|---|
| `REVIEWER_PRIMITIVES` set in [`api/services/primitives/registry.py`](../../api/services/primitives/registry.py) | 16-tool curated subset includes `FireInvocation`, `Schedule`, `WriteFile`, `ProposeAction`, `DispatchSpecialist`, `Clarify`, `ReturnVerdict`, plus reads + revision-chain primitives. | **C** for `FireInvocation`'s presence; **A** for the others. |
| `FireInvocation` in production use | 2 production fires in the system's history per the prior session's audit; 13 prose mentions across bundles + Reviewer prompts. Mostly aspirational. | **C** (mechanism is wired; usage suggests the mechanism's existence is causing bundle-author confusion) |

### Verdict on T4

**Canon and runtime are C on the FireInvocation question.** The thesis (T4) explicitly says "There is no Reviewer-facing primitive for 'fire this unit of work.'" Current canon (ADR-261) put FireInvocation in `REVIEWER_PRIMITIVES`; current runtime exposes it; current alpha-trader principles.md teaches the Reviewer to use it for commissioning stale substrate.

The other two thesis shapes (worldview-writes + back-edge actions + cadence-authoring) are all canonical and implemented.

**DispatchSpecialist sits in a fourth category the thesis didn't name.** Specialist dispatch is sub-judgment-cycle inside the same Reviewer cycle (Claude Code sub-agent pattern). It's not a back-edge external action (no external-world effect), not a worldview-write (the specialist writes substrate, not the Reviewer directly), not a cadence-authoring. It's "delegate a focused sub-cycle." Thesis is silent on this; runtime treats it as a Reviewer-callable primitive. Either the thesis needs to name a fourth shape (sub-delegation) or DispatchSpecialist needs to fit under one of the three (probably: sub-cycle = inside-this-cycle, doesn't change the Reviewer's action surface from outside).

**Load-bearing gap**: T4 says FireInvocation as a Reviewer primitive dissolves. Current canon + runtime put it there. This is a direct architecture-shape conflict, not a vocabulary one. The thesis says when the Reviewer judges worldview is too stale, the action is *re-schedule next cycle for after the relevant mirror fires*. Current canon says when the Reviewer judges worldview is too stale, the action is *FireInvocation the upstream recurrence directly* (per principles.md). These produce different runtime behaviors and different cost profiles.

---

## T5 — Worldview maintainers run on their own schedules; they are not judgment

**Thesis target shape**: Only scheduled recurring entities are worldview maintainers (mechanical mirrors). No "judgment recurrence" type. Judgment is one continuous cycle.

### Canon position

| Source | Position | Color |
|---|---|---|
| [ADR-263 D1 "Recurrence schema gains mode: judgment | mechanical"](../adr/ADR-263-recurrence-mode-mechanical-vs-judgment.md) | Two recurrence modes. **`judgment` recurrences DO exist as a type.** They are recurrences whose firing wakes the Reviewer with the recurrence's prompt as the addressed-equivalent envelope. | **C** |
| [ADR-261 D1 "Recurrences are prompts. One shape."](../adr/ADR-261-recurrences-as-prompts.md) | "A recurrence is a self-scheduled wake-up — for the Reviewer (or operator) — that hands the Reviewer a prompt at the scheduled time." Recurrences ARE the kernel's mechanism for waking the Reviewer. | **C** |
| [ADR-275 D1 "Bundle ships capability + maintenance + reactive; not judgment cadence"](../adr/ADR-275-introspection-cadence-reviewer-authored.md) | Bundles ship only mechanical-mode (maintenance) + reactive (`schedule: null`) recurrences; the Reviewer is supposed to *author its own judgment-mode recurrences* via Schedule. **But judgment-mode recurrences themselves are NOT dissolved** — the Reviewer is authorized to create them. The point of dispute is *who authors*, not *whether the category exists*. | **C** (on the category existing); **A** (on bundles not pre-scheduling judgment cadence) |

### Runtime position

| Surface | Position | Color |
|---|---|---|
| `Recurrence.mode` field | Two values: `judgment | mechanical`. Implemented. | **C** |
| Mechanical recurrence dispatch in `_dispatch_mechanical` | Worldview-maintainer path. No Reviewer wake. Aligns with thesis. | **A** |
| Judgment recurrence dispatch via `invoke_reviewer(trigger="reactive")` | The kernel mechanism by which cron fires a judgment recurrence and wakes the Reviewer with that recurrence's prompt. | **C** |
| alpha-trader bundle's `signal-evaluation` recurrence | judgment-mode, scheduled at @market_open + 15min. Bundle-shipped as judgment cadence (in contradiction to ADR-275 D1's "bundles ship only mechanical + reactive"). Operator's trading-strategy heartbeat exception. | **C** + **P** (bundle has carve-out for operator-business-heartbeat) |

### Verdict on T5

**Canon and runtime are C.** The category "judgment recurrence" exists at every layer — canon, runtime, bundles. ADR-275 thins the bundle's judgment cadence to just operator-business-heartbeat shapes (signal-evaluation), but the category itself is intact.

**The thesis dissolves the category.** Under T5, what was a "judgment recurrence" becomes "the Reviewer's next cycle, scheduled with a topic-hint-prompt, that happens to coincide with @market_open + 15min." Mechanically that's similar to a recurrence-with-prompt, but conceptually it's a Reviewer self-scheduled cycle, not a kernel-scheduled recurrence-that-wakes-the-Reviewer.

**Load-bearing gap**: This is partly definitional. If you interpret "the Reviewer's next cycle, scheduled with a prompt" as identical to "a judgment recurrence," the thesis and canon are isomorphic. If you interpret them as structurally different — the difference being *who owns the scheduling decision* and *whether the cycle is "the Reviewer continuing" vs "the kernel waking the Reviewer with a separate identity moment* — they are different shapes.

The audit cannot resolve this. Worth surfacing for the next discourse round: what is the architectural difference between (a) "judgment recurrence fires, wakes Reviewer with its prompt" and (b) "Reviewer's next continuously-self-scheduled cycle happens to start at @market_open + 15min with topic-hint 'evaluate signals'"? Mechanically the same; conceptually different. Does it matter?

---

## T6 — External-world effect is the load-bearing test

**Thesis target shape**: The continuous-judgment-cycle thesis is only as real as the Reviewer's ability to originate external-world writes (`ProposeAction` → execute → real platform write) on its own cadence, against real worldview, under operator-absent conditions. Internal worldview maintenance is necessary but not sufficient.

### Canon position

| Source | Position | Color |
|---|---|---|
| [FOUNDATIONS Axiom 8 "Money-truth substrate"](FOUNDATIONS.md) | Ground-truth substrate per program (`_money_truth.md` for trading; future programs have their analog). Money/value loop closure is foundational. | **A** |
| [ADR-193 ProposeAction + AUTONOMY gating](../adr/ADR-193-action-proposals.md) | Back-edge primitive with autonomy-mode gates. Implemented end-to-end for trading capital actions. | **A** |
| [ADR-293 D4 "AUTONOMY mode gates substrate writes uniformly with capital actions"](../adr/ADR-293-governance-operational-substrate-taxonomy.md) | Uniform gating across capital + substrate writes. | **A** |
| [ADR-294 autonomy-demo + ADR-295 self-amendment discipline](../adr/ADR-294-operator-proxy-and-observation-discipline.md) | Hat-B framework for testing autonomy + Reviewer-self-amendment. | **A** |
| Coverage statement: "every program operating under this thesis must expose back-edge action coverage sufficient for the program's value loop to close" | **Absent.** No canon document explicitly names "back-edge action coverage" as a per-program required artifact. Implicit in ADR-187 (trading) + ADR-183 (commerce) but not canonized as a program-design contract. | **U** |

### Runtime position

| Surface | Position | Color |
|---|---|---|
| `ACTION_DISPATCH_MAP` in `propose_action.py` | alpha-trader has full coverage (`trading.submit_bracket_order`, etc.). alpha-commerce has coverage. alpha-author has NO publish-action coverage. | **P** |
| End-to-end test of Reviewer-originated external writes under operator-absent | The alpha-trader autonomy demo on `kvk` is in flight. T0 baseline captured 2026-05-20. No T+24h evidence yet. | **U** (test is in flight; result pending) |

### Verdict on T6

**Canon and runtime are A on the mechanism** (ProposeAction, AUTONOMY, attribution, risk_gate, autonomy-demo framework) but **P on coverage** (alpha-author can't yet test the back-edge fully because publish-action coverage is absent) and **U on canonization of coverage as a program-design contract**.

**Load-bearing gap**: T6 is mostly aligned where it matters and untested where it doesn't yet have data. The remaining work is (a) extend the alpha-author bundle with publish-action coverage so its autonomy demo tests the back-edge half, and (b) consider canonizing "back-edge action coverage" as a per-program design contract in a follow-on ADR (probably small, possibly absorbed into an updated ADR-294 or ADR-188).

This is the easiest gap to close. Not a primitive redesign; a coverage extension.

---

## T7 — The loop must satisfy three operational constraints to be real (C1: cadence cost, C2: worldview-read completeness, C3: willingness to originate action)

**Thesis target shape**: Three falsifiable constraints. Testable through observation.

### Canon position

| Source | Position | Color |
|---|---|---|
| Cost tractability framework | [ADR-293 D7 "_token_budget.yaml"](../adr/ADR-293-governance-operational-substrate-taxonomy.md) defines per-workspace daily-spend ceilings + max-judgment-recurrences-per-day. [ADR-291 "unified cost ledger"](../adr/ADR-291-unified-cost-ledger.md) defines `execution_events` as authoritative cost record. | **A** |
| Worldview-read completeness | [ADR-276 + ADR-281 substrate ABI](../adr/ADR-276-reactive-trigger-envelope-governance-preload.md) + [`reviewer_envelope.py`](../../api/services/reviewer_envelope.py) covers the universal + program-shaped envelope shape. ADR-296 makes this load-bearing. | **A** |
| Willingness to originate action | [ADR-295 D6 + alpha-trader principles.md](../adr/ADR-295-reviewer-self-amendment-discipline.md) carry the discipline frame (anti-pattern ledger, evidence thresholds). [ADR-295 Phase A-D notes "behavioral drift; v2 amendment expected"](../adr/ADR-295-reviewer-self-amendment-discipline.md) — open question. | **P** |

### Runtime position

| Surface | Position | Color |
|---|---|---|
| Cost telemetry per cycle | `execution_events` columns: input_tokens, output_tokens, cache_read_tokens, cache_create_tokens, model, tool_rounds, envelope_load_ms, duration_ms. Full per-cycle cost telemetry shipped. | **A** |
| Worldview-read latency observability | `envelope_load_ms` column added per ADR-276 hardening (2026-05-15). | **A** |
| Action-origination observability | Reviewer `actions_taken` array in `ReviewerOutput`; `judgment_log.md` lineage entries per ADR-281 §5.D2; bundle-level observation framework via Hat-B `docs/observations/`. | **A** |

### Verdict on T7

**Canon and runtime are A on the three observable properties.** All three constraints (C1 cost, C2 worldview-read, C3 origination willingness) are measurable today through existing surfaces. No new infrastructure needed to *test* the thesis once T1 + T3 + T4 are realized in runtime.

**Load-bearing gap**: None on observability. The constraints are real and measurable. What's not real yet is **the runtime shape that produces measurable behavior under those constraints** — see T1 + T3 + T4 gaps.

---

## Cross-cutting findings

### F1: The "Operator-as-Reviewer acts continuously while the human sleeps" canon framing is consistent with T1 if reinterpreted

[FOUNDATIONS Axiom 2 §"The operator is one principal with two runtime embodiments"](FOUNDATIONS.md) reads, on first pass, like alignment with T1. On audit it's prose-level alignment without runtime commitment. The continuity claimed is *operator's standing intent applied continuously by the Reviewer-embodiment* — substrate-encoded standing intent + Reviewer-as-personified-operator. That is *not* the same as a continuously-running Reviewer cycle.

The thesis (T1) commits the runtime shape that would make the canon prose architecturally true. Without T1, the canon's "acts continuously" claim is true only at the substrate/intent layer, not at the runtime/cycle layer. This is the bridge ADR-296 is proposing to build.

### F2: ADR-260's session-vs-loop terminology is load-bearing

ADR-260 uses "the Loop" (capitalized) to mean *one synchronous Reviewer session*. The thesis (ADR-296) uses "the loop" to mean *the continuous cycle across sessions*. These are different referents.

If ADR-296 is ratified, ADR-260's terminology needs a vocabulary refactor — either ADR-296 invents new vocabulary (e.g., "the Cycle" for the across-time concept), or ADR-260's "the Loop" becomes "the within-cycle synchronous tool-use loop" and "the Cycle" becomes "the cross-time continuous judgment cycle." This is canon-housekeeping, not architectural conflict.

### F3: Mechanical mirrors are A across the board; T5's ambiguity is only on the judgment side

T5 has two halves: (a) mechanical mirrors run on their own schedules, do not wake Reviewer — fully A. (b) Judgment is one continuous cycle, not many recurrences — C (canon has the category; thesis dissolves it). Splitting T5 into T5a + T5b in a future ADR-296 revision would clarify what the thesis commits.

### F4: FireInvocation's runtime presence is the most concrete architectural conflict

T4 says FireInvocation as a Reviewer primitive dissolves. Current `REVIEWER_PRIMITIVES` includes it. The conflict is concrete, primitive-level, and would surface in any implementation work that takes ADR-296 seriously.

Two sub-questions:
- **For Reviewer use**: does dissolving FireInvocation from the Reviewer's primitive surface require *replacing* it with a different mechanism (continuous-cycle scheduling) or *removing* it (the mechanism is unnecessary under T1+T3)?
- **For operator use via chat**: FireInvocation is also in CHAT_PRIMITIVES (used by YARNNN to dispatch operator-initiated "run this now" requests). T4 says nothing about operator-side FireInvocation. Does it survive on the chat-mode surface?

ADR-296 is silent on the operator-chat FireInvocation question. The thesis is Reviewer-shape only; the operator's authority to fire recurrences manually is a different surface.

### F5: Worldview-delta surface is the under-specified piece

The thesis names "worldview deltas — what changed since my last cycle" as a load-bearing input. Today's runtime has the ingredients (standing_intent.md from prior cycle, ADR-209 revision chain, decisions.md history) but no helper composes them into a delta block. The Reviewer is asked to infer the delta during prompt-time reasoning.

This is the thesis's most under-specified mechanism. Three sub-questions for future ADRs:
- Should the kernel compute the delta and surface it as a separate envelope block?
- Or should the Reviewer compute the delta from substrate at prompt-time (current shape, just made more deliberate)?
- Or should the delta surface be "what events landed in execution_events between cycle N−1 and cycle N"?

The answer probably emerges from observation of the alpha-trader / alpha-author autonomy demos as they accumulate cycles. Without empirical evidence of "Reviewer missed a worldview-change because the delta wasn't surfaced," there's nothing to optimize.

### F6: The bundle-authoring "schedule: null" pattern is a symptom, not a primitive

The original session that produced ADR-296 was triggered by the alpha-author bundle's `schedule: null` `pre-ship-audit` recurrence having no caller. The session diagnosed this as a "missing upstream caller" bug to fix at the bundle layer.

Under the ADR-296 lens, `schedule: null` recurrences are *structurally suspect* — the thesis says judgment cadence is Reviewer-authored, so any bundle-shipped recurrence (even reactive `schedule: null` ones) is bundle-fork scaffolding, not Reviewer-authored judgment. The alpha-author bundle's `pre-ship-audit` should either:
- Dissolve entirely; the Reviewer's standing intent ("watch for drafts moving to ready_for_review") + continuous-cycle reading covers it.
- Survive as a *reactive event handler* (operator's `mark ready_for_review` action writes substrate that triggers a Reviewer wake via specialized handler).

Either resolution is consistent with the thesis. The current "schedule: null + waiting for a caller" shape is not.

---

## Gap map summary

| Thesis claim | Canon | Runtime | Load-bearing gap |
|---|---|---|---|
| **T1** Continuous self-pacing cycle | **C** | **C** | No runtime shape for cycle-to-cycle continuity; "session" is the largest unit; cron + bundle declarations own the next-cycle decision, not the Reviewer's previous cycle. Largest gap. |
| **T2** Worldview unifies input | **A** (partial) | **A** (partial) | Trigger source persists in `invoke_reviewer` signature + user-message framing block. Worldview-delta is implicit (standing_intent + substrate state), not explicit. |
| **T3** Cadence is Reviewer-authored at end-of-cycle | **A** on authority; **U** on obligation | **A** on capability; **C** on cycle-terminus enforcement | Self-scheduling is wired but optional; no kernel mechanism for external-event-driven cadence pull-forward against Reviewer interest hints. |
| **T4** Three action shapes only | **C** | **C** | `FireInvocation` in `REVIEWER_PRIMITIVES` directly conflicts with "no Reviewer-facing primitive for fire-this-unit." principles.md teaches the conflicting pattern. `DispatchSpecialist` is a fourth shape the thesis didn't name. |
| **T5** Mechanical mirrors only; no judgment recurrence | **A** on mirrors; **C** on judgment-recurrence category | **A** on mirrors; **C** on judgment-recurrence category | Definitional ambiguity: "judgment recurrence with prompt" vs "Reviewer cycle self-scheduled with topic hint" may be mechanically isomorphic. Worth deciding in next discourse round. |
| **T6** External-world effect is the test | **A** mechanism; **U** on coverage canonization | **A** mechanism; **P** coverage (alpha-author lacks publish actions); **U** test result pending | Easiest gap to close. Extend alpha-author bundle. Consider canonizing back-edge action coverage as a per-program design contract. |
| **T7** Three observable constraints | **A** | **A** | None on observability. Gap is on the runtime shape that would produce measurable behavior under T1+T3+T4. |

---

## What the next discourse round needs to decide

Five questions surface from this audit. Each is upstream of any implementation work.

### Q1: Cycle-vs-session vocabulary commitment

ADR-260 uses "the Loop" to mean *within-session synchronous tool-use*. ADR-296 thesis uses "the loop" to mean *across-session continuous judgment cycle*. Does ADR-296 commit to new vocabulary (e.g., "the Cycle"), and does ADR-260's terminology get re-keyed accordingly?

**Decision needed**: vocabulary commitment, no architectural change.

### Q2: T5 definitional ambiguity

Is "judgment recurrence fires, wakes Reviewer with prompt" architecturally *different* from "Reviewer self-scheduled next cycle at this time with this topic hint"? If the same mechanism implements both, what's the load-bearing distinction?

**Decision needed**: whether T5 is a structural commitment or a vocabulary preference. If structural, the next ADR specifies the architectural difference. If vocabulary, T5 simplifies to "what we call them changes; the mechanism doesn't."

### Q3: FireInvocation's fate

Three candidate resolutions to F4:
- **(a)** Remove FireInvocation from `REVIEWER_PRIMITIVES`. Replace its use cases (stale-substrate commission, downstream-judgment chaining) with self-scheduled next-cycle.
- **(b)** Keep FireInvocation for operator-chat-initiated manual fire only (remove from REVIEWER_PRIMITIVES; keep in CHAT_PRIMITIVES).
- **(c)** Keep FireInvocation as-is; accept that ADR-296 thesis dissolves with empirical evidence of the loop closing without it, but until then it survives.

**Decision needed**: which resolution. Implementation work depends on it.

### Q4: Worldview-delta mechanism

Should "what changed since my last cycle" be:
- **(a)** A kernel-computed delta block in the envelope.
- **(b)** Inferred by the Reviewer from `standing_intent.md` + current substrate.
- **(c)** A query over `execution_events` between previous cycle and now.
- **(d)** Some hybrid.

**Decision needed**: under-specified in ADR-296; needs commitment in ADR-296a or absorbed into a follow-on.

### Q5: T1 realization mechanism

The largest gap is T1 — no runtime shape for cycle-to-cycle continuity. Three candidate implementations:
- **(α)** Reviewer's cycle terminus *requires* `Schedule(action="create", slug="reviewer-next-cycle", schedule="...", prompt="...")` before `ReturnVerdict`. Hard contract.
- **(β)** Reviewer's cycle terminus *defaults to* scheduling the next cycle (via persona-frame guidance + soft tooling), but doesn't fail-fast if absent — kernel has a fallback "if no next cycle is scheduled, default to next operator-declared cadence-floor."
- **(γ)** Hybrid: substrate-event-driven dispatcher detects "next cycle should pull forward" against Reviewer's prior interest hints in `standing_intent.md`, fires on that. Reviewer doesn't have to author schedule mid-loop; the kernel infers from standing intent.

**Decision needed**: this is the architectural shape of the autonomy loop. Major decision; the entire follow-on implementation work depends on it.

---

## What is NOT in this audit

- No canon-edit recommendations. The audit names gaps; resolution is the next round's discourse.
- No code changes. The audit reads runtime; doesn't propose edits.
- No ADR-296 revision. The pure-thesis form stands until the discourse round produces commitments worth folding back into it.
- No Hat-B observation work. This is Hat-A canon audit. The Hat-B observation work (alpha-trader autonomy demo T+24h / T+5d) feeds into Q5's empirical evidence base, but is its own work product.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-05-20 | v1 — Initial audit. Canon (FOUNDATIONS Axioms 2/4, GLOSSARY, ADR-256/260/261/263/274/275/276/293/295, invocation-and-narrative.md) read; runtime (invocation_dispatcher, reviewer_agent, reviewer_envelope, unified_scheduler, scheduling.py, primitives/registry.py) read; bundle reference workspaces (alpha-trader, alpha-author) read. Seven thesis claims rated A/P/C/U against canon and runtime separately. Five decision questions surfaced for next discourse round. No implementation. No canon edits. No ADR revisions. |
