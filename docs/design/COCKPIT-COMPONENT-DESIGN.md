# Cockpit Component Design — Common vs Program-Specific

> **Status**: Canonical design reference (2026-05-01). Governs the visual
> architecture of the `/work` cockpit zone — specifically how **common**
> (kernel-default, any workspace) components and **program-specific** (bundle-
> supplied, e.g. alpha-trader) components compose on screen.
>
> This doc does NOT replace `docs/architecture/compositor.md` (the seam
> reference) or ADR-228 (the four-face model). It adds the visual design layer
> those docs omit.

---

## The two-layer model

The operator sketch that drove this document showed a clear two-layer page
structure:

```
┌──────────────────────────────────────────────────────────────────────┐
│ COMMON - PAGE HEADER                                                 │
│                                                                      │
│   Title: {mandate-based title}        autonomy mode: [toggle]        │
│                                                                      │
│   {mandate-based summary paragraph}                                  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ PROJECT SPECIFIC - for trader "performance"                          │
│                                                                      │
│   [Portfolio chart — 1D/1M/1Y/All]   [Watchlist]                    │
│                                                                      │
│   Balances: Buying Power · Cash · Daily Change                       │
│                                                                      │
│   Top Positions: Asset | Price | Qty | Market Value | Total P/L     │
│                                                                      │
│   Recent Orders: searchable, filterable, paginated                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

**Layer 1 — Common (kernel-default, always present)**
- Mandate-based title and summary: derived from `/workspace/context/_shared/MANDATE.md`
- Autonomy mode indicator + toggle: derived from `/workspace/context/_shared/AUTONOMY.md`
- Applies to every workspace regardless of active program
- Visual style: clean, prose-weight, page-header shape (not a card)

**Layer 2 — Program-specific (bundle-supplied)**
- The entire brokerage/operation-specific dashboard
- For alpha-trader: portfolio chart + balances + positions + recent orders
- For alpha-commerce: revenue chart + product summary + recent orders/subscribers
- Visual style: data-rich, domain-shaped, can embed external dashboard aesthetics

---

## Gap between current implementation and design intent

As of 2026-05-01, the cockpit renders **four equal-weight stacked cards**:
1. MandateFace — mandate text + autonomy summary (card, not page header)
2. MoneyTruthFace — stat tiles (equity, buying power, positions count)
3. PerformanceFace — Reviewer calibration + signal expectancy table
4. TrackingFace — pending proposals + operational state (positions link-out) + recent activity

**What the design requires instead:**

| Current | Target |
|---|---|
| MandateFace renders as a card among peers | MandateFace becomes `CockpitHeader` — full-width page header, mandate title prominent, autonomy toggle inline top-right |
| Autonomy chip lives only in chat composer (ADR-238) | Autonomy posture surface moves to `CockpitHeader` — the cockpit is where the operator *runs* the operation; autonomy belongs there |
| MoneyTruth + Performance + Tracking as separate cards | Bundle replaces all three with one unified `TraderDashboard` component — portfolio chart, balances, positions, orders as a single cohesive block |
| `TraderMoneyTruth` shows 3 stat tiles only | `TraderDashboard` shows the full Alpaca brokerage panel shape |

---

## Common components — visual contract

**CockpitHeader** (`web/components/library/CockpitHeader.tsx`)

Always rendered. No bundle override. Visual shape:

```
┌─────────────────────────────────────────────────┐
│                                                  │
│  {Mandate title}              Autonomy: [label]  │
│                                                  │
│  {Mandate summary — first non-blank paragraph}   │
│                                                  │
└─────────────────────────────────────────────────┘
```

- Title: derived from `## Primary Action` heading or first `# Mandate` heading in MANDATE.md
- If MANDATE.md is skeleton/empty: CTA prompt "Define your mandate in chat"
- Autonomy label: `manual | assisted | bounded autonomous | autonomous` from AUTONOMY.md default.level
- Autonomy toggle: opens `/agents?agent=thinking-partner&tab=autonomy` (the Autonomy tab, per ADR-236 Round 5+)
- No card border. Subtle background (`bg-muted/10`). Full-width.

---

## Program-specific components — visual contract

**For alpha-trader — `TraderDashboard`**

Single component registered in `LIBRARY_COMPONENTS` as `kind: TraderDashboard`.
Declared in SURFACES.yaml under `cockpit.program_dashboard.kind`.
Replaces the MoneyTruth + Performance + Tracking card stack entirely.

Visual shape (mirrors Alpaca dashboard aesthetic per design sketch):

```
┌─────────────────────────────────────────────────────────────────────┐
│ Your portfolio    [1D] [1M] [1Y] [All] [↻]           [Watchlist]   │
│ $XX,XXX.xx ↑ +X.X%                                                  │
│ April XX, XXXX KST                                                  │
│                                                                      │
│ [equity chart over time period]           [watchlist panel]         │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│ 🗂 Balances                                                    [+]  │
│ Buying Power        Cash             Daily Change                   │
│ $XX,XXX             $XX,XXX          +$XXX (+X.X%)                  │
├─────────────────────────────────────────────────────────────────────┤
│ Top Positions   Asset Class [All ▾]  Side [All ▾]    View All       │
│ Asset | Price | Qty | Market Value | Total P/L ($)                  │
│ [empty state: "No open positions. Place some trades."]              │
├─────────────────────────────────────────────────────────────────────┤
│ Recent Orders                                          View All      │
│ [Search...]                    [Cancel X selected] [⚙ Columns]      │
│ ☐ | Asset | Order Type | Side | Qty | Status | Submitted At        │
│ [empty state: "No orders. Place a trade via dashboard or API."]     │
│ [Previous] [1] [Next]                                               │
└─────────────────────────────────────────────────────────────────────┘
```

Data sources:
- Portfolio chart: `api.cockpit.moneyTruth()` (live Alpaca equity over time, Phase 3 deferred — chart timeline uses Alpaca `/v2/account/portfolio/history`)
- Balances: `api.cockpit.moneyTruth()` (equity, cash, buying_power, day_pnl)
- Positions: `api.cockpit.moneyTruth()` (positions_count) + a new `api.cockpit.positions()` call (Alpaca `/v2/positions`)
- Recent Orders: new `api.cockpit.recentOrders()` call (Alpaca `/v2/orders?status=all&limit=10`)

Fallback when Alpaca unreachable: substrate-derived panel (`_performance.md` + `_positions.md`).

---

## Layout orchestration — how layers compose

`CockpitRenderer` after this design update:

```
CockpitRenderer
├── CockpitHeader          (always, common)
└── ProgramDashboard       (optional, bundle-supplied)
    └── TraderDashboard    (when cockpit.program_dashboard.kind === 'TraderDashboard')
```

The `ProgramDashboard` slot replaces the current four-face stack for workspaces where the bundle declares a program dashboard. Workspaces with no active bundle continue to render kernel-default faces.

---

## Implementation roadmap (ADR-243)

This design requires:

**Phase A — CockpitHeader** (~150 LOC, FE-only)
- Extract mandate title derivation from MandateFace into CockpitHeader
- Move autonomy posture surface from chat composer to CockpitHeader
- CockpitRenderer renders CockpitHeader unconditionally before the four faces

**Phase B — TraderDashboard** (~400 LOC, FE + light backend)
- Author `web/components/library/TraderDashboard.tsx` — portfolio chart + balances + positions + orders
- New backend endpoints: `GET /api/cockpit/positions` (Alpaca positions), `GET /api/cockpit/orders` (recent orders)
- Portfolio chart: uses Alpaca `/v2/account/portfolio/history` (already in `alpaca_client.get_portfolio_history`)
- alpha-trader SURFACES.yaml: `cockpit.program_dashboard.kind: TraderDashboard`
- Deprecate the current three-card stack (MoneyTruth + Performance + Tracking) for bundle workspaces — they remain as kernel-default for non-bundle workspaces

**Phase C — Bundle layout switch**
- CockpitRenderer checks `cockpit.program_dashboard.kind` — when set, renders CockpitHeader + ProgramDashboard only (no individual faces)
- When unset, renders CockpitHeader + original four faces (kernel-default behavior)

---

## What the operator's design sketch tells us about direction

The design communicates two things clearly:

1. **Common = prose/intent layer** — The page header reads like a mandate declaration + the operator's operating mode. It communicates purpose and constraints. It's text-weight, not data-weight.

2. **Project-specific = operational dashboard** — The trader section is literally the Alpaca web interface aesthetic. The operator is running a trading operation; the cockpit should feel like a trading terminal's summary view, not a generic dashboard. This is the key difference: the *program* defines what "operational" looks like for its domain; the kernel just provides the mandate framing.

This maps directly to ADR-222's OS framing: the **kernel** sets the mandate/autonomy layer (universal, any program); **programs** bring their own operational aesthetics (domain-specific).

---

## Relationship to existing architecture docs

- `docs/architecture/compositor.md` — the seam (how `kind` strings map to components). Unchanged.
- `ADR-228` — the four-face model. Phase C above amends it to allow "program_dashboard replaces four faces" for bundle workspaces.
- `ADR-242` — alpha-trader bundle components Phase 1+2 (current state). ADR-243 extends this toward the full design.
- `web/components/library/README.md` — the component registry discipline. ADR-243 adds `CockpitHeader` as a kernel component and `TraderDashboard` as a bundle component.
