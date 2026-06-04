# Home Component Design — Kernel-Universal vs Program-Specific

> **Renamed 2026-06-04** from `COCKPIT-COMPONENT-DESIGN.md` — the surface is the Home (ADR-312 D1), so the design doc carries the surface's name.
>
> **ADR-312 D2 amendment note (2026-06-04):** the Home's six slots partition by substrate ownership. The **kernel renders the three universal slots itself** — slot #3 Decision queue (`KernelDecisionQueue`, `action_proposals`/ADR-307), slot #5 Recent artifacts (`KernelRecentArtifacts`, delivered outputs), slot #6 Judgment trail (`KernelJudgmentTrail`, `decisions.md`) — for *every* workspace, not via SURFACES.yaml. They live at `web/components/library/kernel-home/` and self-hide when their substrate is empty. The **program declares only the two program-shaped slots** — slot #2 Ground-truth hero + slot #4 Live entities — via `home.program_sections[]`. So "Layer 2" below is no longer 100% program-supplied: it's kernel-universal slots interleaved with program sections. See ADR-312 §"D2 amendment (2026-06-04)".
>
> **ADR-312 D2 amendment #2 note (2026-06-04):** a program declares **exactly two** `home.program_sections` — one ground-truth hero (#2) + one entity list (#4). It may NOT re-render the mandate/autonomy (kernel slot #1), declare more than two sections, or sprawl into a metric stack. The hero answers "**is this working?**" in one plain headline; the entity list answers "**what's in play?**" as a labeled, newest-first list. alpha-author's former four cards (AuthorMandate/Corpus/Voice/Pipeline — which duplicated the kernel mandate AND split "voice accuracy" across two cards) collapsed to `AuthorHero` + `AuthorPieces`. **Plain-language rule:** every operator-facing string reads like macOS, not a workbench — see ADR-312 §"D2 amendment #2" for the vocabulary table. (alpha-trader's 7-section stack is the known exception, reshape deferred to a follow-up.)
>
> **ADR-312 vocabulary note (2026-06-02):** the **cockpit surface renames to Home** (`slug: home`, route `/home`). `CockpitRenderer` → `HomeRenderer`; `CockpitHeader` → `HomeHeader` (the Constitution band, slot #1); the composition key `cockpit:` → `home:`; trader-data routes folded `/api/cockpit/*` → `/api/programs/alpha-trader/*` (pace → kernel `/api/pace`). The `Trader*` program components keep their names — they are the alpha-trader bindings of the Home's slots. The kernel-general "Layer 1 header" described below IS the Constitution band. The substrate-backed 7-section stack (ADR-273) survives verbatim as the program's declared composition. Read "cockpit" below as "Home."
>
> **Status**: Canonical design reference (2026-05-14, v3 — substrate-backed
> 7-section stack per ADR-273; surface renamed Home per ADR-312 D1). Governs
> the visual architecture of the **Home** surface — specifically how
> **kernel-general** (any workspace) components and **program-specific**
> (bundle-supplied, e.g. alpha-trader) components compose on screen.
>
> This doc does NOT replace `docs/architecture/compositor.md` (the seam
> reference) or ADR-225 (the compositor) or ADR-273 (the program-section
> split + substrate-backed expansion).
>
> **v3 changes**: ADR-273 superseded the four-face fallback (MoneyTruthFace,
> PerformanceFace, TrackingFace, MandateFace all deleted). The kernel-general
> layer collapses to `CockpitHeader` + an `UnactivatedCockpitCTA` empty state.
> alpha-trader's program_sections grew from 4 to 7, adding `TraderRegime`,
> `TraderExpectancy`, and `TraderSignals` — all substrate-backed. Components
> now live under `web/components/library/programs/alpha-trader/` per ADR-273
> D1 (kernel/program folder split).
>
> **Implementation history**: Phase A (CockpitHeader) tracked in ADR-243.
> Phase B (program_sections seam) tracked in ADR-243 + ADR-225. Phase C
> (initial 4 trader sections) tracked in ADR-243. ADR-273 Phases 1-8
> (cockpit refactor — folder split, fallback deletion, substrate routes,
> 3 new sections, SURFACES.yaml reorder) tracked in ADR-273.

---

## The two-layer model (v3)

```
┌──────────────────────────────────────────────────────────────────────┐
│ Layer 1 — KERNEL-GENERAL (CockpitHeader, always present)             │
│                                                                      │
│   Title: {mandate-based title}        autonomy mode: [link]          │
│                                                                      │
│   {mandate-based summary paragraph}                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ Layer 2 — PROGRAM-SPECIFIC (program_sections OR UnactivatedCockpitCTA)│
│                                                                      │
│   When program_sections declared (active bundle):                    │
│     ordered stack of named components, no kernel chrome between them │
│                                                                      │
│   When no program_sections declared (never-activated workspace):     │
│     UnactivatedCockpitCTA deep-linking to Settings → Workspace       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Layer 1 — `CockpitHeader` (kernel-general, always rendered)**
- Mandate title + summary: derived from `/workspace/context/_shared/MANDATE.md`
- Autonomy posture: derived from `/workspace/context/_shared/_autonomy.yaml` (ADR-254)
- Applies to every workspace regardless of active program
- Visual style: clean, prose-weight, page-header shape (NOT a card)

**Layer 2 — Program-specific sections OR UnactivatedCockpitCTA**
- When `program_sections` declared in `SURFACES.yaml`: ordered stack of named
  components, each a discrete section, rendered by `dispatchComponent({kind})`
  via the universal LIBRARY_COMPONENTS registry.
- When no program is activated (no SURFACES, no program_sections): renders
  `UnactivatedCockpitCTA` — deep-link to Settings → Workspace.
- Bundles cannot mix the two: it's program_sections XOR the CTA. No four-face
  fallback (deleted in ADR-273 Phase 2).

**Singular implementation rules (ADR-273 D1 + D2)**:
- Kernel-general components live at `web/components/library/` root.
- Program-specific components live at `web/components/library/programs/{slug}/`.
- Registry is one flat dict keyed by `kind`; folder location is filesystem
  signal, not registry namespacing.
- The deleted four-face fallback (MoneyTruthFace / PerformanceFace /
  TrackingFace / MandateFace) does not return. Never-activated workspaces
  see CockpitHeader + UnactivatedCockpitCTA, full stop.

---

## Composability model — why multiple stacked sections, not one block

The program layer is a **declared ordered list of named components**, not a monolithic bundle. This gives three properties:

1. **Reorderable**: operator edits `order` field in SURFACES.yaml (or asks YARNNN to) → sections reorder without code changes
2. **Collapsible**: removing a section from `program_sections[]` hides it — no bundle code change
3. **Additive**: new section types register in `LIBRARY_COMPONENTS` and declare themselves in SURFACES.yaml — existing sections unchanged (ADR-222 Principle 16)

**SURFACES.yaml declaration (alpha-trader)**:

```yaml
cockpit:
  program_sections:
    - kind: TraderPortfolio
      order: 1
    - kind: TraderBalances
      order: 2
    - kind: TraderPositions
      order: 3
    - kind: TraderOrders
      order: 4
```

**CockpitRenderer processing**:

```
GET /api/programs/surfaces
  → cockpit.program_sections (sorted by order)
  → render CockpitHeader (always, Layer 1)
  → for each section in sorted program_sections:
      dispatch through LIBRARY_COMPONENTS[section.kind]
```

No `program_sections` in the workspace's composition → CockpitRenderer falls through to the four kernel-default faces (current behavior). This preserves backward compatibility.

---

## Layer 1 — CockpitHeader visual contract

**Component**: `web/components/library/CockpitHeader.tsx`
**Always rendered**: yes — no bundle override.
**Replaces**: the current `MandateFace` card (which stays as a fallback-face but is not the cockpit header).

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  {mandate title}                         Autonomy: {level} [→ edit]    │
│                                                                         │
│  {mandate summary — first prose paragraph, stripped of headings/meta}  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

Visual rules:
- Full width, no card border
- Subtle background (`bg-muted/10` or transparent — context-dependent)
- Title: `text-2xl font-semibold` — same weight as a surface title
- Mandate summary: `text-sm text-muted-foreground` — up to 3 lines, prose weight
- Autonomy posture: top-right corner, `text-xs`, links to `/agents?agent=thinking-partner&tab=autonomy`
  - `manual` → muted text, no icon
  - `assisted` → muted text + info icon
  - `bounded_autonomous` → amber text + shield icon
  - `autonomous` → primary text + shield icon
- Skeleton state (MANDATE.md absent or kernel-default placeholder): CTA prompt "Define your mandate in chat" — same amber/dashed visual as current MandateFace skeleton

**Substrate reads**:
- `/workspace/context/_shared/MANDATE.md` → title + summary extraction
- `/workspace/context/_shared/AUTONOMY.md` → level + ceiling (via `useAutonomy()` from `@/lib/autonomy`)

---

## Layer 2 — alpha-trader sections (v3, 7 sections)

The dashboard tells a story top-to-bottom: tape → account → balances →
tenure → live state → today's decisions → ledger. Each section builds
on the prior. Operator can reorder by editing `order` values in
SURFACES.yaml or asking YARNNN to.

### 1. TraderRegime (order: 1) — tape headline

**Data**: `api.cockpit.regime()` → `/workspace/context/trading/_regime.yaml`
(written by TrackRegime primitive, ADR-271 Thread A).

Thin one-line strip. Three tones:
- **Risk-on** (emerald) — SPY uptrend + VIX quiet
- **Risk-off** (amber) — SPY downtrend OR VIX active
- **Neutral** (slate) — everything else

Empty state: "Regime tracker hasn't fired yet — paused or first run pending."

### 2. TraderPortfolio (order: 2) — equity chart + headline

**Data**: `api.cockpit.portfolioHistory()` + `api.cockpit.moneyTruth()`

Headline equity + day Δ pct + paper/live badge + SVG sparkline. Period
toggle (1D / 1M / 1Y / All). Canonical not-connected surface for the
alpha-trader stack (other sections suppress not-connected to avoid dup).

### 3. TraderMoneyTruth (order: 3) — live balances

**Data**: `api.cockpit.moneyTruth()`

3-column grid: equity (with day Δ) · buying power (with cash subtitle) ·
positions count. Returns null when live=false (TraderPortfolio surfaces
the canonical not-connected state).

### 4. TraderExpectancy (order: 4) — accumulated per-signal P&L (ADR-273)

**Data**: `api.cockpit.moneyTruth().by_signal` — reads `_money_truth.md`
frontmatter `by_signal` block (written by `services/outcomes/ledger.py`
per ADR-195). No new endpoint — reuses moneyTruth route.

Table sorted by abs(cumulative). Columns: signal · count · win rate ·
cumulative · 7d/30d/90d rolling. All dollar amounts color-coded.

Recovers signal that lived in deleted MoneyTruthFace (ADR-273 Phase 2).

Empty state: "No reconciled outcomes yet — reconciliation runs daily at
05:00 UTC."

### 5. TraderPositions (order: 5) — live positions + substrate merge (ADR-273)

**Data**: `api.cockpit.positions()` + `api.cockpit.indicators(ticker)`
per row.

Live Alpaca position table merged with per-ticker indicators from
TrackUniverse substrate (`/workspace/context/trading/{TICKER}.yaml`).
Columns: symbol · qty · market value · unrealized P/L · **trend badge**
(SMA50 vs SMA200) · **suggested stop** (price − 2× ATR).

Trend + stop columns degrade gracefully — when indicators absent for
a ticker, row renders without enrichment.

### 6. TraderSignals (order: 6) — today's signals + reviewer trail (ADR-273)

**Data**: `api.cockpit.signals(10)` →
`/workspace/context/trading/signals/*.yaml` listed newest-first +
best-effort correlation against `/workspace/review/judgment_log.md`.

Collapsible list. Header row: ticker · direction · expectancy · verdict
badge (approved/rejected/deferred). Expand: signal rationale + reviewer
reasoning excerpt + source-file deep-link.

Closes the gap between "signal evaluator fires a proposal" and
"operator sees what was evaluated and what the Reviewer said about it."

Empty state: "No signals evaluated yet. Signal evaluator runs at
market open."

### 7. TraderOrders (order: 7) — recent orders ledger

**Data**: `api.cockpit.recentOrders(10)` → Alpaca `/v2/orders`

Asset · order type · side · qty · avg fill · status · submitted-at.
Returns null when Alpaca not connected.

---

## Layout orchestration — CockpitRenderer (post-ADR-273)

```
CockpitRenderer
├── CockpitHeader          (always; kernel-general; mandate + autonomy)
└── if program_sections declared in composition:
│   └── for each section (sorted by order):
│       └── dispatchComponent({ kind })
└── else (no program activated):
    └── UnactivatedCockpitCTA (deep-link to /settings?tab=workspace)
```

No four-face fallback. The deleted MoneyTruthFace / PerformanceFace /
TrackingFace / MandateFace are gone per ADR-273 Phase 2; their dead-code
status is preserved only as historical comments in the registry and
deleted-file mentions in TraderMoneyTruth's docstring trail.

---

## Implementation history

**Phase A — CockpitHeader (ADR-243 Phase A, 2026-05-01)**
- `web/components/library/CockpitHeader.tsx`
- Reads MANDATE.md + uses `useAutonomy()` (ADR-238 hook)

**Phase B — program_sections compositor (ADR-243 Phase B, 2026-05-01)**
- `web/lib/compositor/types.ts` + `resolver.ts` (`getProgramSections`)
- `api/services/composition_resolver.py` passthrough
- CockpitRenderer: program_sections takes precedence over four-face

**Phase C — Initial 4 trader sections (ADR-243 Phase C, 2026-05-01)**
- `TraderPortfolio` + `TraderMoneyTruth` + `TraderPositions` + `TraderOrders`
- Backend: `/api/cockpit/portfolio-history` + `/positions` + `/recent-orders`

**ADR-273 — Cockpit refactor (2026-05-14)**
- Phase 1: kernel/program folder split — Trader* → `programs/alpha-trader/`
- Phase 2: deleted 4 fallback faces, added `UnactivatedCockpitCTA`
- Phase 3: 3 new backend routes (`/regime`, `/indicators`, `/signals`)
- Phase 4: rewrote 4 existing components (TraderPositions substrate-merged)
- Phase 5: 3 new sections (`TraderRegime`, `TraderExpectancy`, `TraderSignals`)
- Phase 6: SURFACES.yaml reordered to 7-section stack
- Phase 7: design doc updates (this doc → v3) + library README v2 + CLAUDE.md ADR-273 entry

---

## Relationship to existing docs + ADRs

| Doc | Relationship |
|---|---|
| `docs/architecture/compositor.md` | Seam reference. `program_sections` extends the compositor. No change to the core dispatch pattern. |
| ADR-225 | The compositor itself — surface manifest spec + composition resolver. Unchanged. |
| ADR-228 | Original four-face model. **Superseded by ADR-273** for the kernel-default fallback path. The fixed-Layer-1-`CockpitHeader` + ordered-Layer-2-stack pattern from ADR-243 + ADR-273 survives. |
| ADR-242 | Initial trader components (`TraderMoneyTruth`, `TraderPositions`) as face-dispatch overrides. Folded into `program_sections` by ADR-243 Phase C and rewritten by ADR-273 Phase 4. |
| ADR-243 | Cockpit header + program_sections seam + initial 4 trader sections. |
| ADR-273 | Folder split + fallback deletion + 3 new substrate-backed sections (Regime, Expectancy, Signals) + 7-section ordering. This doc → v3. |
| ADR-238 | `useAutonomy()` hook consumed by CockpitHeader. Unchanged. |
| `web/components/library/README.md` | Component registry discipline + folder convention (v2 reflects programs/ subdir per ADR-273 D1). |
