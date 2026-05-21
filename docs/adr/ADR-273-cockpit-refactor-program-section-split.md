# ADR-273: Cockpit Refactor — Kernel/Program Section Split + Substrate-Backed Trader Sections

**Status**: **Proposed 2026-05-14**. Phased implementation across one PR (8 commits) tracked in working todo list. Phase 0 = this ADR.

**Companion / prior art**:
- ADR-225 — Compositor Layer (the seam that makes program_sections dispatch possible).
- ADR-228 — Cockpit as Delegation Posture (four-face kernel-default — three of which this ADR retires).
- ADR-242 — Trader Money Truth (live Alpaca substrate-binding pattern, preserved).
- ADR-243 — Schedule Surface + CockpitHeader (Phase A header carry-over).
- ADR-271 — Bundle Authoring Discipline + Identity-Layer Audit (mechanical-vs-production carve).
- ADR-272 — Identity-Layer Collapse (clarified what the cockpit dashboard *isn't* about: it's the operation rendered, not the LLM identities).

**Supersedes**:
- ADR-228 §"Cockpit as four faces" — three of the four kernel faces (`MoneyTruthFace`, `PerformanceFace`, `TrackingFace`) are deleted as dead fallback code. The four-face model held during Phase 1 of cockpit work; alpha-trader workspaces never render them (program_sections wins the XOR). `MandateFace` was already noted as redundant in `COCKPIT-COMPONENT-DESIGN.md`; it is deleted here too. `CockpitHeader` (always-rendered, kernel-general) is the singular Layer-1 component going forward.

**Amends**:
- ADR-225 Phase 2 — confirms `web/components/library/programs/{slug}/` as the canonical home for program-specific section components. Kernel-general components stay at `web/components/library/` root. README updated to reflect this convention.
- `COCKPIT-COMPONENT-DESIGN.md` — v3 update: the alpha-trader program section stack grows from 4 to 7 components, three new sections render currently-invisible accumulated substrate.

**Preserves**:
- FOUNDATIONS Axiom 1 (Substrate) — every new section reads from existing substrate files (`_money_truth.md`, `_regime.yaml`, per-ticker `_indicators.yaml`, `signals/{slug}.yaml`). No new substrate is invented.
- FOUNDATIONS Axiom 6 (Channel) — surface archetypes per ADR-198. The cockpit zone of `/work` list mode remains a Dashboard archetype (live substrate slice, no action affordances).
- ADR-194 v2 Reviewer substrate — `/workspace/review/decisions.md` is the source for TraderSignals' reviewer-trail render.
- ADR-195 v2 money-truth substrate — `_money_truth.md` frontmatter (totals, by_signal, by_action_type, rolling windows) is the source for TraderExpectancy.
- ADR-209 Authored Substrate — substrate reads are authoritative; component renders are pure.
- ADR-262 — output topology lives in CONVENTIONS.md / SURFACES.yaml, not registries. This ADR adds 3 new component `kind`s to the universal library; SURFACES.yaml declares them in `cockpit.program_sections[]`.

**Dimensional classification**: **Channel** (Axiom 6) primary — restructures the cockpit dashboard's visual architecture. **Substrate** (Axiom 1) secondary — surfaces accumulated trading substrate that was previously invisible. No Identity / Mechanism / Purpose / Trigger changes.

---

## 1. Why this ADR

Three observations from production:

1. **The dashboard's kernel-vs-program boundary is buried in filenames, not the filesystem.** `web/components/library/` is currently flat: `CockpitHeader.tsx`, `MoneyTruthFace.tsx` (kernel-general); `TraderMoneyTruth.tsx`, `TraderPortfolio.tsx`, `TraderPositions.tsx`, `TraderOrders.tsx` (program-specific). The README claims a single universal library, but the trader components are program-specific by name and SURFACES.yaml binding. New contributors can't tell the boundary at a glance.

2. **The kernel-default fallback faces are dead code for any workspace with an active program.** `MoneyTruthFace`, `PerformanceFace`, `TrackingFace`, `MandateFace` only render when `program_sections` is absent from SURFACES.yaml — which is true only for the never-activated workspace state. alpha-trader (active) and alpha-commerce (deferred) both declare program_sections; the four faces are vestigial. The design doc already flagged `MandateFace` as "redundant; deferred cleanup." This ADR finishes the cleanup for all four.

3. **The trading substrate accumulates richer signal than the dashboard renders.** Live E2E session 2026-05-14 produced:
   - 5 per-ticker `_indicators.yaml` files (SMA/RSI/ATR/volume) — invisible on dashboard
   - `_regime.yaml` mechanical mirror with today's tape regime + breadth + vol — invisible on dashboard
   - 2 of 5 expected `signals/{slug}.yaml` files + reviewer decisions trail in `/workspace/review/decisions.md` — invisible on dashboard
   - `_money_truth.md` frontmatter with `by_signal` per-signal attribution + rolling 7d/30d/90d windows — invisible on dashboard (renders only in deleted `MoneyTruthFace`, never in alpha-trader's `TraderMoneyTruth`)

   The operator's dashboard today shows live Alpaca data (equity, balances, positions, orders) but none of the *accumulated* intelligence the substrate has built up. The gap between "system accumulates" and "operator sees" is the surface the dashboard refactor closes.

---

## 2. Decisions

### D1 — Filesystem split: kernel-general at library/ root, program-specific at library/programs/{slug}/

`web/components/library/` reorganizes:

```
web/components/library/
├── CockpitHeader.tsx              kernel-general (always renders, Layer 1)
├── CockpitRenderer.tsx            kernel-general (dispatch + unactivated CTA)
├── CockpitContext.tsx             kernel-general
├── ChromeRenderer.tsx             kernel-general
├── MiddleResolver.tsx             kernel-general
├── BundleBanner.tsx               kernel-general
├── WorkDetailActionsContext.tsx   kernel-general
├── kernel-chrome/                 kernel-general
├── registry.tsx                   updated imports (kernel + programs/*)
├── README.md                      v2 — programs/ subdir convention
└── programs/
    └── alpha-trader/
        ├── TraderRegime.tsx       NEW (D4)
        ├── TraderPortfolio.tsx    moved from library/ root
        ├── TraderMoneyTruth.tsx   moved from library/ root
        ├── TraderExpectancy.tsx   NEW (D4)
        ├── TraderPositions.tsx    moved from library/ root, substrate-merged in D4
        ├── TraderSignals.tsx      NEW (D4)
        └── TraderOrders.tsx       moved from library/ root
```

`registry.tsx::LIBRARY_COMPONENTS` continues to be one flat dict keyed by `kind`. The folder split is filesystem signal, not registry namespacing — SURFACES.yaml still references components by bare `kind`. The registry imports kernel components from `./` and program components from `./programs/alpha-trader/`.

Future programs follow the same convention: `web/components/library/programs/alpha-commerce/*`, `web/components/library/programs/alpha-defi/*`, etc. Mirrors the on-disk `docs/programs/{slug}/` structure.

### D2 — Delete the three dead kernel fallback faces (+ MandateFace)

Four files DELETED:
- `web/components/library/faces/MoneyTruthFace.tsx`
- `web/components/library/faces/PerformanceFace.tsx`
- `web/components/library/faces/TrackingFace.tsx`
- `web/components/library/faces/MandateFace.tsx`

The `faces/` directory is removed entirely.

`CockpitRenderer.tsx` simplifies — the four-face fallback branch is replaced by a clean "no program activated" CTA reading `/api/workspace/state.active_program_slug`:

```
if program_sections declared (active bundle with sections):
    render CockpitHeader + each section in order
else:
    render CockpitHeader + UnactivatedCockpitCTA
        ("Activate a program from Settings → Workspace to see your operation here.")
```

The MoneyTruthFace `by_signal` rendering — which alpha-trader workspaces never saw — moves into the new `TraderExpectancy` section. No data is lost; the surface for it changes.

### D3 — Three new backend cockpit routes for substrate reads

All three are pure substrate reads (zero LLM, deterministic). They follow the same pattern as the existing `/api/cockpit/positions` route — read workspace_files at a known path, parse YAML/markdown frontmatter, return JSON.

| Endpoint | Reads | Shape |
|---|---|---|
| `GET /api/cockpit/regime` | `/workspace/context/trading/_regime.yaml` | `{ live: bool, regime: str, breadth_pct: number, vol_regime: str, as_of: str }` |
| `GET /api/cockpit/signals` | `/workspace/context/trading/signals/*.yaml` + `/workspace/review/decisions.md` (correlation) | `{ signals: [{ slug, ticker, direction, expectancy, status, reviewer_decision?, decided_at? }] }` |
| `GET /api/cockpit/indicators?ticker={t}` | `/workspace/context/trading/{ticker}/_indicators.yaml` | `{ ticker, sma_50, sma_200, rsi_14, atr_14, volume_avg_20, as_of }` |

The existing `/api/cockpit/money-truth` route already returns the `by_signal` block consumed by `TraderExpectancy` — no expectancy-specific route needed.

### D4 — New + rewritten trader sections (the substance)

Four existing sections rewritten:

- **`TraderPortfolio`** — minor visual cleanup. Same data binding (`api.cockpit.portfolioHistory()` + `api.cockpit.moneyTruth()`).
- **`TraderMoneyTruth`** — minor cleanup. Already balances-only (equity, buying power, cash, positions count, day Δ). No `by_signal` rendering here — moves to `TraderExpectancy`.
- **`TraderPositions`** — substrate-merged. Live Alpaca position table extended with per-ticker indicators column (regime context: trend direction from SMA, ATR-based suggested stop-loss). Reads `/api/cockpit/positions` (live) + iterates `/api/cockpit/indicators?ticker={t}` (substrate) per row.
- **`TraderOrders`** — visual cleanup. Same data binding (`api.cockpit.recentOrders()`).

Three new sections:

- **`TraderRegime`** (order 1) — thin one-line headline strip at top of program section stack. Reads `/api/cockpit/regime`. Renders: `Risk-on · breadth 78% · vol regime: compressed · as of 9:15am KST`. High signal-to-pixel ratio. Single component, single line, no card chrome.

- **`TraderSignals`** (order 6) — reads `/api/cockpit/signals`. Renders today's evaluated signals (from `signals/{slug}.yaml`) with reviewer decision correlated from `decisions.md`. Each row: ticker · direction (long/short) · expectancy · reviewer verdict (approved / rejected / deferred) · reasoning excerpt. Closes the gap between "signal evaluator fires proposal" and "operator sees what was evaluated and why the reviewer said no."

- **`TraderExpectancy`** (order 4) — reads `/api/cockpit/money-truth.by_signal` (existing payload). Renders per-signal attribution: signal_id · count · win rate · total P&L · rolling 7d/30d/90d expectancy. This is the surface for the `by_signal` block that ADR-242 / P&L unification (2026-05-12) intended to surface — currently dark because it lives in `MoneyTruthFace` which alpha-trader never renders.

### D5 — SURFACES.yaml program_sections ordering

The dashboard tells a story top-to-bottom. New ordering:

```yaml
cockpit:
  program_sections:
    - kind: TraderRegime         # order: 1 — "what's the tape doing"
      order: 1
    - kind: TraderPortfolio      # order: 2 — "how is the account doing overall"
      order: 2
    - kind: TraderMoneyTruth     # order: 3 — "what can I deploy / what moved today"
      order: 3
    - kind: TraderExpectancy     # order: 4 — "which signals work, tenured"
      order: 4
    - kind: TraderPositions      # order: 5 — "what's open right now + regime context"
      order: 5
    - kind: TraderSignals        # order: 6 — "what did the system evaluate today, why was it accepted/rejected"
      order: 6
    - kind: TraderOrders         # order: 7 — "ledger of recent executions"
      order: 7
```

Rationale: tape → account → balances → tenure → live state → today's decisions → ledger. Each section builds on the prior. Operator can reorder via WriteFile per ADR-262 §6.2 (SURFACES.yaml mutation discipline).

### D6 — Graceful degradation for empty substrate

Each new section renders an empty-state-with-context when its substrate file is absent (not the cleaner `null`):

- `TraderRegime` absent → "Regime tracker hasn't fired yet — paused or first run pending."
- `TraderSignals` empty → conditional on `evaluator_last_run_at` from `tasks.last_run_at` for `signal-evaluation`: when null, "No signals evaluated yet. Signal evaluator runs at market open." When populated, "Evaluator last ran {when} — no signals matched entry conditions." Distinguishes "never run" from "ran, found nothing" — the latter is the steady-state default when entry rules are tight.
- `TraderExpectancy` empty `by_signal` → "No reconciled outcomes yet — reconciliation runs daily at 05:00 UTC."
- `TraderPositions` indicators absent for a ticker → renders position row without indicator column; no error.

Empty-state messages reference the back-office task that would populate them — a self-documenting trail back to the recurrence layer.

---

## 3. Singular Implementation discipline

This ADR honors the rule by:
- Deleting 4 files (4 dead fallback faces). No flag, no shim, no opt-out path.
- Moving 4 files (Trader components → programs/alpha-trader/). The old paths cease to exist; registry imports update.
- Adding 3 new components + 3 new backend routes. No prototypes, no behind-flag versions.
- `CockpitRenderer` fallback branch collapses to one shape (the UnactivatedCockpitCTA). The fallback's previous "render four kernel faces" branch is gone.

Failure mode if any of the above is dual-pathed (e.g. keeping `MoneyTruthFace.tsx` "for now"): the kernel-vs-program boundary the operator asked for stays buried. We commit to the move.

---

## 4. Out of scope

- **Universal library expansion**: only program-specific components for alpha-trader change. No new kernel-general components ship in this ADR. The `MetricCardRow` / `TaskOutputViewer` / `AlertCard` etc. (paper-design from ADR-225) remain deferred until a bundle demands them.
- **alpha-commerce / alpha-defi cockpit sections**: alpha-commerce is `status: deferred` per ADR-224; no FE work. alpha-defi is `reference`-only.
- **Cockpit Header redesign**: `CockpitHeader` (Phase A of ADR-243) carries forward unchanged.
- **Mobile / responsive shifts**: existing layout discipline preserved.
- **CockpitContext / WorkDetailActionsContext refactor**: these stay as is; D1 just relocates Trader components, not the surrounding context plumbing.

---

## 5. Implementation roadmap

Eight commits, each green (type-check passes, build succeeds, no broken imports):

| Phase | Commit | Scope |
|---|---|---|
| 0 | this commit | ADR-273 authored |
| 1 | `refactor(adr-273 phase 1)` | FS split: library/programs/alpha-trader/ + registry imports + README v2 |
| 2 | `refactor(adr-273 phase 2)` | Delete 4 kernel faces + CockpitRenderer fallback rewrite |
| 3 | `feat(adr-273 phase 3)` | 3 new backend cockpit routes (regime, signals, indicators) |
| 4 | `refactor(adr-273 phase 4)` | Rewrite 4 existing Trader components (Portfolio/MoneyTruth/Positions/Orders) |
| 5 | `feat(adr-273 phase 5)` | New TraderRegime + TraderSignals + TraderExpectancy |
| 6 | `feat(adr-273 phase 6)` | SURFACES.yaml program_sections updated |
| 7 | `docs(adr-273 phase 7)` | COCKPIT-COMPONENT-DESIGN.md v3 + library README + CLAUDE.md ADR-273 entry |
| 8 | (verification) | Type-check + final smoke + push |

Phase ordering rationale: 0–2 are mechanical (cheap, low risk, set up clean state). 3 unblocks 4 and 5 (backend before frontend consumers). 4 + 5 author the components. 6 wires them. 7 closes the doc loop. 8 verifies.

---

## 6. Risks & mitigations

- **R1**: Deleting `MoneyTruthFace` strands an operator on a never-activated workspace.
  **Mitigation**: D2's UnactivatedCockpitCTA is the explicit empty-state replacement. The four-face fallback was always a placeholder; the activation flow per ADR-244 is the real onboarding surface.

- **R2**: `_regime.yaml` / `_indicators.yaml` schema drift between mechanical mirror writer (Python) and FE reader.
  **Mitigation**: Backend route parses + reshapes into a stable FE contract. If the substrate writer changes shape, only the route's parser updates — components stay stable.

- **R3**: `TraderSignals` correlation between `signals/{slug}.yaml` and `decisions.md` is fragile.
  **Mitigation**: Backend route does the correlation (text-match on slug + ticker). FE consumes a clean denormalized payload. If correlation fails, signals render without `reviewer_decision` field (graceful).

- **R4**: Phase 1 (FS split) breaks registry imports if not done atomically.
  **Mitigation**: Phase 1 commit moves files AND updates `registry.tsx` imports in the same commit. Type-check verifies before commit.

---

## 7. Acceptance criteria (Phase 8 verification)

- [ ] `web/components/library/programs/alpha-trader/` contains 7 components (4 rewritten + 3 new).
- [ ] `web/components/library/faces/` directory does not exist.
- [ ] `CockpitRenderer` has no four-face fallback branch.
- [ ] `GET /api/cockpit/regime`, `/signals`, `/indicators?ticker=...` return well-formed JSON in dev.
- [ ] alpha-trader SURFACES.yaml program_sections lists 7 entries in declared order.
- [ ] `npx tsc --noEmit` clean.
- [ ] Production build clean (`pnpm build` in web/).
- [ ] On kvk's workspace: dashboard renders all 7 sections in order without console errors.
- [ ] Empty-state copy renders correctly for sections whose substrate is absent.
