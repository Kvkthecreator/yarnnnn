# Trader Cockpit Re-Write — Scoping Memo

> **Date**: 2026-04-29
> **Status**: Scoping memo. Precedes ADR-239 per ADR-236 Round 3 step 3.1.
> **Companion**: [ADR-236 umbrella](../adr/ADR-236-frontend-cockpit-coherence-pass.md), [ADR-228 cockpit](../adr/ADR-228-cockpit-as-delegation-posture.md), [ADR-225 compositor](../adr/ADR-225-compositor-layer.md), [ADR-237 chat role grammar](../adr/ADR-237-chat-role-based-design-system.md), [ADR-238 autonomy FE](../adr/ADR-238-autonomy-mode-fe-consumption.md).
> **Goal**: Surface the architectural questions ADR-239 needs to answer **before** drafting. The memo doesn't decide; it scopes.

---

## Why a memo precedes the ADR

ADR-236 Rule 8 (drafted-pair sequencing) requires sub-ADRs to draft just-in-time. For most items that's "draft → implement → land" in one session. Round 3 is the exception: Item 3 (trader cockpit re-write) has the largest surface in the pass, and ADR-228's deferred Phase 3–5 state means several decisions are still latent. Drafting a sub-ADR without first separating the architectural questions from the implementation work would produce an oversized ADR that's hard to land cleanly.

The memo's job: **inventory what's deferred, name the architectural questions, propose phasing**. ADR-239 then drafts against a known scope.

---

## What "trader cockpit" means concretely

The trader cockpit is the alpha-trader workspace's `/work` cockpit zone — the four-face delegation posture surface ADR-228 shipped Phase 1+2 of:

| Face | File | Source substrate | Status (per ADR-228) |
|---|---|---|---|
| Mandate | `web/components/library/faces/MandateFace.tsx` | `_shared/MANDATE.md`, `_shared/AUTONOMY.md`, bundle MANIFEST | **Phase 1+2 Implemented**; substrate stub fix shipped |
| Money truth | `web/components/library/faces/MoneyTruthFace.tsx` | substrate fallback only (no platform-live binding) | Phase 1+2 Implemented; **Phase 3 deferred** (Alpaca platform-live) |
| Performance | `web/components/library/faces/PerformanceFace.tsx` | `_performance.md`, Reviewer `decisions.md` | Phase 1+2 Implemented; **Phase 4 deferred** (sub-metrics + bundle wiring) |
| Tracking | `web/components/library/faces/TrackingFace.tsx` | pending decisions, operational state | Phase 1+2 Implemented; **Phase 4 deferred** (operational-state bundle wiring) |

Plus the **chat-side snapshot modal** at `web/components/chat-surface/SnapshotModal.tsx` which currently renders three independent tabs (Mandate / Review / Recent) with zero shared components with the cockpit faces.

---

## What's deferred — the inventory

### From ADR-228 directly

ADR-228's status text names five phases; Phases 3–5 are explicitly deferred:

- **Phase 3** — `MoneyTruth` platform-live binding via `/api/cockpit/money-truth/{workspace_id}`. Today the face reads from `/workspace/context/portfolio/_performance.md` (substrate fallback). Phase 3 wires Alpaca live.
- **Phase 4** — `PerformanceFace` sub-metrics + `TrackingFace` operational-state bundle wiring. Bundle SURFACES.yaml gains face-binding entries; bundle-supplied sub-component overrides land.
- **Phase 5** — final doc sync. Cockpit doc + per-ADR amendments.

### From the umbrella's audit (ADR-236 Item 3 inventory)

- **Convergence opportunity 1** — `/work` cockpit ↔ chat snapshot modal share zero components today. ADR-198 Briefing archetype admits convergence; no ADR has authorized it.
- **Convergence opportunity 2** — Tracking unification (Reviewer Decisions panel ↔ TrackingFace). Today `decisions.md` is rendered by `web/components/agents/reviewer/DecisionsStreamPane.tsx` (Reviewer detail view) AND by `TrackingFace` (cockpit). Two surfaces over the same Stream archetype.
- **Convergence opportunity 3** — Portfolio time-series component is unbuilt. Today MoneyTruthFace shows substrate fallback only.
- **Substrate transition consequence** — ADR-231 moved task-output substrate from YAML to natural-home `.md` paths. The trader-specific kernel surface was authored against the older substrate model and may have stale path references or assumptions.

### Now-relevant after Round 1+2

- **ADR-238 autonomy chip** is composer-level only. ADR-237's `MessageRow` exposes a row-level autonomy slot for future opt-in. The trader cockpit may want **face-level autonomy badges** (e.g., MoneyTruthFace shows "live trading enabled" when AUTONOMY = `bounded_autonomous` for the trading domain). This is a new surface ADR-237 didn't anticipate.
- **ADR-237 role grammar** is now available. Cockpit faces that surface chat-shaped content (last Reviewer verdict, agent activity) could compose with `MessageRenderer` instead of re-rendering. SnapshotModal "Recent" tab is the most obvious candidate.

---

## The architectural questions ADR-239 must answer

### Q1 — Is `/work` cockpit ↔ SnapshotModal convergence in scope?

**Why it matters:** today they're independent. SnapshotModal's three tabs (Mandate / Review / Recent) overlap conceptually with three of the four cockpit faces (Mandate / Performance / Tracking). One source of truth or two?

**The two answers:**
- **Converge** — SnapshotModal becomes a thin surface that wraps the same four face components in a modal layout. Single rendering path; chat-side and work-side agree by construction. Larger ADR-239 scope.
- **Defer** — SnapshotModal stays independent for now. Convergence becomes Item 10 in Round 5 (the umbrella already has it as Item 10 but gated on Items 1+3). Smaller ADR-239 scope.

**Memo recommendation:** **Defer.** ADR-239's scope is large enough without folding in SnapshotModal. Item 10 (Round 5) is the right home for convergence; ADR-239 ships face-level work first, Item 10 ships convergence after both ADR-237 and ADR-239 settle.

### Q2 — Should Tracking unification land in ADR-239 or stay separate?

**Why it matters:** `decisions.md` is rendered by both `DecisionsStreamPane` (Reviewer detail view) and `TrackingFace` (cockpit). ADR-198 calls Stream archetype; the unification is structural.

**The two answers:**
- **Unify in ADR-239** — extract a shared `DecisionsStream` component; both call sites compose with it. Cockpit gains nothing user-visible but loses duplication.
- **Defer** — Tracking unification is Item 10 territory (cockpit ↔ snapshot convergence). Same logic as Q1.

**Memo recommendation:** **Unify in ADR-239.** Unlike SnapshotModal (whose convergence touches modal-vs-page semantics), the `DecisionsStream` extraction is pure component lift — same shape ADR-237 just did for chat-role components. Belongs in cockpit work because it's where the duplication hurts.

### Q3 — Phase 3 (MoneyTruth platform-live) — is it ADR-239 scope or follow-up?

**Why it matters:** Phase 3 introduces a new API endpoint (`/api/cockpit/money-truth/{workspace_id}`), live Alpaca data fetching, fallback logic when the API key is missing or trading is disabled. That's substantive backend work. ADR-236 Scope Guard 1 says "no backend work beyond Item 6 500 fix" — Phase 3 violates that guard.

**The two answers:**
- **In ADR-239** — accept the scope guard violation explicitly with rationale (the guard exists to prevent merge collisions with ADR-235 in flight; ADR-235 is now Implemented). Phase 3 lands inside ADR-239.
- **Defer to ADR-241** — Phase 3 becomes its own sub-ADR after ADR-239 ships. ADR-239 stays FE-only.

**Memo recommendation:** **Defer to ADR-241** (or whichever number is next). Two reasons: (1) Phase 3 is independent in shape — it can stand alone as "MoneyTruth platform-live binding" without trader-cockpit-rewrite scope coupling; (2) keeping ADR-239 FE-only preserves the umbrella's scope guard discipline cleanly and matches ADR-237/238's FE-only sizing. The umbrella's "Trader cockpit re-write" name doesn't promise the platform-live binding; that's an honest separation.

### Q4 — Face-level autonomy badges — ADR-239 or future?

**Why it matters:** ADR-238 left a row-level autonomy slot in MessageRow (future opt-in). Trader cockpit faces could similarly opt-in. But faces are fundamentally different surfaces from chat rows.

**The two answers:**
- **In ADR-239** — extend the AutonomyMeta read pattern to faces. MoneyTruthFace gains an autonomy badge when trading domain is `bounded_autonomous`. Other faces follow.
- **Defer** — ADR-239 is FE coherence work on existing faces; face-level autonomy is a new affordance. Belongs in a face-affordance ADR after MoneyTruthFace's Phase 3 substrate work lands.

**Memo recommendation:** **Defer.** Face-level autonomy badges are speculative without the operator-feedback signal that they're useful. ADR-239 sticks to consolidation/cleanup; if face-level autonomy turns out to be needed, it's a small follow-up.

### Q5 — Substrate-transition cleanup (post-ADR-231 path drift)

**Why it matters:** trader cockpit faces may reference `/tasks/{slug}/outputs/...` paths that no longer exist post-ADR-231 (ADR-231 moved task outputs to natural-home `.md` paths under `/workspace/reports/{slug}/{date}/`). Smoke-checking each face's substrate-read paths is straightforward but needs to land somewhere.

**The two answers:**
- **In ADR-239** — audit each face's path references, fix any drift in same commit.
- **Defer to a hygiene commit** — small enough to land outside an ADR.

**Memo recommendation:** **In ADR-239.** Even small, the audit belongs in the cockpit-rewrite scope because it's part of "make the trader cockpit coherent against current substrate." Standalone hygiene commits accumulate slop; lumping it in keeps the audit visible.

### Q6 — Bundle wiring (ADR-228 Phase 4)

**Why it matters:** Phase 4 wires bundle-supplied sub-component overrides through SURFACES.yaml. Today MoneyTruthFace's autonomy summary formatter is hardcoded; ADR-228 envisioned bundle override (e.g., trader bundle supplies "Bounded autonomy on paper · $100/$500 day budget remaining" formatter). The compositor surface (ADR-225) supports it; the wiring isn't done.

**The two answers:**
- **In ADR-239** — wire the bundle override path; trader bundle supplies its own formatter; falls back to kernel default.
- **Defer** — bundle wiring is its own concern; ADR-239 stays focused on consolidation.

**Memo recommendation:** **Defer.** Bundle wiring touches `web/lib/compositor/`, registry types, and bundle MANIFEST schema — all infrastructure ADR-225 owns. The cleanest landing is a small ADR-225 amendment that wires the bundle override, separate from ADR-239's consolidation work.

---

## Proposed ADR-239 scope (after memo recommendations)

Given Q1–Q6 recommendations, ADR-239 ships:

### In scope

1. **`DecisionsStream` extraction** (Q2) — shared component used by both `DecisionsStreamPane` (Reviewer detail) and `TrackingFace` (cockpit). Singular Implementation rule honored: extract once, both call sites compose.
2. **Substrate-transition path audit** (Q5) — verify every face's substrate-read paths against post-ADR-231 reality; fix any drift.
3. **Face-level docstring updates** to cite ADR-237's role grammar where the face renders chat-shaped content (e.g., `TrackingFace`'s decisions list now uses `MessageRenderer` for each Reviewer entry rather than re-rendering inline).
4. **Test gate** — Python regression script asserting (a) `DecisionsStream` lives in one place, (b) face files import from it, (c) substrate paths match current ADR-231 conventions.

### Out of scope (deferred)

- SnapshotModal convergence → Item 10 (Round 5)
- MoneyTruth platform-live (ADR-228 Phase 3) → ADR-241 (separate sub-ADR)
- Face-level autonomy badges → defer; reassess after operator usage signals
- Bundle wiring (ADR-228 Phase 4) → ADR-225 amendment, separate
- PerformanceFace sub-metrics → roll into Phase 4 deferral

### Phasing

ADR-239 is sized to be a **single commit, not phased**. Per the recommendations above, the in-scope work is `DecisionsStream` extraction + path audit + 1-2 face docstring touch-ups. ~150–250 LOC delta. Sized similar to ADR-237.

If the path audit (Q5) reveals more drift than expected during implementation, ADR-239 phases at that moment per umbrella Rule 7 (legitimate phase split). Memo predicts no phasing needed.

---

## Out-of-scope honest declaration

ADR-239 will **not** make the trader cockpit feel "rewritten" in a user-visible way. It's a coherence pass — duplication removed, paths corrected, role grammar adopted where applicable. The user-visible "rewrite" comes from:

- **ADR-241** (proposed, separate) — MoneyTruth platform-live binding makes the face show real Alpaca account state.
- **ADR-225 amendment** (proposed, separate) — bundle wiring lets trader-specific summary formatters land per-bundle.
- **Round 5 Item 10** — cockpit ↔ snapshot convergence makes chat-side and work-side agree.

ADR-239 is the connective tissue between Round 2 (chat grammar settled) and these three follow-ups. Naming it that way honestly is part of why a memo precedes the ADR.

---

## What the memo doesn't decide (for ADR-239's drafting)

- The exact prop signature of `DecisionsStream` — implementation-time per Rule 7.
- Whether `MessageRenderer` composes inside `DecisionsStream` or alongside it — implementation-time.
- Test gate assertion count — implementation-time.
- Specific path drift items — surfaces during implementation.

---

## Recommendation to operator

Approve the memo's scoping recommendations (or redirect them) before ADR-239 drafts. Specific decision points:

1. ✅ Defer SnapshotModal convergence to Item 10 (Q1)
2. ✅ Unify Tracking in ADR-239 (Q2)
3. ✅ Defer MoneyTruth Phase 3 to ADR-241 (Q3)
4. ✅ Defer face-level autonomy badges (Q4)
5. ✅ Substrate-transition audit lands in ADR-239 (Q5)
6. ✅ Defer bundle wiring to ADR-225 amendment (Q6)

If operator agrees, ADR-239 drafts with ~250 LOC delta target, single commit. If operator redirects on any of the six, the memo updates and ADR-239 absorbs the redirected scope.

---

## Closing

The memo is the discipline ADR-236 Rule 8 + Round 3 sequencing requires for the largest item in the pass. Naming the questions before drafting prevents an oversized ADR-239 that mixes consolidation work with deferred-Phase-3 + bundle-wiring + convergence — three legitimate concerns that each deserve their own scope. ADR-239's job, post-memo, is to ship the consolidation work cleanly and let the follow-ups be follow-ups.
