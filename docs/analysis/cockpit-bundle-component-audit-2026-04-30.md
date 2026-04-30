# Cockpit Bundle-Component Model — Audit + v2 Proposal

> **Date**: 2026-04-30
> **Author**: KVK, Claude
> **Scope**: Audit the existing compositor + bundle-component architecture (ADR-225 + ADR-228 + ADR-223 + ADR-224 + `docs/architecture/compositor.md`) against shipped reality, find why the model "isn't working," and propose v2.
> **Read alongside**: [docs/architecture/compositor.md](../architecture/compositor.md) (canonical reference), [ADR-225](../adr/ADR-225-compositor-layer.md), [ADR-228](../adr/ADR-228-cockpit-as-delegation-posture.md).

---

## TL;DR

The compositor architecture (ADR-225) is **correct in shape**. The kernel/program boundary (ADR-224) is **correctly enforced**. The cockpit four-face model (ADR-228) is **correctly framed**. What "isn't working" is that **the bundle component layer was never actually written for the cockpit faces** — alpha-trader's `SURFACES.yaml` declares only fallback substrate paths, no bundle component overrides, no platform-live binding. The cockpit is running entirely on kernel-default substrate-fallback paths.

This is not an architecture failure. It is an **implementation completeness** gap that ADR-228 itself flagged ("Commits 3-5 deferred"). The frustration the operator reports — "current simply isn't working" — is the consequence of running on placeholder substrate ([ADR-228 substrate-stub follow-up](../adr/ADR-228-cockpit-as-delegation-posture.md) shipped a stub-writer fix; the **content** is still empty).

The v2 proposal: **finish ADR-228 Commits 3–5 as a coordinated sub-ADR (ADR-242)**, with a sharper framing than "platform-live binding." The right framing is the operator's: **dedicated components per program (alpha-trader, alpha-commerce); generic kernel components for any program that hasn't authored its own.** This is exactly ADR-225's contract — just unfilled.

---

## 1. What the documentation says exists

### 1.1 The kernel/program boundary (ADR-224)

Every program-shaped template lives in a bundle (`docs/programs/{slug}/MANIFEST.yaml`). Kernel registries hold only universal templates. Bundle reads are point-of-use, not always-loaded. Rationale: substrate is fully agnostic; programs are specific by construction.

**Verified by grep:** zero `if (programSlug === ...)` branches in kernel code.

### 1.2 The compositor seam (ADR-225 + compositor.md)

Resolver pattern: declare in YAML → resolve via match (or kernel-default fallback) → dispatch through `LIBRARY_COMPONENTS`. **One pattern, three call sites** (middle / chrome / cockpit).

Five invariants codified in `docs/architecture/compositor.md`:
- I1 — Kernel defaults are library components
- I2 — Bundle declarations are data, not code
- I3 — Components own their visual semantics; the resolver doesn't
- I4 — Singular implementation per slot
- I5 — The seam respects the kernel/program boundary

Six binding types, four resolution sites on Work (detail middle, detail chrome, list pinned tasks, cockpit four faces).

### 1.3 The cockpit four-face model (ADR-228)

Universal four faces in fixed order: **Mandate / MoneyTruth / Performance / Tracking**. Bundles fill each face's binding map; bundles cannot reorder or omit faces. The cockpit IS the operation, rendered.

Phase 1 of ADR-228 shipped: four face components scaffolded; substrate-fallback path; alpha-trader `SURFACES.yaml` migrated to `cockpit:` block. **Commits 3–5 deferred.**

### 1.4 Bundle declaration shape (ADR-223)

`docs/programs/{slug}/SURFACES.yaml` is the composition manifest. Schema validated by ADR-223. Bundles own the entire program-shaped specialization; the kernel stays bundle-agnostic.

---

## 2. What the documentation says SHOULD exist for alpha-trader

Per `compositor.md` §"How a bundle authors a Phase 3 override" + ADR-228's deferred Commits 3–5:

### 2.1 MoneyTruth face — alpha-trader

Documentation contract:
> *"Bundle declares `cockpit.money_truth.live_source` — for trader, an Alpaca account snapshot."*

Alpha-trader bundle SHOULD declare:
```yaml
cockpit:
  money_truth:
    live_source: alpaca  # platform-live snapshot
    substrate_fallback: /workspace/context/portfolio/_performance.md
```

`MoneyTruthFace.tsx` SHOULD have a **bundle-supplied component override** — call it `TraderMoneyTruth.tsx` — that fetches from `/api/cockpit/money-truth/{workspace_id}` (Alpaca live) and renders brokerage-shaped content (equity, buying power, day delta, drawdown).

### 2.2 Performance face — alpha-trader

Documentation contract:
> *"alpha-trader's PerformanceFace surfaces signal expectancy + accuracy by signal type from `portfolio/_performance.md`"*

Alpha-trader SHOULD declare:
```yaml
cockpit:
  performance:
    attribution_source: /workspace/context/portfolio/_performance.md
    components:
      - kind: TraderSignalExpectancy
        source: attribution_source
```

A `TraderSignalExpectancy.tsx` library component SHOULD render expectancy-by-signal-type, distinct from the kernel-default Reviewer-calibration aggregate.

### 2.3 Tracking face — alpha-trader

Documentation contract:
> *"Operational state — bundle-shaped table (positions for trader, active campaigns for commerce)."*

Alpha-trader SHOULD declare:
```yaml
cockpit:
  tracking:
    operational_state:
      kind: TraderPositions
      source: /workspace/context/portfolio/_positions.md
```

A `TraderPositions.tsx` library component SHOULD render the positions table.

---

## 3. What actually exists in code

Sub-section labels: ✓ shipped, ✗ missing, ▲ stub-only.

### 3.1 alpha-trader `SURFACES.yaml` (verified 2026-04-30)

```yaml
cockpit:
  money_truth:
    substrate_fallback: /workspace/context/portfolio/_performance.md   # ✓
    # live_source: ABSENT                                               # ✗
  performance:
    attribution_source: /workspace/context/portfolio/_performance.md   # ✓
    # components: ABSENT                                                # ✗
  # tracking: ABSENT ENTIRELY                                          # ✗
```

The bundle declares **only fallback paths** for two of four faces. The third (`tracking`) is undeclared. The fourth (`mandate`) reads kernel-default paths.

### 3.2 `web/components/library/` (verified 2026-04-30)

```
faces/
  MandateFace.tsx          ✓ kernel default
  MoneyTruthFace.tsx       ▲ kernel-default + substrate-fallback only
  PerformanceFace.tsx      ✓ kernel default (Reviewer calibration)
  TrackingFace.tsx         ▲ kernel default (3 regions: pending decisions ✓
                                                          operational state ▲ link-out placeholder
                                                          recent activity ✓)
kernel-chrome/             ✓ 8 kernel chrome components for /work detail
                              (this is what the bundle pattern WORKS for)
```

**Zero alpha-trader-specific bundle components exist.** Not in `web/components/library/`. Not anywhere in `web/`. The `LIBRARY_COMPONENTS` registry (`registry.tsx`) holds only kernel-default chrome — no `TraderMoneyTruth`, `TraderSignalExpectancy`, `TraderPositions`, `TradingProposalQueue`, `TradingPortfolioMetadata`, or any of the other component names referenced in compositor.md examples.

### 3.3 The platform-live endpoint

```
/api/cockpit/money-truth/{workspace_id}    ✗ does not exist
```

ADR-228's Commit 3 named this endpoint as the platform-live binding seam. It was deferred. `MoneyTruthFace.tsx` only knows the substrate-fallback path; there is no code that calls Alpaca live.

### 3.4 What the operator sees today

For an alpha-trader workspace with `_performance.md` populated:
- **Mandate face**: renders MANDATE.md + AUTONOMY.md (kernel-default; works correctly)
- **MoneyTruth face**: renders `_performance.md` frontmatter as a substrate snapshot (kernel-default; reconciliation-time-stale)
- **Performance face**: renders Reviewer calibration aggregate from `decisions.md` (kernel-default; works correctly)
- **Tracking face**: renders pending action_proposals + a link-out placeholder for operational state + recent activity (kernel-default; placeholder is the issue)

**The operator runs an Alpaca brokerage account next to this cockpit** ([ADR-228 §"Context"](../adr/ADR-228-cockpit-as-delegation-posture.md)). The cockpit shows **stale reconciled substrate**, not live equity. The visceral experience: "I have to look at two screens because YARNNN's cockpit doesn't actually know my account."

---

## 4. Why the doc says it works but it doesn't

The architecture doc (`compositor.md`) describes the **seam** (resolver pattern, override slots, kernel-default fallback). It does not describe **completeness state per face per bundle**.

When `compositor.md` §"How a bundle authors a Phase 3 override" says the alpha-trader portfolio-review override "renders the bundle middle + bundle chrome metadata + kernel chrome actions" — that's a **hypothetical** example. The example is not implemented. There is no `TraderPortfolioMetadata.tsx`. The example is illustrative documentation; readers correctly assume the architecture supports it (it does), and incorrectly assume the example is shipped (it isn't).

Compounding factor: ADR-225's Phase 2 implementation refinements section noted "shipped 6 components not 14 — demand-pull discipline, only what bundles actually reference." That discipline was correct **for /work detail middles**, where alpha-trader doesn't need bundle middles (cockpit absorbed them per ADR-228 Commit 2). But the same discipline applied to the **cockpit faces** means: alpha-trader needs bundle face overrides; those overrides haven't been authored; therefore they don't exist; therefore the cockpit faces render generic kernel-default substrate paths.

The seam is correct. The library is empty. **No demand has pulled the alpha-trader components into existence yet because the operator who would author them is the same operator running the alpha-trader workspace.**

---

## 5. The reframe: "dedicated components and generic for kernel projects"

The operator's phrasing is sharper than ADR-225/228's. Translated:

| Operator language | Architecture language | Today's state |
|---|---|---|
| **Dedicated components** | Bundle-supplied component overrides per program | **0 written for cockpit** |
| **Generic for kernel projects** | Kernel-default library components, used by any program with no override | ✓ shipped (4 faces + 8 chrome) |

The architecture supports both halves of the operator's framing. **Half is shipped (kernel-default), half is empty (bundle-supplied).** The "isn't working" diagnosis is: operator sees one half, calls it broken because the cockpit reads as a placeholder for the alpha-trader workflow it's supposed to host.

This audit identifies the gap as **completing the bundle component layer for alpha-trader's cockpit**, not as an architectural rewrite. The compositor seam, the kernel/program boundary, the four-face model — all stay.

---

## 6. v2 Proposal — ADR-242 scope

Open as a sub-ADR draft (proposed, not implemented in this audit memo).

### 6.1 ADR-242 title (working)

**ADR-242: Cockpit Bundle Components — alpha-trader Pass.**

Or if the scope wants to be clearer: **ADR-242: Cockpit v2 — Finishing the Bundle Component Layer.**

The first is operationally honest (this is alpha-trader work primarily). The second is architecturally honest (the pattern generalizes; alpha-trader is the first concrete consumer).

**Recommendation**: title **"ADR-242: Cockpit Bundle Components — alpha-trader Pass"** — names the immediate consumer; the generalization to alpha-commerce becomes a future ADR-242.5 / ADR-243 after operator pressure surfaces.

### 6.2 What the v2 ADR ships

Three component bundles, one backend endpoint, one bundle manifest extension:

**A. Backend — platform-live MoneyTruth endpoint**
- `GET /api/cockpit/money-truth/{user_id}` returns Alpaca live snapshot:
  - equity, buying power, day delta, drawdown, exposure %
- Reads `platform_connections` row for Alpaca, decrypts API key, calls Alpaca account/positions endpoints
- Falls back to substrate (`_performance.md`) if Alpaca unreachable / not connected
- Render parity: API + Unified Scheduler should NOT have this endpoint (FE-only consumer; scheduler doesn't need it)
- Per ADR-236 scope guard 1, this is **explicitly an architecture gate-pass** — backend touch is the deferred-ADR work

**B. Bundle components — three new files in `web/components/library/`**
- `TraderMoneyTruth.tsx` — calls `/api/cockpit/money-truth/{user_id}`, renders brokerage shape
- `TraderSignalExpectancy.tsx` — reads `_performance.md` frontmatter for expectancy-by-signal-type
- `TraderPositions.tsx` — reads `_positions.md` for the positions table
- All three register in `LIBRARY_COMPONENTS` registry per the existing pattern

**C. alpha-trader `SURFACES.yaml` extension**
- `cockpit.money_truth.live_source: alpaca` (the new endpoint key)
- `cockpit.performance.components: [{kind: TraderSignalExpectancy, source: attribution_source}]`
- `cockpit.tracking.operational_state: {kind: TraderPositions, source: /workspace/context/portfolio/_positions.md}`

**D. Face component refactor — accept bundle overrides**
- `MoneyTruthFace.tsx`: when `live_source === 'alpaca'`, dispatch to `TraderMoneyTruth` via the registry. Else fall through to substrate-fallback render.
- `PerformanceFace.tsx`: when `cockpit.performance.components` declared, dispatch through registry. Else render kernel-default Reviewer calibration aggregate.
- `TrackingFace.tsx`'s `OperationalState` region: when `cockpit.tracking.operational_state` declared, dispatch through registry. Else render the link-out placeholder.

The face components stay structurally identical. They gain a **dispatch branch** that consults the bundle registry; everything else (substrate-fallback path, empty states, region layout) is preserved.

### 6.3 Snapshot modal convergence — folded in

ADR-241 moved Decisions to `/work`. SnapshotModal still has three tabs (Mandate / Review / Recent). Per the operator's "dedicated components and generic for kernel projects" framing, SnapshotModal's tabs should ALSO consume the same library components:

- SnapshotModal Mandate tab → render `MandateFace` directly (or a thinner variant)
- SnapshotModal Review tab → render the same Reviewer-Identity-or-Principles content TP's tab uses
- SnapshotModal Recent tab → narrative slice (already operates this way)

This is **structural simplification, not new code**. The components already exist (post-ADR-241); SnapshotModal just imports them instead of re-rendering. Item 10 (Cockpit ↔ snapshot convergence) collapses into ADR-242 as a side-effect of the bundle-component work being done first.

### 6.4 What ADR-242 does NOT do

- **Does not introduce alpha-commerce bundle overrides.** alpha-commerce is `status: deferred` per ADR-224; its bundle components ship when the program activates against a real consumer.
- **Does not change the four-face model.** ADR-228 universal-fixed-order stays.
- **Does not modify `LIBRARY_COMPONENTS` registry shape.** Three new entries added; registry pattern unchanged.
- **Does not introduce a new resolution site.** Reuses existing cockpit binding map; the bundle-supplied components are dispatched via the same registry as kernel-default chrome.
- **Does not amend ADR-225 invariants.** All five invariants stay.
- **Does not change `compositor.md`.** The doc already describes this state as the intended outcome; the doc was correct, the implementation was incomplete.

### 6.5 Phasing

Two commits, sized medium each:

**Phase 1 — Backend + bundle manifest extension** (~300 LOC)
- New endpoint + Alpaca client method
- alpha-trader `SURFACES.yaml` extension
- Composition resolver verified to merge the new fields
- Test gate: `api/test_adr242_phase1_cockpit_bundle_components.py`

**Phase 2 — Bundle components + face dispatch** (~500 LOC)
- Three new TSX files in `web/components/library/`
- Three face components extended with dispatch branches
- Registry entries
- SnapshotModal refactor (Item 10 convergence)
- Test gate: `api/test_adr242_phase2_face_dispatch.py`

Operator manual smoke required at Phase 2: cockpit shows live Alpaca equity in MoneyTruth face; PerformanceFace shows trader-shaped expectancy; TrackingFace shows positions table; SnapshotModal renders the same components inline.

---

## 7. Risks

**R1 — Backend boundary creep.** `/api/cockpit/money-truth/{user_id}` is a new endpoint. Adding endpoints "for cockpit" risks accumulating cockpit-coupled API surface. Mitigation: name the endpoint by **what it returns** (Alpaca account snapshot), not by **who consumes it** (cockpit). Future readers wanting Alpaca live equity for any reason can use the same endpoint.

**R2 — Bundle component naming conflicts.** Three new components have `Trader*` prefix. If alpha-commerce ships parallel components (`Commerce*`), the registry stays clean. But if a hypothetical future bundle wants a **shared** "PositionsTable" component, namespacing matters. Mitigation: `Trader*` prefix is the bundle's responsibility; future shared components can lift naming via a `@/lib/library/` reorganization if pressure surfaces. Today's three live where they live.

**R3 — Substrate-stub vs platform-live state machine.** When Alpaca is unreachable mid-session, the face needs to gracefully degrade from live to substrate. The fallback path already exists; the live path is new. Mitigation: `TraderMoneyTruth.tsx` consumes both — preferred live, falls back to substrate read on error. State indicator: "live" / "last reconciled {ts}" / "no platform connection."

**R4 — Operator-visible verification cost.** Phase 2's smoke test requires kvk's workspace to be in alpha-trader-program-active state. The operator gates between Phase 1 and Phase 2 are real; not all of it can be automated. Mitigation: Python regression gates cover structural correctness (component registered, manifest declares the binding, dispatch branch exists). Operator confirms visual.

**R5 — SnapshotModal reuse breaks chat-side semantics.** SnapshotModal is a `/chat` overlay (briefing archetype, ADR-198). Importing the four-face components risks behavioral coupling. Mitigation: SnapshotModal imports the **same components**, not the **CockpitRenderer wrapper**. Each face component (`MandateFace`, etc.) is self-contained per ADR-228 D5; they render correctly inside any container.

---

## 8. What this audit recommends, concretely

1. **Read this audit alongside compositor.md** to confirm the diagnosis.
2. **Draft ADR-242** as the v2 closer for the deferred ADR-228 Commits 3–5 + ADR-236 deferred Cluster B items.
3. **Phase 1 first** (backend endpoint + manifest extension). Smaller, validates the pattern works end-to-end before Phase 2's component scaffolding.
4. **Phase 2 includes Item 10 fold-in** (SnapshotModal reuse). Don't run convergence as a separate sub-ADR — it's structurally a no-cost addition once the components exist.
5. **Document the resulting state** in `compositor.md` §"How a bundle authors a Phase 3 override" — replace the *hypothetical* alpha-trader portfolio-review example with a *shipped* example.

The cockpit framing is correct. The seam is correct. The kernel/program boundary is correct. **What's missing is two days of bundle-component authorship for alpha-trader.** That work belongs in a sub-ADR; this audit names it as ADR-242.

---

## Appendix A — Component-shipped checklist

For ADR-242 implementation, the audit recommends explicitly tracking:

- [ ] Backend: `/api/cockpit/money-truth/{user_id}` endpoint
- [ ] Backend: Alpaca client method for account+positions snapshot
- [ ] Bundle: `TraderMoneyTruth.tsx` (registered)
- [ ] Bundle: `TraderSignalExpectancy.tsx` (registered)
- [ ] Bundle: `TraderPositions.tsx` (registered)
- [ ] Manifest: `cockpit.money_truth.live_source: alpaca`
- [ ] Manifest: `cockpit.performance.components: [...]`
- [ ] Manifest: `cockpit.tracking.operational_state: {...}`
- [ ] Face refactor: `MoneyTruthFace` dispatch branch
- [ ] Face refactor: `PerformanceFace` dispatch branch
- [ ] Face refactor: `TrackingFace.OperationalState` dispatch branch
- [ ] SnapshotModal: imports `MandateFace` for Mandate tab
- [ ] SnapshotModal: imports Principles content for Review tab
- [ ] Test gate Phase 1 (backend + manifest)
- [ ] Test gate Phase 2 (component registration + dispatch + face renders)
- [ ] Operator smoke: live Alpaca equity in cockpit
- [ ] Operator smoke: SnapshotModal renders identical content to /work cockpit

The list is the spec. Two phases, two commits, ~800 LOC total delta.
