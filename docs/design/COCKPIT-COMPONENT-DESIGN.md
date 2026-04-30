# Cockpit Component Design — Common vs Program-Specific

> **Status**: Canonical design reference (2026-05-01, v2 — program_sections
> model). Governs the visual architecture of the `/work` cockpit zone —
> specifically how **common** (kernel-default, any workspace) components and
> **program-specific** (bundle-supplied, e.g. alpha-trader) components compose
> on screen.
>
> This doc does NOT replace `docs/architecture/compositor.md` (the seam
> reference) or ADR-228 (the four-face model). It adds the visual design layer
> those docs omit.
>
> **Implementation**: Phase A (CockpitHeader) tracked in ADR-243.

---

## The two-layer model

The operator sketch that drove this document showed a clear two-layer page
structure:

```
┌──────────────────────────────────────────────────────────────────────┐
│ COMMON - PAGE HEADER (Layer 1, always present)                       │
│                                                                      │
│   Title: {mandate-based title}        autonomy mode: [toggle]        │
│                                                                      │
│   {mandate-based summary paragraph}                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ PROJECT SPECIFIC (Layer 2, bundle-supplied, stacked sections)        │
│                                                                      │
│   Section 1 (order: 1) — e.g. TraderPortfolio                       │
│   Section 2 (order: 2) — e.g. TraderBalances                        │
│   Section 3 (order: 3) — e.g. TraderPositions                       │
│   Section 4 (order: 4) — e.g. TraderOrders                          │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Layer 1 — Common (kernel-default, always present)**
- Mandate-based title and summary: derived from `/workspace/context/_shared/MANDATE.md`
- Autonomy mode indicator + toggle: derived from `/workspace/context/_shared/AUTONOMY.md`
- Applies to every workspace regardless of active program
- Visual style: clean, prose-weight, page-header shape (NOT a card)

**Layer 2 — Program-specific (bundle-supplied, ordered stack of named sections)**
- Multiple independent named components, each a discrete section
- Declared in SURFACES.yaml as `cockpit.program_sections[]` with an `order` field
- Order controls display sequence; operator (or YARNNN) can reorder, hide, or add sections
- For alpha-trader: portfolio chart + balances + positions + recent orders
- For alpha-commerce (future): revenue chart + subscriber summary + product table
- Visual style: data-rich, domain-shaped (trading terminal aesthetic for alpha-trader)

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

## Layer 2 — alpha-trader sections visual contract

### TraderPortfolio (order: 1)

**Data**: `api.cockpit.portfolioHistory()` → Alpaca `/v2/account/portfolio/history` (line chart data) + `api.cockpit.moneyTruth()` (equity headline)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Your portfolio    [1D] [1M] [1Y] [All]  [↻ refresh]     [Watchlist ▸]  │
│ $XX,XXX.xx ↑ +X.X%  · paper                                            │
│ {timestamp} KST                                                         │
│                                                                         │
│ [line chart — equity over selected time period]                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

- Chart: lightweight SVG sparkline or recharts-style line chart. NOT a full Recharts bundle — keep it minimal.
- Paper badge: shown when `paper: true` from moneyTruth response
- Refresh: re-fetches live data

### TraderBalances (order: 2)

**Data**: `api.cockpit.moneyTruth()` (equity, cash, buying_power, day_pnl, day_pnl_pct)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 🗂 Balances                                                        [+]  │
│ Buying Power           Cash                Daily Change                 │
│ $XX,XXX                $XX,XXX             +$XXX (+X.X%) ↑              │
└─────────────────────────────────────────────────────────────────────────┘
```

- 3-column grid, clean labels
- Daily Change: colored (green/red) with trend arrow

### TraderPositions (order: 3)

**Data**: new `api.cockpit.positions()` → Alpaca `/v2/positions`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Top Positions    Asset Class [All ▾]  Side [All ▾]         View All →  │
│ Asset | Price | Qty | Market Value | Total P/L ($)                     │
│                                                                         │
│ [empty: "No open positions. Place some trades."]                        │
└─────────────────────────────────────────────────────────────────────────┘
```

### TraderOrders (order: 4)

**Data**: new `api.cockpit.recentOrders()` → Alpaca `/v2/orders?status=all&limit=10`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Recent Orders                                              View All →   │
│ [Search...]             [Cancel X selected]  [⚙ Columns]               │
│ ☐ | Asset | Order Type | Side | Qty | Status | Submitted At            │
│                                                                         │
│ [empty: "No orders. Place a trade via the API or dashboard."]           │
│ [Previous] [1] [Next]                                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Layout orchestration — revised CockpitRenderer

```
CockpitRenderer
├── CockpitHeader          (always, common — mandate + autonomy)
└── if program_sections declared in composition:
    └── for each section (sorted by order):
        └── dispatchComponent(section.kind)
    else (no bundle active):
    └── [four kernel-default faces: MandateFace, MoneyTruthFace, PerformanceFace, TrackingFace]
        (MandateFace retained as kernel-default fallback when CockpitHeader
         is present it becomes redundant; deferred cleanup)
```

---

## Implementation roadmap — ADR-243

**Phase A — CockpitHeader** (~200 LOC, FE-only)
- Author `web/components/library/CockpitHeader.tsx`
- Reads MANDATE.md (title/summary extraction) + uses `useAutonomy()` (ADR-238 hook)
- Autonomy posture shown inline top-right; links to TP Autonomy tab (ADR-236 Round 5+)
- CockpitRenderer: render `<CockpitHeader />` unconditionally before four-face stack
- SURFACES.yaml: no change for Phase A
- Test gate: 4 assertions (component exists, exports, reads mandate + autonomy)

**Phase B — program_sections compositor** (~100 LOC, FE)
- `web/lib/compositor/types.ts`: add `program_sections?: Array<{kind: string; order: number}>` to cockpit block
- `web/lib/compositor/resolver.ts`: add `getProgramSections(composition)` helper
- `api/services/composition_resolver.py`: pass through `program_sections` from SURFACES.yaml (additive, no merge needed for v1 since single-bundle per workspace)
- CockpitRenderer: if `program_sections` present → render sections instead of four-face stack
- alpha-trader SURFACES.yaml: add `cockpit.program_sections[]` with 4 current-existing component kinds as placeholder

**Phase C — alpha-trader sections** (~400 LOC, FE + backend)
- New backend endpoints: `GET /api/cockpit/positions`, `GET /api/cockpit/recent-orders`
- Author `TraderPortfolio.tsx` (with portfolio history chart), `TraderBalances.tsx`, `TraderPositions.tsx` (upgrade existing), `TraderOrders.tsx`
- Register in `LIBRARY_COMPONENTS`
- alpha-trader SURFACES.yaml: update `program_sections` to reference real component kinds

---

## Relationship to existing docs + ADRs

| Doc | Relationship |
|---|---|
| `docs/architecture/compositor.md` | Seam reference. Phase B extends the compositor with `program_sections`. No change to the core dispatch pattern. |
| ADR-228 | Four-face model. Phase A + Phase B amend the four-face layout: header separates out; program_sections replaces the face stack for bundle workspaces. |
| ADR-242 | Current state: `TraderMoneyTruth`, `TraderSignalExpectancy`, `TraderPositions` as face-dispatch overrides. Phase C supersedes this — these components fold into the `program_sections` stack as upgraded sections. |
| ADR-238 | `useAutonomy()` hook. CockpitHeader consumes it for the autonomy posture display — no code change to the hook itself. |
| `web/components/library/README.md` | Component registry discipline. Phase C adds 4 new trader section components as bundle components. |
