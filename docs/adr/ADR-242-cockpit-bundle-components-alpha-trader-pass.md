# ADR-242: Cockpit Bundle Components — alpha-trader Pass

> **Status**: **Phase 1 Implemented** (2026-04-30); Phase 2 Proposed.
> **Date**: 2026-04-30
> **Authors**: KVK, Claude
> **Dimensional classification**: **Channel** (Axiom 6) primary — fills the empty bundle half of the cockpit composition seam. **Substrate** (Axiom 1) secondary — surfaces platform-live brokerage state alongside `_performance.md` substrate-fallback per ADR-228 D5.
> **Builds on**: ADR-187 (Trading integration — Alpaca client + `platform_connections` row), ADR-194 v2 (Reviewer substrate — Implemented), ADR-198 (Surface Archetypes — five archetypes), ADR-222 (OS framing — kernel/program boundary), ADR-223 (Program Bundle Specification — `SURFACES.yaml` schema), ADR-224 (Kernel/Program Boundary Refactor — Implemented), ADR-225 (Compositor Layer — Phase 1+2+3 Implemented), ADR-228 (Cockpit as Operation — Phase 1+2 Implemented; Commits 3–5 deferred), ADR-236 (Frontend Cockpit Coherence Pass — Implemented; this ADR closes deferred Cluster B items), ADR-237 (Chat Role-Based Design System — Implemented), ADR-238 (Autonomy-Mode FE Consumption — Implemented), ADR-241 (Single Cockpit Persona — Implemented).
> **Composes with**: ADR-241 (the SnapshotModal Item-10 convergence in Phase 2 reuses the four face components ADR-241 made canonical), ADR-209 (Authored Substrate — backend reads platform_connections; no substrate writes), ADR-216 (orchestration vs judgment — backend canon untouched).
> **Closes (per ADR-236 umbrella's Definition of Done deferrals)**: MoneyTruth platform-live binding (originally deferred from ADR-228 Commit 3); Item 10 cockpit ↔ snapshot convergence (deferred from ADR-236 Round 5).
> **Companion memo**: [docs/analysis/cockpit-bundle-component-audit-2026-04-30.md](../analysis/cockpit-bundle-component-audit-2026-04-30.md). Memo is the architecture-level diagnosis; this ADR is the decision record + implementation contract.
> **Preserves**: FOUNDATIONS axioms 1–9, ADR-141 (execution layers), ADR-156 (single intelligence layer), ADR-225 invariants I1–I5 (kernel defaults are library components, bundle declarations are data not code, components own visual semantics, singular implementation per slot, kernel/program boundary respected), ADR-228 four-face universal-fixed-order model.

---

## Context

The companion memo (`docs/analysis/cockpit-bundle-component-audit-2026-04-30.md`) audits the existing cockpit + compositor architecture against shipped reality. **TL;DR**: the architecture is correct in shape; what's missing is the bundle component layer was never written for the cockpit faces. ADR-228's Commits 3–5 were deferred and the work was never picked back up.

Concretely:

| Surface | Kernel-default | alpha-trader bundle override | State |
|---|---|---|---|
| Mandate face | ✓ MANDATE.md + AUTONOMY.md substrate read | None (correct — face is universal) | Working |
| MoneyTruth face | ✓ `_performance.md` frontmatter (substrate-fallback) | **None** (live_source absent) | **Empty half** |
| Performance face | ✓ Reviewer calibration aggregate | **None** (no signal-expectancy override) | **Empty half** |
| Tracking face | ✓ Pending action_proposals + recent activity (kernel) | **None** (operational state = link-out placeholder) | **Empty half** |

The operator's observation ("current simply isn't working") is the consequence of running on placeholder substrate. The architecture supports the bundle override path; nobody filled it.

The operator's reframe ("dedicated components and generic for kernel projects") is exactly the existing ADR-225 contract:
- **Dedicated components** = bundle-supplied per program
- **Generic for kernel projects** = kernel-default library components

ADR-242 fills the bundle half for alpha-trader, finishes ADR-228 Commits 3–5, and structurally absorbs ADR-236's Item 10 (cockpit ↔ snapshot convergence) as a side-effect of having reusable face components.

---

## Decision

Three structural changes, two phases.

### D1 — Backend platform-live MoneyTruth endpoint (Phase 1)

`GET /api/cockpit/money-truth/{user_id}` returns a normalized brokerage snapshot:

```json
{
  "live": true,
  "provider": "alpaca",
  "paper": true,
  "equity": 100000.00,
  "cash": 95000.00,
  "buying_power": 200000.00,
  "day_pnl": 234.50,
  "day_pnl_pct": 0.23,
  "positions_count": 5,
  "as_of": "2026-04-30T14:30:00Z"
}
```

Or, when Alpaca is unreachable / no trading platform connection:

```json
{
  "live": false,
  "fallback_reason": "no_platform_connection" | "alpaca_unreachable" | "no_credentials",
  "as_of": null
}
```

The endpoint reads `platform_connections` for the `trading` row, decrypts `credentials_encrypted` (format: `api_key:api_secret`), reads `metadata.paper`, calls `alpaca_client.get_account()` + `get_positions()`. On any error, returns the `live: false` shape — the FE handles graceful degradation to substrate-fallback.

**Naming discipline (per memo R1)**: endpoint is named by **what it returns** (Alpaca account snapshot), not by **who consumes it** (cockpit). Future readers wanting Alpaca live equity for any reason (e.g., a future portfolio dashboard, an MCP query) can use the same endpoint. The path `/api/cockpit/money-truth/` reflects the current consumer surface; the rename to `/api/platforms/trading/account-snapshot` is a future hygiene if pressure surfaces.

Auth boundary: `user_id` in the path must match `auth.user_id`. No cross-user reads.

### D2 — Bundle components (Phase 2)

Three new files in `web/components/library/`, registered in `LIBRARY_COMPONENTS`:

- `TraderMoneyTruth.tsx` — calls `/api/cockpit/money-truth/{user_id}`. Renders brokerage shape: equity headline, day Δ tile, buying power, positions count. Falls back to substrate-fallback rendering (current `MoneyTruthFace` body) when `live: false`.
- `TraderSignalExpectancy.tsx` — reads `_performance.md` frontmatter for `expectancy_by_signal` block. Renders signal-type → expectancy table.
- `TraderPositions.tsx` — reads `_positions.md` (or substrate-equivalent path declared in manifest). Renders positions table — symbol, quantity, market value, unrealized P&L.

All three honor the per-slot conventions in `compositor.md`: visual shape matches the face's slot; substrate read is unidirectional (component → API/substrate); no mutation surface; loading + error + empty states owned by the component.

### D3 — Bundle manifest extension (Phase 1)

`docs/programs/alpha-trader/SURFACES.yaml` extends:

```yaml
cockpit:
  money_truth:
    live_source: alpaca
    substrate_fallback: /workspace/context/portfolio/_performance.md
  performance:
    attribution_source: /workspace/context/portfolio/_performance.md
    components:
      - kind: TraderSignalExpectancy
        source: attribution_source
  tracking:
    operational_state:
      kind: TraderPositions
      source: /workspace/context/portfolio/_positions.md
```

The composition resolver passes the cockpit block through unchanged; face components consume the keys they understand and ignore the rest (per ADR-228 D5: "schema is open by design — face components consume only the keys they understand").

Per ADR-225 §"Multi-bundle composition", this is forward-compatible with multi-bundle workspaces: the per-face deep-merge resolves correctly when a future alpha-commerce ships its own cockpit bundle declarations.

### D4 — Face dispatch branches (Phase 2)

Each face component gains a **dispatch branch**: when the cockpit binding declares a bundle component, dispatch through `LIBRARY_COMPONENTS`. Else, fall back to existing kernel-default render.

```ts
// MoneyTruthFace.tsx (sketch)
const bundleSource = composition.tabs?.work?.list?.cockpit?.money_truth?.live_source;
if (bundleSource === 'alpaca') {
  return dispatchComponent({ kind: 'TraderMoneyTruth', source: '...' }, {});
}
return <KernelMoneyTruthFallback />;  // existing body
```

The face's structural shape (size, positioning in the cockpit zone, accessibility role) stays. Only the inner content's source changes when the bundle takes over.

**Singular Implementation discipline**: kernel-default render and bundle render do NOT coexist visually. A single render path per workspace state — bundle when declared, kernel when absent. No A/B, no toggle.

### D5 — SnapshotModal convergence — Item 10 fold-in (Phase 2)

Per the operator's reframe ("replacing existing work page, re-using the components for chat snapshot tabs"), SnapshotModal's three tabs (Mandate / Review / Recent) gain bundle-component reuse:

- **Mandate tab** → renders `<MandateFace />` directly (the same component `/work` cockpit uses).
- **Review tab** → renders the same Principles content that's now TP's Principles tab (post-ADR-241), composed inline rather than re-rendered.
- **Recent tab** → unchanged structurally; already operates as a narrative slice.

This is **structural simplification**, not new code. The components exist post-ADR-241; SnapshotModal imports them and renders inline. Item 10 (cockpit ↔ snapshot convergence) collapses into ADR-242 Phase 2 as a near-zero-cost addition since the face components are now bundle-aware and self-contained.

---

## What this ADR does NOT do

- **Does not change the four-face cockpit model** (ADR-228 universal-fixed-order stays).
- **Does not introduce alpha-commerce bundle overrides** (alpha-commerce is `status: deferred` per ADR-224; its bundle components ship when the program activates against a real consumer).
- **Does not modify `LIBRARY_COMPONENTS` registry shape** (three new entries added; pattern unchanged).
- **Does not introduce a new resolution site** (reuses existing cockpit binding map).
- **Does not amend ADR-225 invariants I1–I5**.
- **Does not change `compositor.md`'s seam description** (the doc was correct; this ADR fills the empty half).
- **Does not introduce a JS test runner** (Python regression gates per ADR-236 Rule 3).
- **Does not touch substrate writes** (Alpaca client is read-only here; submit_order continues to flow through `services/platform_tools.py` per ADR-187).
- **Does not duplicate `ConnectedIntegrationsSection` logic** (the Alpaca credential read uses the same `token_manager.decrypt` pattern as `routes/integrations.py`; no parallel implementation).

---

## Implementation

### Phase 1 — Backend + bundle manifest extension (this commit, ~250 LOC)

**Files created (2)**:
- `api/routes/cockpit.py` — new router file. One endpoint: `GET /api/cockpit/money-truth/{user_id}`. ~100 LOC.
- `api/test_adr242_phase1_cockpit_money_truth.py` — Python regression gate (6 assertions).

**Files modified (3)**:
- `api/main.py` — register the new `cockpit_router` under `/api`.
- `docs/programs/alpha-trader/SURFACES.yaml` — extend `cockpit:` block per D3.
- `api/integrations/core/alpaca_client.py` — verified: `get_account` + `get_positions` already exist; no changes needed for Phase 1.

**Test gate (Phase 1)** asserts:
1. `api/routes/cockpit.py` exists and exports `router`.
2. The endpoint returns the documented shape (`live: bool`, `equity` / `fallback_reason` exclusive).
3. alpha-trader's `SURFACES.yaml` declares `cockpit.money_truth.live_source: alpaca`.
4. alpha-trader's `SURFACES.yaml` declares `cockpit.performance.components` array.
5. alpha-trader's `SURFACES.yaml` declares `cockpit.tracking.operational_state`.
6. alpaca_client's `get_account` + `get_positions` methods exist (regression guard against the dependency being removed).

**Render parity (Phase 1)**:
| Service | Affected | Why |
|---|---|---|
| API (yarnnn-api) | **Yes** | New `/api/cockpit/money-truth/{user_id}` endpoint. |
| Unified Scheduler | No | FE-only consumer; scheduler does not need cockpit endpoints. |
| MCP Server | No | MCP surface is ADR-169's three intent tools; cockpit is separate. |
| Output Gateway | No | Untouched. |

**No env var changes. No schema changes. No new services.** Endpoint reads existing `platform_connections` rows + decrypts via existing `token_manager`.

### Phase 2 — Bundle components + face dispatch + SnapshotModal fold-in (next commit, ~500 LOC)

**Files created (3)**:
- `web/components/library/TraderMoneyTruth.tsx`
- `web/components/library/TraderSignalExpectancy.tsx`
- `web/components/library/TraderPositions.tsx`

**Files modified (5)**:
- `web/components/library/registry.tsx` — three new entries.
- `web/components/library/faces/MoneyTruthFace.tsx` — dispatch branch on `live_source === 'alpaca'`.
- `web/components/library/faces/PerformanceFace.tsx` — dispatch branch on declared `components[]`.
- `web/components/library/faces/TrackingFace.tsx` — `OperationalState` region dispatches on declared `operational_state.kind`.
- `web/components/chat-surface/SnapshotModal.tsx` — Mandate tab renders `<MandateFace />`; Review tab renders the same Principles content TP's tab uses.

**Files NOT modified**:
- ADR predecessors (Rule 2 historical preservation).
- `compositor.md` (doc correctly describes the intended seam; this ADR fills it).
- `LIBRARY_COMPONENTS` shape — entries added; pattern unchanged.

**Test gate (Phase 2)** asserts:
1. Three bundle component files exist.
2. Three components registered in `LIBRARY_COMPONENTS`.
3. `MoneyTruthFace`, `PerformanceFace`, `TrackingFace` each have a dispatch branch.
4. `SnapshotModal.tsx` imports `MandateFace` from `@/components/library/faces/MandateFace`.
5. `SnapshotModal.tsx` does NOT re-implement Mandate or Principles content (regression guard against duplication).
6. `LIBRARY_COMPONENTS` stays a single registry — no per-bundle namespace introduced.

**Render parity (Phase 2)**: FE-only.

### Singular Implementation discipline

- One MoneyTruth endpoint (`/api/cockpit/money-truth/{user_id}`). No parallel "live snapshot" path elsewhere.
- One bundle component per face slot. No legacy substrate-only render coexists with the bundle render — the face's dispatch branch picks one path per workspace state.
- One Mandate face component (`MandateFace.tsx`). SnapshotModal imports it; does NOT re-implement.
- One Principles content (TP Principles tab). SnapshotModal imports it; does NOT re-implement.
- One bundle manifest extension. No mid-flight schema migration.

---

## Risks

**R1 — Alpaca credentials decryption boundary.** Endpoint decrypts `platform_connections.credentials_encrypted` server-side. Same pattern as existing `services/platform_tools.py` Alpaca tool callers. Mitigation: reuse the `token_manager.decrypt` path; never log decrypted credentials; never return them.

**R2 — Alpaca rate limiting.** The MoneyTruth endpoint is operator-facing (one call per cockpit render). Alpaca's free tier allows 200 req/min. With one operator polling on tab focus + cockpit mounts, rate-limit pressure is low. Mitigation: face component fetches once on mount, no auto-poll. Future enhancement: client-side cache + manual refresh button (deferred — operator demand will surface it).

**R3 — Dispatch branch coupling.** Each face's dispatch branch couples to a specific bundle binding key (`live_source`, `components`, `operational_state`). Adding a new bundle (e.g., alpha-commerce) requires extending each face's dispatch logic. Mitigation: the dispatch logic is a thin "if bundle declares X, dispatch component Y" — extending it for alpha-commerce is one new branch per face. The pattern is already in shape; ADR-242 sets the precedent.

**R4 — SnapshotModal-vs-cockpit visual divergence.** SnapshotModal renders the same components in a smaller container. Visual layout might differ (modal width vs cockpit zone width). Mitigation: face components honor their container's width via responsive Tailwind classes — already true today for the substrate-fallback path; bundle components inherit the same convention.

**R5 — Phase 1 ships without operator-visible change** (backend endpoint + manifest extension only; faces still render kernel-default). Mitigation: explicit two-phase split — Phase 1's value is ungating Phase 2; operator manual smoke happens after Phase 2 lands.

**R6 — `_positions.md` substrate may not exist.** alpha-trader's `_positions.md` is an accumulated context file; it materializes when track-universe + portfolio-review tasks run. Cold workspaces won't have it. Mitigation: `TraderPositions.tsx` renders an empty state ("No positions tracked yet — run portfolio-review to populate") rather than 404.

---

## Phasing

Two atomic commits, one per phase. Phase 1 ships first; Phase 2 ships in a subsequent session after Phase 1 is operator-validated end-to-end via direct curl against `/api/cockpit/money-truth/{user_id}`.

**Phase 1 sequence**:
1. Author `api/routes/cockpit.py`.
2. Register router in `api/main.py`.
3. Extend `docs/programs/alpha-trader/SURFACES.yaml`.
4. Author `api/test_adr242_phase1_cockpit_money_truth.py`.
5. Run all gates (231/233 P1+P2/234/237/238/239/240/241/242 Phase 1).
6. CHANGELOG entry `[2026.04.30.N]`.
7. Atomic commit.

**Phase 2 sequence** (separate commit):
1. Author three bundle components in `web/components/library/`.
2. Register in `registry.tsx`.
3. Add dispatch branches to three face components.
4. Refactor `SnapshotModal.tsx` to import + render face components.
5. Author `api/test_adr242_phase2_face_dispatch.py`.
6. Run all gates.
7. CHANGELOG entry.
8. Atomic commit.
9. Operator manual smoke against alpha-trader workspace.

Pre-commit `git diff --cached --stat` discipline per ADR-239 recovery note (commit `0a7fee3`) — verify no other-session sweep-up.

---

## Closing

ADR-242 closes the bundle-component half of the cockpit composition seam. The architecture (ADR-225) was correct from the start; the kernel/program boundary (ADR-224) was correctly enforced; the four-face model (ADR-228) was correctly framed. What was missing was the bundle author actually writing the components for the alpha-trader cockpit. ADR-242 is that work — finishing ADR-228 Commits 3–5 + folding in ADR-236 Item 10's cockpit ↔ snapshot convergence as a structural side-effect.

The pattern this ADR ships becomes the spec for future bundles: when alpha-commerce activates, its bundle components follow the same recipe — manifest declaration + library component + face dispatch branch.

After ADR-242 lands fully (both phases), `compositor.md` §"How a bundle authors a Phase 3 override" gets a documentation update replacing the **hypothetical** alpha-trader portfolio-review example with a **shipped** example. The doc was correct in shape; it just needed a real consumer to validate.
