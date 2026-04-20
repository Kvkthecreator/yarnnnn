# ADR-198: Surface Archetypes — Five Substrate-Consumer-Purpose Cells

> **Status**: Proposed (2026-04-20)
> **Date**: 2026-04-20
> **Authors**: KVK, Claude
> **Extends**: FOUNDATIONS v6.0 Axiom 6 (Channel) + Derived Principle 12 (Channel legibility gates autonomy)
> **Amends (not supersedes)**: ADR-180 (Work/Context Surface Split), ADR-163 (Surface Restructure), `docs/design/SURFACE-ARCHITECTURE.md` v14 (four nav tabs). This ADR introduces a distinct, deeper framing — **archetypes** under the four nav tabs, not a replacement for them.
> **Depended on by**: ADR-195 Phase 4 (daily-update briefing), ADR-195 Phase 5 (feedback actuation surface), ADR-194 v2 Phase 2b (review-proposal Queue surface)
> **Primary dimensions (v6.0)**: **Channel** (the Where dimension). Secondary: Purpose (operator-consumer affordances), Identity (operator as consumer, with archetype-specific read patterns).

---

## Context

### Why this ADR now

FOUNDATIONS v6.0 names Channel as one of the six orthogonal dimensions (Axiom 6) and introduces Derived Principle 12: *"Channel legibility gates autonomy. An action without a visible channel is a trust leak — the operator cannot supervise what they cannot see."* The principle names ADR-198 as the doc where surface archetypes are canonized.

At the same time, the following are all partially-shipped or imminent:

- **Money-truth substrate** (ADR-195, Phases 1–3 Implemented) — `_performance.md` per domain + `_performance_summary.md` cross-domain are now in Substrate, but the operator's only addressed Channel to read them is the existing Files surface (cross-task domain browsing per ADR-180). No briefing pointer, no dashboard, no stream view.
- **Reviewer decisions substrate** (ADR-194 Phase 2a Implemented) — `/workspace/review/decisions.md` is appended on every approve/reject, but operators have no dedicated stream surface to read it.
- **ProposeAction queue** (ADR-193) — `action_proposals` rows render inline in chat as ProposalCard. No dedicated Queue surface.
- **Daily-update briefing** (ADR-161) — ships as email, reads from compact index. Phase 4 of ADR-195 wants to extend it to cite `_performance_summary.md`. Under Principle 12, that extension must be *pointer-based* (briefing links to a legible destination), not *content-duplicating* (briefing repeats what a dashboard could show).

**The existing nav tabs (Chat / Work / Files / Agents per ADR-180 + SURFACE-ARCHITECTURE v14) are correct and unchanged.** What's missing is a framing for *what shape of Channel each tab actually offers*. Without that framing, new features silently drift into arbitrary placements — a new summary ends up on Chat's home tab, a new stream ends up on Work, a new queue ends up inline — because there's no dimensional vocabulary for "this is a dashboard-shaped thing, it belongs in a dashboard archetype."

ADR-198 gives that vocabulary.

### The dimensional framing

A **surface archetype** is a Channel cell characterized by:

- **What Substrate it reads** (Substrate dimension)
- **Who the consumer is** (Identity dimension — in v1, always the operator)
- **What Purpose the reading serves** (Purpose dimension)
- **How it's read** (one-shot / live / appended-over-time / periodic)

Five archetypes cover the operator's reading surface exhaustively for current scope. Each is distinct in at least one of those four properties — no two archetypes are collapsible into each other without losing information.

---

## Decision

### Five archetypes

| # | Archetype | Substrate read | Purpose | Reading shape | Nav home |
|---|---|---|---|---|---|
| 1 | **Document** | A composed output file (`/tasks/{slug}/outputs/{date}/` + compose artifacts) | Consume a deliverable | One-shot read, HTML or markdown | `/work?task={slug}` |
| 2 | **Dashboard** | Live state of a Substrate slice (`/workspace/context/{domain}/`, `/workspace/context/_performance_summary.md`, agent roster) | See what the state *is right now* | Continuous read; refreshed on every visit | `/context`, `/context?domain=…`, `/agents`, future `/money` |
| 3 | **Queue** | Pending addressed-to-operator items (`action_proposals` rows, `/workspace/review/decisions.md` pending tail) | Act on what's awaiting | List of actionable entries, each with approve/reject/defer affordance | `/chat` inline ProposalCards + future `/review` |
| 4 | **Briefing** | Curated selection across multiple Substrate files (`_performance_summary.md`, today's digests, pending proposals count) | Receive periodic one-shot summary with pointers | Periodic push (email); read on demand (Chat home) | Email + `/chat` home view |
| 5 | **Stream** | Append-only log files (`decisions.md`, `memory/notes.md`, `feedback.md`, per-task run logs) | Audit what has happened, chronologically | Append-at-end, read newest-at-top or newest-at-bottom per convention | `/review` stream view, `/work?task=…` run log, Files |

### The five are exhaustive for current scope

Every operator-facing Channel in YARNNN today maps to exactly one of the five. The exhaustiveness check:

- "I want to read the current sales brief." → **Document** (the composed weekly brief at `/tasks/weekly-sales-brief/outputs/latest/`).
- "I want to see my book right now." → **Dashboard** (`/workspace/context/_performance_summary.md` rendered at `/context`).
- "What's waiting on my approval?" → **Queue** (pending `action_proposals`).
- "What should I know this morning?" → **Briefing** (daily-update email + Chat home).
- "What did the Reviewer decide last week?" → **Stream** (`decisions.md` rendered chronologically).

The five are collectively exhaustive and mutually exclusive under Axiom 6's sub-shape test (Substrate-return vs Addressed, crossed with periodic vs reactive vs addressed consumer affordance).

### Archetypes are not nav tabs

Critical clarification: **ADR-198 does not add nav tabs.** The four tabs (Chat / Work / Files / Agents) from ADR-180 are unchanged. Archetypes describe *the shape of Channel within* nav tabs — one nav tab can host multiple archetypes, and one archetype can appear under multiple nav tabs.

Mapping current state:

| Nav tab | Archetypes hosted today |
|---|---|
| `/chat` | Briefing (home), Queue (inline ProposalCards), conversation proper (not an archetype — this is Identity's address mode) |
| `/work` | Document (task detail output), Stream (task run log), Dashboard (task health card) |
| `/context` | Dashboard (domain folder view, `_performance_summary.md`) |
| `/agents` | Dashboard (roster), Document (AGENT.md detail view) |
| Email | Briefing (daily-update) |

This mapping is the normative cell under Axiom 6. A new feature proposing to, e.g., surface the Reviewer's stream should pick a nav tab + declare "this is a Stream archetype" rather than invent a new tab.

### Archetype invariants

Each archetype carries invariants that keep the dimensional separation clean:

**Document invariants.**
- D1: Read-only from the operator's side. Operator edits flow through feedback primitives (per ADR-181), not direct edit.
- D2: One document = one Substrate file (or a manifest that addresses a set). No cross-file composition at read time — composition happens in Mechanism (the compose substrate per ADR-170), then the result is a single Substrate artifact.
- D3: Documents have stable URLs. Linking from Briefing (#4) points at a Document.

**Dashboard invariants.**
- D1: Always a live Substrate slice read. No cached or scheduled snapshot unless the Substrate itself is snapshot-regenerated (e.g., `_performance_summary.md` is regenerated by the daily reconciler; Dashboard is still live-reading the current file).
- D2: No action affordances. A dashboard that sprouts "Approve" buttons becomes a Queue — redesign as Queue or use a separate Queue pane.
- D3: Grouping/filtering is the surface's job; data shape is Substrate's job.

**Queue invariants.**
- Q1: Every entry has a pending status (status column on a row, or unresolved block in a file). Resolved entries leave the Queue.
- Q2: Every entry has action affordances (approve / reject / defer / modify-then-approve). A Queue without actions is a Stream.
- Q3: Resolution writes an audit entry to a Stream archetype (decisions.md for review, activity log for others).

**Briefing invariants.**
- B1: Periodic by Trigger (per Axiom 4's periodic sub-shape). Daily cadence is default; weekly briefings are a natural extension.
- B2: Composed by selection, not by duplication. Briefing content is *pointers + headline numbers* from other archetypes, not a re-render of their content.
- B3: Briefing has a legible Channel consumer (email for operator outside the app; Chat home for operator inside the app).

**Stream invariants.**
- S1: Append-only to Substrate. Mutations to historical entries are not permitted (edits would be a different archetype — Stream + Document hybrid violating Axiom 6).
- S2: Ordering is chronological. Grouping/filtering is permitted at the surface; reordering the underlying file is not.
- S3: Stream content is always historical — a Stream that shows a projection of the future is mis-archetyped.

### Channel legibility applied to current gaps

Principle 12 says autonomous writes need a legible Channel. Mapping current gaps by archetype:

- **Reviewer `decisions.md`** (ADR-194 Phase 2a shipped) — no Stream surface yet. ADR-194 Phase 2b will add `/review` or a Chat tab for this Stream. Until it ships, operators can only access `decisions.md` via the generic Files browser — legible but not dedicated. *Principle 12 status: weak, addressable in Phase 2b.*
- **Money-truth `_performance_summary.md`** (ADR-195 Phase 3 shipped) — readable via generic Files browser only. ADR-195 Phase 4 adds Briefing pointer ("Your book this week" in daily-update email links to `/context?path=/workspace/context/_performance_summary.md`). *Principle 12 status: weak now, Briefing pointer fixes it; true Dashboard archetype deferred until Phase 4 observation shows the email-pointer pattern is inadequate.*
- **`action_proposals` pending queue** — ProposalCards in Chat are a Queue archetype inline. No dedicated `/review` tab yet. Adequate for alpha scope; ADR-194 Phase 2b adds `/review` when proposal volume warrants. *Principle 12 status: adequate for current volume.*
- **Reviewer principles + identity** (`/workspace/review/IDENTITY.md` + `principles.md`, ADR-194 Phase 1 shipped) — read via Files. Legible. *Principle 12 status: adequate as Dashboard archetype under Files.*

### What ADR-198 is not

- **Not a nav change.** Four tabs unchanged.
- **Not a re-layout of existing surfaces.** No redesign of Work, Agents, Files, or Chat; they continue per their owning ADRs (ADR-180, ADR-167, ADR-165, ADR-163).
- **Not new routes.** Any new route (e.g., `/review`, `/money`) is a separate ADR with ADR-198 as its dimensional-classification reference.
- **Not a UI component library.** Archetype invariants are at the dimensional level (Channel × Purpose × Consumer), not the visual-component level. Two Dashboards can look different; what makes them both Dashboards is Axiom 6 behavior.

---

## Implementation sequence

No code in this ADR. It's a canonization of framing that later ADRs cite as a prereq. Future phases that cite ADR-198:

| # | Future ADR | Uses ADR-198 for |
|---|---|---|
| ADR-195 Phase 4 | Daily-update briefing integration | Briefing archetype — pointer-based, not duplicating |
| ADR-194 Phase 2b | `/review` Queue + Stream surface | Queue + Stream archetype invariants |
| ADR-195 Phase 5 | Feedback actuation surface | Queue + Stream archetype for high-impact outcome feedback entries |
| Future | `/money` Dashboard (if operator-facing need emerges) | Dashboard archetype for `_performance_summary.md` |

---

## Impact table (per ADR-191 matrix gate)

| Domain | Impact | Notes |
|--------|--------|-------|
| **E-commerce** | Helps | Document (campaign briefs), Dashboard (revenue summary), Queue (autonomous discount proposals), Briefing (weekly revenue email), Stream (churn-signal event log) — all mappable. |
| **Day trader** | Helps | Document (trade thesis output), Dashboard (position + P&L), Queue (trade proposals), Briefing (pre-market), Stream (trade history + review decisions) — all mappable. |
| **AI influencer** | Forward-helps | Document (drafted post), Dashboard (engagement state), Queue (publish proposals), Briefing (daily trend pulse), Stream (brand-deal history). |
| **International trader** | Forward-helps | Document (route brief), Dashboard (shipment state + counterparty scorecard), Queue (tariff/compliance alerts to act on), Briefing (weekly trade brief), Stream (compliance-incident log). |

Every alpha domain uses all five archetypes naturally. Each archetype is useful in each domain. No domain is served by fewer than four archetypes. Gate passes.

---

## Open questions (carried forward from FOUNDATIONS v6.0)

1. **Does a sixth archetype emerge at scale?** FOUNDATIONS v6.0 Open Question 2 flagged "Alerts as distinct from Queue." Current read: Alerts are a Queue variant with a time-urgency weight — no structural distinction. If operators with high alert volume emerge and the Queue's resolution affordance (approve/reject/defer) doesn't map (e.g., "acknowledge" only), a sixth archetype may be warranted. Defer until observed.

2. **Archetype composition.** When a nav tab hosts multiple archetypes (Work tab: Document + Stream + Dashboard), what governs the visual composition? Today this is surface-architecture detail. ADR-198 is silent on composition; individual surface ADRs own it.

3. **Cross-archetype navigation.** Briefing's pointer-based discipline (B2) means the Briefing email contains links to Documents and Dashboards. Under what URL conventions? Today: `{app_url}/context?path=…` works. As surfaces diversify, a surface-archetype URL-space ADR may be warranted. Defer.

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-20 | v1 — Initial draft. Five surface archetypes (Document / Dashboard / Queue / Briefing / Stream) as Channel-dimension cells per FOUNDATIONS v6.0 Axiom 6. Each archetype has invariants under the dimensional model. Not a nav change; ADR-180's four tabs preserved. Forward-referenced by FOUNDATIONS v6.0 Derived Principle 12 and Open Question 2. Cited as prereq by ADR-195 Phase 4 (Briefing), ADR-194 Phase 2b (Queue + Stream). |
