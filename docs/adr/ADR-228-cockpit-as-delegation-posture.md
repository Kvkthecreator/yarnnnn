# ADR-228: Cockpit as Operation — Four Faces of an Operating Workspace

> **Status:** **Commits 1, 2, and substrate-stub follow-up Implemented 2026-04-28**.
> Commit 1: four-face component scaffolds + kernel cockpit replacement + eleven legacy components deleted + alpha-trader `SURFACES.yaml` migrated to `cockpit:` block.
> Commit 2: trader detail middles removed from `SURFACES.yaml`. The bundle-shaped specifics for trader (positions, risk, performance attribution, proposal queue) live inside the cockpit's four faces — that is where the operator runs the operation. /work detail mode is forensics ("show me the latest output"); kernel-default `DeliverableMiddle` handles `portfolio-review` and `trading-signal` the same as every other `produces_deliverable` task.
> **Substrate-stub follow-up (post-Commit-2 cockpit audit, 2026-04-28)**: a visual review of the four faces against kvk's live workspace surfaced 404s on `MANDATE.md`, `AUTONOMY.md`, `_performance.md`, `decisions.md`. An upstream-substrate audit (see "Substrate-stub audit" section below) traced each 404 to its writer. The audit recommended one in-code fix and one operational fix:
> · **In-code (this commit):** `services/outcomes/ledger.py::fold_outcome_candidates` now writes an empty `_performance.md` stub via `_init_performance` when called with `candidates=[]` AND no `_performance.md` exists yet for the domain. After this change, a 404 on `_performance.md` post-task-execution unambiguously means "back-office task hasn't run yet" rather than "ran but no candidates." Closes the ambiguity ADR-228 D4 raised about the cockpit's MoneyTruth/Performance face empty-state distinguishing capability.
> · **Operational (out of scope for this commit):** kvk's `MANDATE.md` is still the kernel-default skeleton because no one has invoked `POST /api/programs/activate` for kvk's workspace yet — the activation FE is ADR-226 Phase 2 (deferred). Until that ships, the bundle template fork for new alpha-trader operators happens via manual API call. The fork logic itself is correct (verified against the bundle's reference-workspace at `docs/programs/alpha-trader/reference-workspace/context/_shared/MANDATE.md` carrying `tier: authored` frontmatter); the gap is the activation surface, not the fork code.
> · **Reviewer audit (`decisions.md`)**: confirmed by-design — the writer (`services/reviewer_audit.py::append_decision`) is wired correctly via `services/review_proposal_dispatch.py::on_proposal_created`. kvk's workspace has zero `action_proposals`, so the file legitimately doesn't exist yet. Empty-state UI in `PerformanceFace` already renders correctly ("Reviewer scaffolded · No decisions yet").
> · **Cross-domain `_performance_summary.md`**: confirmed already-correct — `services/outcomes/ledger.py::write_performance_summary` writes an empty stub on every reconciliation run regardless of per-domain content. No fix needed.
> Commits 3-5 (`MoneyTruth` platform-live binding via `/api/cockpit/money-truth/{user_id}`, `PerformanceFace` sub-metrics, `TrackingFace` operational-state bundle wiring, final doc sync) deferred to subsequent sessions.
> **Authors:** KVK, Claude
> **Supersedes:** ADR-225 cockpit composition — `KERNEL_DEFAULT_COCKPIT_PANES` flat sequence, the six-question pane registry, the assumption that the cockpit is a stack of axis-shaped panes.
> **Depends on:** ADR-217 (AUTONOMY.md), ADR-207 (MANDATE.md), ADR-194 v2 (Reviewer), ADR-195 v2 (money-truth substrate), ADR-187 (trading platform integration), ADR-219 (narrative substrate), ADR-209 (authored substrate), ADR-222 (OS framing — bundle-shaped surfaces)
> **Related:** ADR-225 (compositor seam — the dispatch mechanism this ADR consumes; ADR-225's cockpit reshape section is replaced by this ADR)

---

## Context

The cockpit shipped today (ADR-225, 2026-04-28 morning) renders six panes mapped to six "questions an operator asks of a delegation product." Walked against the alpha-trader workspace, the cockpit fails to convey what the operator actually walked up to read:

> *Looking at this screen I cannot answer what we're trying to achieve, how we're doing, what mode we're in, what's being done, or how it's performing.*

The discourse around this failure surfaced the deeper diagnostic. The six-question framing treated the cockpit as a **dashboard of substrate axes** — six things substrate has, six panes that read them. But for an operator running a workspace, the cockpit is not a dashboard *about* delegation. The cockpit is **the operation itself, rendered.**

A useful comparison: the Alpaca brokerage screen the operator runs alongside this cockpit. That screen has portfolio chart, balances, positions, recent orders, trade panel. It does not ask "what are the six questions a trader has." It says *here is your account, here is what's in it, here is how to act.* It renders the **subject** of operation — the brokerage account — as itself. There is no posture machine, no trust state, no delegation read. The screen is the thing.

The YARNNN cockpit is the same shape with one difference: the operation here is *agent-driven*, so the operator's view includes what the team is doing on their behalf. But the underlying frame is identical — **render the operation as itself, not as a meta-read about it.**

## The four faces of an operation

Every operating workspace has four legibility surfaces. They are categorically different from each other — not axes of one substrate, but four faces of the same operation seen from four directions:

| Face | Question it answers | Time-shape | Source class |
|---|---|---|---|
| **Mandate** | What is this workspace *for*? | Standing | Authored substrate (`MANDATE.md`, `AUTONOMY.md`) |
| **Money truth** | Where does the account stand *right now*? | Live | Platform live + substrate fallback |
| **Performance** | How is the operation doing against the mandate? | Historical, attributed | Outcome substrate (`_performance.md`, `decisions.md`) |
| **Tracking** | What is in motion right now? | Live operational | Pending proposals, open positions, fresh signals, recent activity |

These four faces are **the cockpit**. Not panes selected from a list. Not axes of a substrate map. The cockpit *is* the operation, and an operation is exactly these four faces.

Trust violations live inside **Mandate** (they are breaches of standing intent) and **Performance** (they are how we're doing on rule compliance). Reviewer health lives inside **Performance**. Outcome stream lives inside **Tracking**. NeedsMe / proposal queue lives inside **Tracking**. The six panes that ADR-225 introduced are not deleted-as-information — they are reorganized into the four faces where the information *belongs*.

## Decision

### D1 — The cockpit renders four faces, in fixed order

The cockpit is a vertical render of four faces. Order is fixed and not bundle-overridable:

```
1. Mandate         — what we're trying to do, with what permissions
2. Money truth     — where the account stands right now
3. Performance     — how we're doing against the mandate
4. Tracking        — what's in motion
```

Order is structural: you cannot read performance without knowing what was being attempted (Mandate first); you cannot read what's in motion without knowing the ground truth state (Money Truth before Tracking). The order encodes the operator's reading sequence.

### D2 — Each face has a kernel contract and a bundle override

Each face is one component with a defined data contract. Bundles override what fills the face for their domain — but cannot change which faces exist or their order.

| Face | Component | Kernel contract | Bundle override surface |
|---|---|---|---|
| Mandate | `MandateFace` | Reads `MANDATE.md` + `AUTONOMY.md`. Renders standing intent (one paragraph from MANDATE) + autonomy posture (phase + autonomy level + budget headroom). When MANDATE absent or skeleton: destructive-tinted authoring CTA. Open trust violations promoted into this face as "mandate breaches." | Bundle declares which authored-substrate files to read, how to format autonomy summary, how to label the operating phase. |
| Money truth | `MoneyTruthFace` | Live-source-first. Bundle declares the live binding (e.g., Alpaca account snapshot for trader, Lemon Squeezy snapshot for commerce). Substrate fallback (`_performance.md`) when live unavailable. Empty state when both absent. Renders the **live state of the account**: balance/equity, buying power, day delta, drawdown, key constraints. Visual shape mirrors a brokerage / commerce dashboard summary, not a card grid. | Bundle declares live source, fields, and visual layout (trading-shaped vs commerce-shaped vs other). |
| Performance | `PerformanceFace` | Reads outcome substrate (`_performance.md` body + `decisions.md`). Renders attribution against the mandate: how the operation is doing on the things mandate said it would do. Includes Reviewer calibration (approve/reject ratio, agreement-with-operator), agent confidence trend, signal accuracy where defined. | Bundle declares attribution metrics (signal-by-signal expectancy for trader, conversion-by-channel for commerce), and which sub-metrics roll up into the face. |
| Tracking | `TrackingFace` | Renders what is in motion right now: pending proposals (with approve/reject actions), recent outcome events (fills, closes, decisions — not task-run deliveries), open operational state (positions, active campaigns, watchlist freshness). | Bundle declares operational state shape (positions table for trader, active campaigns for commerce), outcome event whitelist, and proposal envelope. |

### D3 — The library shrinks to four face components

The current library has six pane components from ADR-225 (`MandateStrip`, `MoneyTruthTile`, `KernelNeedsMePane`, `MaterialNarrativeStrip`, `TrustViolations`, `TeamHealthCard`) plus alpha-trader-specific (`TradingProposalQueue`, `PerformanceSnapshot`, `PositionsTable`, `RiskBudgetGauge`, `TradingPortfolioMetadata`).

After this ADR the cockpit-side library is:

```
web/components/library/
  faces/
    MandateFace.tsx
    MoneyTruthFace.tsx
    PerformanceFace.tsx
    TrackingFace.tsx
```

These are **dense, opinionated faces**, not generic primitives. Each face is rich enough to render the operating subject without composition by the host page — the cockpit is `<MandateFace /> <MoneyTruthFace /> <PerformanceFace /> <TrackingFace />` and that's it.

Inside each face, the bundle declares the substrate bindings and visual shape. A face is allowed to be substantial — `MoneyTruthFace` for trader is a balance + chart + buying power summary (Alpaca-shaped); for commerce it's MRR + net new customers + churn (Lemon-shaped). The face is bundle-aware, not bundle-agnostic.

The six ADR-225 pane components, the trader-specific dashboard components, and any other axis-shaped components from ADR-225 Phase 3 are **deleted**. Their information is reorganized into the four faces. There is no compatibility shim, no parallel registry.

### D4 — Bundle override is per-face, declared in `SURFACES.yaml`

```yaml
cockpit:
  mandate:
    sources:
      mandate: /workspace/context/_shared/MANDATE.md
      autonomy: /workspace/context/_shared/AUTONOMY.md
    autonomy_summary: trader_summary    # named formatter in bundle
  money_truth:
    live_source:
      kind: platform
      platform: trading
      fields: [equity, buying_power, day_pnl, drawdown_pct, positions_count]
    substrate_fallback: /workspace/context/portfolio/_performance.md
    layout: trading_account              # named visual layout
  performance:
    attribution_source: /workspace/context/portfolio/_performance.md
    sub_metrics: [signal_accuracy, expectancy_by_signal, reviewer_calibration]
  tracking:
    proposal_filter:
      proposal_type: trading
      status: pending
    outcome_events: [position_opened, position_closed, stop_triggered,
                     proposal_approved, proposal_rejected, reviewer_decision]
    operational_state:
      kind: positions_table
      source: /workspace/context/portfolio/_positions.md
```

Bundles cannot declare a fifth face. They cannot reorder the four. They cannot replace a face with a different component shape. Override is scoped strictly to **what fills each face for this operation's domain**.

The current alpha-trader `cockpit_panes:` array (six-pane sequence) is replaced by the `cockpit:` block above in the same commit that lands this ADR's code. No dual schema.

### D5 — `MoneyTruthFace` is platform-live where a platform exists

For delegation products with a connected platform that holds ground-truth account state (trading via ADR-187, commerce via ADR-183), the live source is the platform, not a reconciled substrate file. The cockpit calls a thin server endpoint that proxies the platform with a 60-second cache. Substrate fallback exists for cold-start and unreachable-platform cases, with a `· last reconciled {ts}` suffix when fallback rendered.

This is the load-bearing piece of the alpaca-comparison: the operator should see *what the broker says now*, not what was reconciled last cycle. For a trading workspace `MoneyTruthFace` reads Alpaca account + positions + recent orders. For a commerce workspace it reads the active commerce provider. For workspaces without a connected platform, substrate is the source of record and the face renders the `_performance.md` snapshot directly.

### D6 — `PerformanceFace` is attribution against the mandate, not a metric grid

The face is opinionated about its read: *how is the operation doing at the things MANDATE said it would do*. For alpha-trader: signal expectancy, accuracy by signal type, drawdown vs. limit, Reviewer agreement rate. For alpha-commerce: conversion by channel, churn vs. target, customer lifetime value vs. CAC.

The face takes its attribution targets from the bundle's MANIFEST (which knows the domain's success metrics) and renders against `_performance.md` body + `decisions.md` parsed for Reviewer calibration. Sub-metrics are bundle-declared; the face's structural shape (mandate-attributed performance) is universal.

### D7 — `TrackingFace` renders motion, filtered to outcomes

The face shows what is in motion right now. Three regions inside the face:

- **Pending decisions** — proposal queue with approve/reject actions inline (this absorbs `KernelNeedsMePane` / `TradingProposalQueue`)
- **Operational state** — positions, active campaigns, watchlist freshness (bundle-shaped table)
- **Recent activity** — outcome events only, filtered per D5 of the prior draft (fills, closes, decisions, approvals/rejections; never task-run delivery events)

These are not three sub-panes that the bundle composes individually — they are three regions of one face component, each region bundle-fed via the SURFACES.yaml `tracking:` block.

### D8 — The `/work` list zone stays

The cockpit is the top zone of `/work`. Below it the existing `WorkListSurface` (My Work / Connectors / System tabs) stays unchanged. The cockpit answers "show me the operation"; the list answers "let me find a specific task." Different reads, both kept.

---

## Why four faces and not five or three

**Three** would be Mandate · Money truth · Tracking — collapsing Performance into either Mandate (your contract includes how you're doing on it) or Tracking (recent outcomes are performance). Neither holds: performance is *historical attribution* (cumulative truth about how the operation has done), distinct from standing intent (Mandate) and present motion (Tracking). Operators read it on a different time-shape.

**Five** would add a separate Trust face. Trust is real concern but it is *attribution about the system's reliability* — which is performance. Reviewer agreement rate is a performance metric of the Reviewer. Open trust violations are mandate breaches surfaced into Mandate. There is no fifth face that doesn't decompose into the existing four.

The four are exhaustive and mutually distinct. Every cockpit-relevant signal lives in exactly one face. This is the test: if a piece of information cannot be placed cleanly in one of the four, the framing is wrong, not the information.

---

## Singular implementation

| Deleted | Replaced by |
|---|---|
| `KERNEL_DEFAULT_COCKPIT_PANES` array in `web/lib/compositor/kernel-defaults.ts` | `KERNEL_COCKPIT_FACES` (the four-face structural list) — but since faces are not bundle-overridable in shape, this is mostly for documentation; the renderer can hardcode the four imports |
| `tabs.work.list.cockpit_panes` SURFACES.yaml key | `cockpit:` block per D4 |
| `MandateStrip`, `MoneyTruthTile`, `KernelNeedsMePane`, `MaterialNarrativeStrip`, `TrustViolations`, `TeamHealthCard` | Information reorganized into `MandateFace`, `MoneyTruthFace`, `PerformanceFace`, `TrackingFace`. Component files deleted. |
| `TradingProposalQueue`, `PerformanceSnapshot`, `PositionsTable`, `RiskBudgetGauge`, `TradingPortfolioMetadata` (alpha-trader-specific cockpit components) | Their rendering merges into the four bundle-aware faces. Trading-shaped MoneyTruthFace and TrackingFace replace these. Component files deleted. |
| `CockpitRenderer.tsx` flat-pane dispatch + section header chrome | `CockpitRenderer` renders `<MandateFace />` `<MoneyTruthFace />` `<PerformanceFace />` `<TrackingFace />` directly. Section-header chrome ("COCKPIT · what needs you · book · since last look · intelligence") deleted; faces have their own headers. |
| Compositor library's pane registry concept *for the cockpit* | Faces are imported directly. The compositor seam (`MiddleResolver`, `ChromeRenderer`, `BundleBanner` for `/work` detail and list-mode banner) stays exactly as ADR-225 left it — those layers are not affected. |

The ADR-225 compositor seam survives. Only the cockpit-side composition (which was a flat pane-list dispatch) is replaced. Detail-mode middle resolution, chrome resolution, list-mode banner — all unchanged.

---

## Implementation plan (after ratification)

Atomic commits, each green-state.

### Commit 1 — Four-face component scaffolds + kernel cockpit replacement

- Create `web/components/library/faces/{MandateFace,MoneyTruthFace,PerformanceFace,TrackingFace}.tsx` with kernel-default rendering.
- Replace `CockpitRenderer.tsx` body with the four-face render.
- Delete `web/components/library/{MandateStrip,MoneyTruthTile,TrustViolations,MaterialNarrativeStrip,TeamHealthCard}.tsx`.
- Delete `web/components/library/kernel-cockpit/KernelNeedsMePane.tsx`.
- Delete `KERNEL_DEFAULT_COCKPIT_PANES` from `kernel-defaults.ts`.
- Delete `resolveCockpitPanes` from `web/lib/compositor/resolver.ts`.
- Update `web/components/library/registry.tsx` to remove deleted-pane dispatch entries.
- Test gate: `web/test/cockpit-faces.test.ts` covers the four faces rendering against an empty-state fixture and a populated fixture.

### Commit 2 — SURFACES.yaml schema bump + alpha-trader migration

- Replace `tabs.work.list.cockpit_panes` schema with `cockpit:` block in `docs/adr/ADR-223` schema reference.
- Update `docs/programs/alpha-trader/SURFACES.yaml` to the new shape with `mandate / money_truth / performance / tracking` sub-blocks.
- Delete the `cockpit_panes:` block from alpha-trader's manifest in the same commit.
- Delete the trader-specific cockpit component files (`TradingProposalQueue`, `PerformanceSnapshot`, `PositionsTable`, `RiskBudgetGauge`, `TradingPortfolioMetadata`) — their rendering now lives inside the four faces' trader-bundle binding.
- Update `composition_resolver.py` to parse `cockpit:` block; delete `cockpit_panes` parsing.

### Commit 3 — `MoneyTruthFace` platform-live binding

- Add `/api/cockpit/money-truth/{workspace_id}` endpoint with bundle-driven dispatch (trading → Alpaca account+positions, commerce → LS provider, none → substrate).
- 60s server-side cache.
- Wire `MoneyTruthFace` to the endpoint with substrate fallback and freshness suffix.
- Test gate: `api/test_adr228_money_truth.py` covers live-trader, fallback, and empty paths.

### Commit 4 — `PerformanceFace` attribution + `TrackingFace` outcome filter

- `PerformanceFace`: read `_performance.md` body + parse `decisions.md` for Reviewer calibration. Bundle-declared sub-metrics inject into the face.
- `TrackingFace`: three regions (pending decisions / operational state / recent activity), each bundle-fed. Outcome event whitelist replaces task-run delivery feed.
- Add `/api/cockpit/performance/{workspace_id}` and `/api/cockpit/tracking/{workspace_id}` if needed for non-trivial reads (or render directly from existing endpoints if substrate read is enough).

### Commit 5 — Doc sync

- Mark ADR-225 cockpit reshape section as **Superseded by ADR-228** at the top of that section.
- Update `docs/architecture/SERVICE-MODEL.md` Frame 5 (compositor row).
- Update `docs/programs/alpha-trader/MANIFEST.yaml` references if any cockpit-pane keys are mentioned.
- Update CLAUDE.md ADR-225 entry with "cockpit reshape superseded by ADR-228 four-face model" note.
- Update `web/components/library/README.md` to document the four faces and the bundle override surface.

---

## Test coverage

| Test | What it locks |
|---|---|
| `cockpit-faces.test.ts` (FE unit) | Each of the four faces renders for empty, partial, and populated substrate fixtures. Order is fixed (Mandate → Money truth → Performance → Tracking). |
| `test_adr228_money_truth.py` (API) | Live-platform path returns provider-shaped data; fallback path reads substrate; empty-state when both absent. Trader and commerce bundles both pass. |
| `test_adr228_surfaces_schema.py` (API) | New `cockpit:` schema parses cleanly; old `cockpit_panes:` schema rejected (no shim). Alpha-trader manifest validates. |
| `web/e2e/cockpit-operation.spec.ts` (Playwright) | Walking the alpha-trader cockpit: each face renders with the operator's actual operating data, no orphan empty states, no rendering of deleted pane components. |
| Grep gate | Zero references to deleted pane component names anywhere in `web/`, `docs/`, or `api/`. |

---

## Consequences

**Conceptual.** The cockpit is no longer a "delegation status read" or a "six-question dashboard." It is **the operation**. The four faces are how an operator sees their own operation regardless of domain. Bundles fill the faces with domain shape. The kernel guarantees the four faces exist, in order, with defined contracts.

**Library.** Six axis-shaped pane components and five trader-specific cockpit components delete. Four dense, opinionated face components ship. The library halves in size on the cockpit side; what remains is denser per component.

**Bundle surface.** Bundle authors think in faces, not panes. "What does Mandate look like for a content-ops workspace? What does Money Truth look like when there's no platform?" These are the design questions. The fixed four-face structure gives bundle authors a clean target: fill four faces with your domain's shape.

**What we accept.** Faces are larger components than panes were. Each face is responsible for a non-trivial slab of the cockpit. We accept this tradeoff: it's better to have four well-shaped components than nine loose ones, because the cockpit reads *as one thing* for the operator and the component shapes should match the user's reading shape.

**What we don't accept.** A "and a fifth face for X" addition request without superseding this ADR. The four faces are the structural commitment. New information goes inside an existing face or its placement is wrong.

---

## Open questions

1. **Does Mandate face merge autonomy more deeply or keep it as a sub-line?** Initial design: autonomy renders as one tight line under standing intent (`Phase 0 — Observation · Bounded autonomy on paper · $100/$500 day budget remaining`). If usage shows operators wanting deeper autonomy interaction (review per-domain ceilings, see violation history), we promote autonomy to a sub-section of Mandate. Out of scope for this ADR; revisit on operator feedback.

2. **Where does the chat-chip surface live?** ADR-225 had `chat_chips` at the SURFACES.yaml top level. This ADR doesn't touch them; they continue rendering wherever ADR-225 placed them.

3. **Does the cockpit also live on `/chat`?** Currently `/work` is the cockpit's home. For an operator who lives in chat, the four-face read might also belong as the empty state of `/chat` or a pinned card at the top. Out of scope for this ADR; revisit when the cockpit's surface placement is reviewed in another ADR.

---

## Why this is the right shape

The Alpaca screen comparison is the load-bearing intuition. That product knows it is **the trading account**, rendered. Not "six questions about a brokerage." Not "delegation status of your trading activity." *The trading account, as itself, where you can see it and act on it.*

The YARNNN cockpit for an alpha-trader operator is the same kind of thing: the *operation*, rendered, where you can see it and act on it. The fact that the operation is agent-driven means the rendering also includes pending decisions and recent agent outcomes — but those are *part of the operation*, not a meta-layer about it.

Four faces — Mandate, Money truth, Performance, Tracking — is the structural answer to "how do you render an operation." It is bundle-shaped (each face fills with the domain's actual data), kernel-guaranteed (the four exist, in order), and operator-legible (the four match how operators think about running a thing).

The six panes were a tool's vocabulary. Four faces are the operator's vocabulary. The cockpit should speak the operator's vocabulary.

---

## Related

- ADR-225 — Compositor seam (preserved; cockpit composition section superseded by this ADR)
- ADR-217 — AUTONOMY.md (Mandate face source)
- ADR-207 — MANDATE.md (Mandate face source)
- ADR-194 v2 — Reviewer (Performance face source for calibration)
- ADR-195 v2 — Money-truth substrate (Money truth face fallback)
- ADR-187 — Trading integration (Money truth face live source for trader)
- ADR-198 — Surface archetypes (cockpit is operation-rendered, archetype-agnostic at this level)
- FOUNDATIONS Axiom 3 (Purpose) + Axiom 6 (Channel) — the cockpit is Purpose × Channel composite where Channel is "operator's primary operating surface"
