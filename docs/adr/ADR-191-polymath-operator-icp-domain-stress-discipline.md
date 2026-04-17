# ADR-191: Polymath Operator ICP + Domain Stress Discipline

> **Status**: Proposed
> **Date**: 2026-04-17
> **Authors**: KVK, Claude
> **Extends**: ADR-188 (Domain-Agnostic Framework), ADR-189 (Three-Layer Cognition), ADR-190 (Inference-Driven Scaffold Depth)
> **Ratifies**: `docs/architecture/DOMAIN-STRESS-MATRIX.md` as the operational conscience for agnostic-by-design

---

## Context

### The strategic tension this resolves

ADR-188 committed YARNNN to a domain-agnostic framework: registries as template libraries, universal roles with contextual application, novel domains composable by YARNNN at workspace level. ADR-189 doubled down: authored team, user-created Agents, Specialists as palette. ADR-190 completed the arc: inference-driven scaffold depth sets the floor for any first-act input.

The strategic question surfaced after ADR-190 shipped: **what's the GTM thesis on top of an agnostic core?**

The conventional SaaS playbook says pick a vertical wedge, dominate, expand. That would contradict three weeks of architectural work. The ADRs claimed universality; a vertical wedge would say the architecture was overbuilt.

The honest alternative: **commit to agnostic at the go-to-market layer too.** The ICP is psychographic (operator-shape), not industry (vertical). The validation strategy is a conglomerate alpha across dissimilar business domains, not a niche beachhead.

### What this ADR does

Ratifies two linked commitments:

1. **ICP is the polymath operator** — a person who runs 2–3 income streams and wants one tool across all of them. Indie hackers with multiple products, creators with side businesses, consultants with niche service lines, scouts running portfolios + newsletters, operators with both a store and a trading account. The ICP is defined by operator-shape, not industry.

2. **Domain stress discipline** — alpha validation runs across multiple structurally different business domains, one test account per domain. Every future ADR is gated by a `DOMAIN-STRESS-MATRIX.md` check: does this change help all tracked domains, or does it verticalize by stealth?

The conglomerate alpha is the **product-validation strategy**; the polymath operator is the **public ICP for SaaS GTM**. Both are consistent with the shipped architecture. Neither requires verticalizing the core.

---

## Decision

### 1. ICP (public positioning): polymath operator

Target: operators who run multiple income streams and refuse to specialize into one tool per stream.

Concrete sub-segments (non-exclusive):
- Indie hackers with 2+ products
- Creators with a content business + e-commerce side
- Solo VC/scouts running deals + newsletters
- Consultants with 2+ niche service lines
- Small-shop traders who also run content or advisory work
- Operators who have "a store and a portfolio" or "a newsletter and a consulting practice"

What they share (the psychographic):
- Polymath identity — identity is tied to running multiple things, not mastering one
- Willingness to pay to replace tool-per-stream with one coherent tool
- Tolerance for a product that's abstract enough to serve all their streams
- Revenue legible across streams (they can see what each stream earns)

What they are NOT:
- "SMB" generic — too broad, produces no wedge
- "Solo founder" generic — too broad, most focus on one thing
- Vertical operator (newsletter-only, store-only) — these are edge cases yarnnn serves, not the ICP

### 2. Alpha validation: conglomerate of test accounts across structurally different domains

Rather than 50 customers in one vertical, alpha runs ≥4 test accounts across ≥4 structurally different business domains. Each account is one operator, one domain, one workspace (single-workspace-per-account; multi-workspace-per-user is deferred to a future ADR if polymath-as-public-ICP demands it).

Initial alpha domains (see `DOMAIN-STRESS-MATRIX.md` for full spec):

| # | Domain | Priority | Rationale |
|---|--------|----------|-----------|
| 1 | **E-commerce operator** | Active | Commerce integration (ADR-183) exists. Clean revenue attribution. Reversible write-backs. Moderate error cost. |
| 2 | **Day trader** | Active | Trading integration (ADR-187) exists. High quality bar (real money). Exercises external_action write-backs. |
| 3 | **AI influencer** | Scheduled | Net-new integration work (content platforms). Start after #1 and #2 prove the core. |
| 4 | **International trader** | Scheduled | Most novel domain. Hardest architectural stretch. Last to spin up. |

Sequence: e-commerce first (gentler domain, builds trust in the core loop), day trader second (tighter quality bar). Influencer third, trader fourth.

Each alpha account is run by someone in the founder's close network, onboarded directly, instrumented for failure-mode observation.

### 3. Anti-verticalization discipline: DOMAIN-STRESS-MATRIX.md as gate

New canonical doc at `docs/architecture/DOMAIN-STRESS-MATRIX.md`. Every architectural change from this ADR onward is gated by a matrix check:

**Gate rule:** Before any new ADR ships, the author writes one row in the matrix's "Impact" table stating how the change affects each active domain. Acceptable patterns:

- "Helps all columns" → green-light.
- "Helps most, neutral on others" → green-light.
- "Helps one, neutral elsewhere" → **verticalization warning**. Requires explicit justification or design revision.
- "Helps one, hurts others" → **reject or rescope**. The change is verticalizing by stealth.

The matrix is append-only (each alpha domain row expands with lived experience) and cross-referenced from every follow-on ADR.

### 4. The conglomerate backstop is separated from the SaaS thesis

Operators running yarnnn as a personal multi-business infrastructure (the "conglomerate intra-tool" use case) is an acceptable terminal state, but it is explicitly **not the primary SaaS thesis**. The SaaS thesis is polymath-operator ICP with public GTM after alpha proves architecture.

This separation prevents morale-hedge creep. The conglomerate backstop stays as personal infrastructure success; the polymath SaaS is the commercial ambition. Both can succeed; they don't compromise each other.

---

## What this replaces

- Any implicit assumption that yarnnn would eventually pick a vertical. Verticalization is now an explicit anti-goal unless the alpha produces overwhelming single-domain signal.
- The "pick a wedge" SaaS playbook as the default GTM framing for yarnnn. Does not apply.

## What stays unchanged

- All architectural ADRs. ADR-188 / 189 / 190 are the foundation this sits on.
- The task pipeline, primitive matrix, execution model, compose substrate — unchanged.
- The existing test-workspace and alpha tooling — used as-is.
- Single-workspace-per-account (multi-workspace-per-user deferred until polymath-as-public-ICP phase demands it).

---

## Consequences

### Positive

1. **Architecture and strategy finally align.** Three weeks of agnostic refactoring was shipping without a coherent GTM story. This closes the gap.
2. **Defensible positioning.** "One tool for operators who run multiple things" is a claim competitors optimized for verticals can't make — they'd have to also support multiple workflows, and their verticalized data models won't allow it.
3. **Alpha tests the actual architectural claim.** Running four dissimilar businesses is a stricter product test than 50 customers in one vertical. If it holds, the moat is ironclad.
4. **Anti-verticalization conscience is explicit, not tribal.** The matrix-gate rule means verticalization has to be an argued-for decision, not an accidental drift.

### Costs

1. **Harder pitch to investors.** "Polymath operator" is a psychographic ICP, not a market-sized vertical. Requires more sophistication to sell the TAM story.
2. **Surface design harder.** Every frontend decision has to be checked against four domains. More design work than designing for one.
3. **Longer time-to-signal on GTM.** A vertical wedge produces clear signal in 30 days (conversion rate in one niche). The polymath thesis takes longer to validate because the cohort is harder to identify and segment.
4. **Requires discipline.** Without the matrix-gate, natural gravity is toward whichever alpha friend talks loudest. Discipline or the agnostic thesis dissolves.

### Deferred

- **Multi-workspace-per-user.** Polymath operators running multiple businesses on one yarnnn account is a natural product shape, but the alpha uses separate accounts per business for clean isolation. Multi-workspace is a future ADR that ships when polymath-as-public-ICP demands it.
- **Sub-segment focus within polymath.** Even within polymath operators, there are sub-segments (creator+commerce, scout+newsletter, etc.). A later GTM iteration may narrow. This ADR keeps it broad until alpha signal dictates otherwise.
- **Pricing for polymath.** If one operator runs multiple yarnnn accounts (one per business), how does billing compose? Per-account (simple) vs. per-operator with workspace bundles (polymath-aligned). Defer until post-alpha.

---

## Implementation sequence (five follow-on ADRs)

This ADR itself is documentation-only. The downstream work lands in five ADRs:

| # | ADR | Purpose |
|---|-----|---------|
| 1 | **ADR-192** | Platform write coverage expansion — audit commerce (ADR-183) + trading (ADR-187) write primitives against matrix's "Write primitives needed" column; close gaps |
| 2 | **ADR-193** | `ProposeAction` primitive + approval loop — the guardrail primitive for trusted write autonomy |
| 3 | **ADR-194** | Surface archetypes — document / dashboard / operational pane as frontend rendering modes; extends `/work`, `/context`, adds pane surfaces |
| 4 | **ADR-195** | TP autonomous decision loop — signal detection → ProposeAction generation → scheduled evaluation |
| 5 | (follow-on) | Surface-brief implementations per ADR-194 per alpha domain |

Order rationale: ADR-192 is mechanical (no architectural risk, unblocks alpha). ADR-193 is the LOAD-BEARING architectural ADR (without approval loop, write autonomy is either always-on or always-manual). ADR-194 composes with 193's output (operational pane renders approval proposals). ADR-195 sits on top. Each ADR gated by the matrix.

Parallel throughout: alpha instrumentation. E-commerce friend spins up first, pain observed, matrix row evolves, next ADR prioritized based on observed friction.

---

## Open questions

1. **Billing for multi-account polymaths.** If one operator runs four alpha test accounts, are they four customers or one? Defer until post-alpha data.
2. **When does polymath-as-public-ICP officially launch?** The alpha is private (founder's network). The thesis ships publicly when... what signal triggers? Likely when 2+ alpha domains show Day-30 compounding that resembles the moat claim.
3. **Multi-workspace-per-user trigger.** What's the friction signal from polymath operators that triggers building multi-workspace? "I have two yarnnn logins and keep forgetting which one I'm on" is the weak signal; "I want YARNNN to know about my whole business portfolio" is the strong signal.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-17 | v1 — Initial proposal. ICP = polymath operator. Alpha = conglomerate of ≥4 test accounts across structurally different domains. Anti-verticalization discipline = DOMAIN-STRESS-MATRIX.md gate on every future ADR. Five-ADR implementation sequence. |
