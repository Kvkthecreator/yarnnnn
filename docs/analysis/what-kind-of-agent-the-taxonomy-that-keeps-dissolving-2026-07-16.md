# What kind of agent? — the taxonomy YARNNN keeps dissolving

**Status**: Research synthesis. **The operator's ask**: *"more on conceptual framing of what kind of agent registry we should start… research our own codebase on related refactorings, analysis, documentation as the evolution of yarnnn's own codebase related to this topic may actually surface some interesting approach. The technical infra stays as we've been discussing, more on the TYPES of agents."*
**Date**: 2026-07-16
**Method**: four parallel readers across the four eras (early type-taxonomies · persona/judgment-seat · production-role capability bundles · current registry vs market). All quotes verbatim with file:line.

---

## 1. The finding, before the history

**YARNNN has answered "what KIND of agent is there?" at least eight times, and every revision removed kinds rather than adding them.** The arc terminates — twice, independently — at *there is no kind, only configuration.* The current four-agent roster (Sonnet · Scout · Critic · Designer) is not a new taxonomy; it is the **endpoint of a decade-compressed dissolution**, and it sits on an axis the codebase already proved was the invariant one.

So the interesting answer to *"what registry should we start?"* is: **the registry is already the right shape, and the codebase has the receipts to prove it — the risk is not designing it wrong, it is re-laddering it, which the history shows is the one thing YARNNN cannot stop trying to do.**

Two things fell out of the research that change what to do next (§5), and one is a live defect (§6).

## 2. The two poles, and the oscillation named in-canon

Every taxonomy revision was a swing between two poles:

- **Pole A — a FIXED ROSTER of named kinds.** ADR-093's 7 purpose types; ADR-140's 6 business-function agents; ADR-176's *Hospital Principle*: *"The specialist roster is fixed at signup — same six roles for every workspace — and cannot be configured by the user. This is deliberate, not a limitation"* (ADR-176:69).
- **Pole B — DISSOLVE kinds into something universal/emergent.** ADR-109's orthogonal axes; ADR-176's *universal* roles; ADR-188's "universal roles, contextual application"; ADR-205's dispatch-time palette with **zero** persisted rows.

**The codebase named its own oscillation, in-canon** — ADR-138:28-29:

> *"**We're stuck in the middle.** We built project infrastructure but keep trying to collapse toward simpler models. Every session adds project complexity; the next session proposes simplifying it. **This oscillation wastes effort.**"*

That sentence is the most important line in the whole record for the operator's question. It is the codebase catching itself doing the thing, three years before now.

## 3. Two arcs, one destination

The research found the dissolution runs on **two separate tracks** that converge on the same endpoint — which is why the endpoint is trustworthy (it was reached twice, by different routes).

### Track 1 — the "what work does it do?" axis (early era)

The classifying axis kept being found to be a *conflation*, and each revision cleaved it:

| ADR | Axis | What it was found to conflate |
|---|---|---|
| **092** | five execution modes (`recurring/goal/reactive/proactive/coordinator`) | separated *when* from *what* |
| **093** | 7 purpose types (`digest/brief/status/watch/deep_research/coordinator/custom`) | still bound platform + intent into the type name |
| **109** | Scope × Role × Trigger | still bound *identity* to *work* |
| **138** | **WHO (Agent) vs WHAT (Task)** | freed identity from work; roles → 4 archetypes |
| **140** | 6 business-function agents, pre-scaffolded | ICP-specific — encoded a user archetype |
| **176/188** | **6 universal cognitive roles**, contextual instantiation | *the actual invariant* |
| **205** | roles survive only as a dispatch-time palette, "**do not accumulate identity**" | the invariant lives in the vocabulary, never in a roster |

The resolution, ADR-188:79 — *the Hospital Principle bisected*:

> *"The principle was **correct about roles**… but incorrect about **roster size and domain assignment**. The evolved principle: **Universal roles, contextual application.**"*

**One line**: the fixedness belongs to the *vocabulary of cognitive functions*; the fluidity belongs to *which and how many* you instantiate. A fixed vocabulary, never a fixed roster.

### Track 2 — the "what kind of judgment entity?" axis (persona era)

Separately, the persona/seat question dissolved the same way:

| ADR | What makes one agent a different KIND |
|---|---|
| **194** | its **Purpose + Trigger cell** — a structural seat, *explicitly not Identity*; the occupant is swappable |
| **216** | **persona-bearing-ness** — judgment (output-divergent) vs orchestration (performance-fungible); *"No hybrid classification"* |
| **315** | (orthogonal) **seat = substrate, occupant = module** — the prerequisite that made the rest possible |
| **381** | **seat-class / order** — one management seat + N judgment seats |
| **383** | **→ nothing structural**: *"the same KIND of construct, differing only in file CONTENT"* (ADR-383:22) |
| **408 D2** | (re-expansion) **altitude** — an ordinal bundling attribution/persona/autonomy/budget |
| **460** | **→ there is no kind**: *"Configuration is a vector, not a rung"* (ADR-460:72) |

ADR-460 explicitly cites 383 as its precedent — *"one order up, already ratified"* (ADR-460:67). **The dissolution was performed twice**: ADR-383 killed the Freddie-vs-persona *structural* distinction; ADR-460 killed the altitude *ordinal*. Both land on: one concept, a fact-vector, and a single gate.

## 4. What the two arcs agree on — the invariant, stated three ways

Both tracks, across eight years of compressed revision, converge on **one structural claim**:

> **There is no taxonomy of agent kinds. There is a fixed vocabulary of what an agent is *for*, an open set of instances, and exactly one boundary that is not a dial — consequential authority — which is held off the entity entirely, at the ADR-307 gate.**

- Track 1 calls the vocabulary *universal cognitive roles* (research/analyze/write/track/design/report).
- The current registry calls it *reasons a member reaches for a colleague* (think/read/pressure-test/make).
- **These are the same axis, narrowed and verb-shaped.** "Reason" is "cognitive function" phrased as *"which colleague do I address?"* instead of *"what does this worker contribute?"* — the layman re-cut of the exact invariant ADR-188 found.

And the one survivor of "kind" is not an entity property: *"Consequential authority was never an Identity property. It is the ADR-307 gate… This ADR deletes the shadow, not the gate"* (ADR-460:101). Every station from ADR-381 onward correctly identified the reversible-vs-consequential seam as the real one; ADR-460 finally moved it off the taxonomy and onto the gate where it was always enforced.

## 5. What this means for "what registry should we start"

**Do not start a new taxonomy. The invariant is found, and it is the one the registry already uses.** The history's lesson is not "here is the right set of kinds" — it is *"stop reaching for kinds."* Three concrete consequences:

**(a) The classifying axis is settled, and it is the right one.** "One Agent per reason a member reaches for a colleague" (agents_registry.py:60) is ADR-188's universal-cognitive-role invariant, re-derived in layman's words. It is not another swing — it is the pole B endpoint, and ADR-460's structural cliff (no authority field, `test_agent_registry.py`) is the **anti-oscillation ratchet** the earlier eras never had. This is why it will hold where 093/140/176 did not.

**(b) The record says the next move is NOT a fifth agent.** The multi-LLM audit is explicit: *"Deliberately NOT in scope: the roster's size… a fifth character changes nothing while every Agent has identical hands. The lineup question is downstream of the tools question"* (multi-llm-audit §6). The unit of growth is **depth, not breadth** — deeper hands for the four (which ADR-463 P2 began, Scout's `QueryKnowledge`+`WebSearch`), and the member-authored identity widening (Lisa `based_on` a kernel reason), which is *already built*. Growing the roster is the Pole-A instinct the history warns against.

**(c) The one honest gap the vocabulary has never closed: the reasons were never enumerated.** ADR-176 asserted *six* cognitive roles; the current registry ships *four*; neither derived the set from first principles — each is a judgment call about "enough." **This is the real open conceptual question**, and it is small and bounded: *is the vocabulary of reasons complete at four (think/read/pressure-test/make), and if not, what is the fifth reason a member reaches for a colleague — not the fifth engine, not the fifth persona, the fifth VERB?* The history says: only add one when a member's unmet reach names it, never to fill a grid (ADR-140's error) and never per-engine (the spec sheet).

## 6. ⚠️ A live defect the research surfaced — the canon lags the code by one move

**`LAYER-MAPPING.md` and `reviewer-seat-substrate.md` still teach the three-altitude ladder as canon.** Both were last rewritten 2026-07-07 (ADR-414/408); neither carries an ADR-460 amendment. `grep` for "460 / one concept / independent fact / no ladder" returns nothing in either.

This is not cosmetic. LAYER-MAPPING is cited by CLAUDE.md as *"the authoritative taxonomy"*, and it currently states:

- *"The sharp word 'Agent' lands at Altitude 3"* and *"`/agents` — the roster is Altitude 3 only (ADR-412 D5)."*

But the roster we shipped this week puts Sonnet/Scout/Critic/Designer — **Altitude-2 helpers by that doc's own classification** (`member:` attribution, no standing intent) — on `/agents`. **The authoritative taxonomy doc and the live surface now disagree about what kind of thing the roster holds**, because the doc predates the dissolution that made "Altitude 2 vs 3" not a thing.

This is the oscillation's *fingerprint*: a dissolution shipped in code (ADR-460) while the canon still teaches the ladder it dissolved. It should be reconciled — LAYER-MAPPING amended to the fact-vector model — **before** any further agent-type work, or the next session will design against a taxonomy the code already retired. (Its own §"Specific clarifications" even hints at the resolution: *"Industry 'agent' vocabulary maps closest to Altitude-2 helpers"* — which under ADR-460 is just *the member's hands attributing as themselves*, no altitude needed.)

## 7. One-line statement

**YARNNN has re-answered "what kind of agent?" at least eight times and every answer removed kinds — the early era proving the invariant is a fixed *vocabulary of cognitive functions, not a roster* (ADR-188's bisected Hospital Principle), the persona era proving *"same construct, different content… configuration is a vector, not a rung"* (ADR-383 → ADR-460) — so the registry to "start" is the one we already have, on the axis the codebase already proved invariant (reason-a-member-reaches-for-a-colleague = universal-cognitive-role in layman's words), with the only real open question being whether the vocabulary of reasons is complete at four; and the one thing to fix first is that the authoritative taxonomy doc still teaches the altitude ladder the code dissolved a week ago.**
