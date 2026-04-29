# ADR-239: Trader Cockpit Coherence Pass — Decisions Parser Unification

> **Status**: **Implemented** (2026-04-29, single commit). Round 3 of the ADR-236 frontend cockpit coherence pass — the third Tier 1 sub-ADR. Test gate `api/test_adr239_decisions_parser_unification.py` 6/6 passing. TypeScript typecheck clean. Cross-ADR regression check 63/63 across seven gates (231 + 233 P1 + 233 P2 + 234 + 237 + 238 + 239). CHANGELOG entry `[2026.04.29.N]` recorded. **Scope smaller than the memo predicted** — implementation-time investigation found two of the memo's three in-scope items were either already clean (Q5 path audit) or speculative (MessageRenderer composition); net change is parser unification only. Memo–reality drift logged in §"What implementation-time investigation found".
> **Date**: 2026-04-29
> **Authors**: KVK, Claude
> **Dimensional classification**: **Mechanism** (Axiom 5) primary — collapses two parsers over the same substrate file into one source of truth. **Channel** (Axiom 6) secondary — the affected surfaces are cockpit faces (`/work`) and the Reviewer detail view (`/agents`).
> **Builds on**: ADR-194 v2 (Reviewer substrate — Implemented), ADR-198 (Surface Archetypes — Stream archetype defined), ADR-228 (Cockpit as Delegation Posture — Implemented Phase 1+2), ADR-231 (Task Abstraction Sunset — Implemented), ADR-235 (UpdateContext Dissolution — Implemented), ADR-236 (Frontend Cockpit Coherence Pass — Round 2 closed), ADR-237 (Chat Role-Based Design System — Implemented), ADR-238 (Autonomy-Mode FE Consumption — Implemented).
> **Companion memo**: [docs/analysis/trader-cockpit-rewrite-2026-04-29.md](../analysis/trader-cockpit-rewrite-2026-04-29.md). Memo's six recommendations stand; this ADR implements the in-scope subset and records what implementation found different from the memo.
> **Composition note**: Future trader-cockpit work (MoneyTruth platform-live binding, bundle wiring, cockpit↔snapshot convergence) lands as separately-scoped follow-ups — see "Out of scope" below.
> **Preserves**: FOUNDATIONS axioms 1–9, ADR-141 (execution layers), ADR-156 (single intelligence layer), ADR-159 (filesystem-as-memory), ADR-194 v2 (Reviewer substrate semantics unchanged), ADR-209 (Authored Substrate attribution), ADR-228 (four-face cockpit shape), ADR-237 (chat role grammar — independent surface).

---

## Context

The ADR-236 audit (2026-04-29) named "trader cockpit re-write" as Item 3 — the largest item in the pass. ADR-236 Rule 8 + Round 3 sequencing required a **scoping memo before drafting** because Item 3 had the largest surface and ADR-228's deferred Phase 3–5 state meant several decisions were latent.

The companion memo (`docs/analysis/trader-cockpit-rewrite-2026-04-29.md`, commit `143af62`) asked six architectural questions and proposed:

| Q | Recommendation | ADR-239 in-scope? |
|---|---|---|
| Q1 | Defer SnapshotModal convergence to Item 10 | No |
| Q2 | Unify Tracking (DecisionsStream extraction) in ADR-239 | **Yes** |
| Q3 | Defer MoneyTruth Phase 3 platform-live to ADR-241 | No |
| Q4 | Defer face-level autonomy badges | No |
| Q5 | Substrate-transition path audit lands in ADR-239 | **Yes** |
| Q6 | Defer bundle wiring to ADR-225 amendment | No |

Memo predicted ~250 LOC delta from Q2 + Q5 + face-level docstring touch-ups citing ADR-237.

### What implementation-time investigation found

Per ADR-236 R5 (architectural surprise during a sub-ADR's drafting requires the umbrella to absorb the redirect honestly), three findings change the in-scope shape:

**Finding 1 — Memo's framing of Q2 was wrong about which face has the duplication.**

Memo claimed `TrackingFace` re-renders Reviewer decisions inline, duplicating `DecisionsStreamPane`. Verified by reading the files:

- `TrackingFace.tsx` renders **pending action_proposals** (proposal queue with inline approve/reject) and **recent narrative activity** (list items with summaries linking to `/work`). It does **NOT** parse `/workspace/review/decisions.md` at all.
- The actual second consumer of `decisions.md` is `PerformanceFace.tsx`, which has its own inline `parseDecisions()` function returning a `ReviewerCalibration` aggregate (different shape from `DecisionsStreamPane`'s `ReviewerDecision[]` list).

The duplication is real but lives between `web/lib/reviewer-decisions.ts::parseDecisions` and `PerformanceFace.tsx::parseDecisions` (inline). Two parsers over one substrate file.

**Finding 2 — Q5 substrate-transition path audit found zero drift.**

Memo predicted the trader cockpit might reference stale `/tasks/{slug}/outputs/` paths post-ADR-231. Grep across `web/components/library/faces/*.tsx` returned zero `/tasks/` references. The faces consume substrate via `/workspace/context/`, `/workspace/review/`, and `api.narrative.byTask()` — all current per ADR-231 / ADR-219 conventions. Zero work needed for Q5.

**Finding 3 — Memo's docstring-touch-ups citing ADR-237 role grammar do not apply.**

Memo suggested `TrackingFace`'s `RecentActivity` component might compose with `MessageRenderer` (ADR-237). Verified by reading the implementation: `RecentActivity` renders narrative entries as **compact list items with summaries linking to `/work`**, not chat bubbles. Using `MessageRenderer` would be the wrong shape — the cockpit's compact list view is intentional and chat-bubble rendering would lose the link-out affordance. ADR-237's role grammar is a chat-surface concern; it does not apply to cockpit list views.

### Net effect

The memo's predicted ~250 LOC delta shrinks to ~60–80 LOC. ADR-239 ships parser unification only. The other two memo recommendations land as **verified-clean / verified-not-applicable** notes in this ADR, not as separate work.

This is the discipline ADR-236 R5 anticipated: a sub-ADR's drafting absorbs the redirect rather than rubber-stamping the memo's prediction.

---

## Decision

### D1 — `parseDecisions` becomes the single FE parser of `decisions.md`

`web/lib/reviewer-decisions.ts` already exports the canonical parser:

```ts
export function parseDecisions(content: string): ReviewerDecision[];
```

Returning `ReviewerDecision[]` — a list of typed decision entries.

`PerformanceFace.tsx` currently has an **inline `parseDecisions(content): ReviewerCalibration`** that duplicates parsing work and produces an aggregate shape. ADR-239 splits this into two layers:

1. **Parsing stays in `reviewer-decisions.ts`** — returns `ReviewerDecision[]`. One source of truth.
2. **Calibration aggregation moves to a new helper `aggregateReviewerCalibration(decisions: ReviewerDecision[]): ReviewerCalibration`** — pure function over the parser output. Lives in `reviewer-decisions.ts` alongside `parseDecisions`. Lifted from `PerformanceFace`'s inline logic; same calibration shape.

`PerformanceFace.tsx`:
- Deletes inline `parseDecisions(content): ReviewerCalibration`.
- Imports `parseDecisions` and `aggregateReviewerCalibration` from `@/lib/reviewer-decisions`.
- Calls them in sequence: `aggregateReviewerCalibration(parseDecisions(content))`.

The visual output is unchanged — same `ReviewerCalibration` shape, same render. The substrate read is unchanged — `decisions.md` is still the source. Only the parsing path consolidates.

### D2 — `ReviewerCalibration` shape moves to `reviewer-decisions.ts`

The `ReviewerCalibration` interface currently lives inline in `PerformanceFace.tsx`. ADR-239 lifts it to `reviewer-decisions.ts` as an exported type so future consumers (Round 5 Item 10 cockpit↔snapshot convergence is the obvious one) can import it.

This is a small lift — one interface definition moves modules. No prop-shape churn.

### D3 — No path drift to fix (Q5 verified clean)

`web/components/library/faces/*.tsx` and `web/components/agents/reviewer/DecisionsStreamPane.tsx` all consume current substrate paths per ADR-231 / ADR-219. Verified via grep; documented as a regression guard in the test gate.

### D4 — No `MessageRenderer` composition (Q4 finding 3)

`TrackingFace::RecentActivity` keeps its compact list rendering. ADR-237's role grammar is a chat-surface concern; cockpit list views are a different rendering shape. Documented as a non-decision in this ADR so future-me reading the memo + the ADR finds the rationale.

---

## What this ADR does NOT do

- **Does not touch SnapshotModal.** Q1 deferred to Item 10. Round 5 territory.
- **Does not introduce platform-live MoneyTruth binding.** Q3 deferred to ADR-241 (separate sub-ADR, future round).
- **Does not add face-level autonomy badges.** Q4 deferred indefinitely; reassess after operator usage signals.
- **Does not wire bundle-supplied face overrides.** Q6 deferred to a future ADR-225 amendment.
- **Does not modify any face's substrate-read paths.** Verified clean per Q5.
- **Does not modify `DecisionsStreamPane.tsx`.** Already uses `parseDecisions` from `reviewer-decisions.ts`. No change needed.
- **Does not introduce a JS test runner.** Same regression-script pattern as ADR-237 / ADR-238 per ADR-236 Rule 3.
- **Does not change the substrate file format of `/workspace/review/decisions.md`.** Parser is reading-only.

---

## Implementation

### Files modified (2)

- `web/lib/reviewer-decisions.ts`
  - Add `ReviewerCalibration` interface (lifted verbatim from `PerformanceFace`).
  - Add `aggregateReviewerCalibration(decisions: ReviewerDecision[]): ReviewerCalibration` — lifted from `PerformanceFace`'s inline `parseDecisions` body, refactored to consume the canonical parser's output. Pure function.
- `web/components/library/faces/PerformanceFace.tsx`
  - Delete inline `ReviewerCalibration` interface.
  - Delete inline `parseDecisions(content): ReviewerCalibration` function.
  - Import `parseDecisions`, `aggregateReviewerCalibration`, `type ReviewerCalibration` from `@/lib/reviewer-decisions`.
  - Replace the call site `setCalibration(parseDecisions(decisionsContent))` with `setCalibration(aggregateReviewerCalibration(parseDecisions(decisionsContent)))`.

### Files created (1)

- `api/test_adr239_decisions_parser_unification.py` — Python regression gate.

### Files NOT modified

- `web/components/agents/reviewer/DecisionsStreamPane.tsx` — already uses canonical parser.
- `web/components/library/faces/{Mandate,MoneyTruth,Tracking}Face.tsx` — verified clean per Q5; no path drift; no parser duplication; no `MessageRenderer` retrofit per Q4 finding.
- `api/services/*` — no backend change.
- ADR predecessors — Rule 2 historical preservation.

### Test gate

`api/test_adr239_decisions_parser_unification.py` asserts six invariants:

1. `web/lib/reviewer-decisions.ts` exports `parseDecisions`, `aggregateReviewerCalibration`, `ReviewerCalibration`.
2. `web/components/library/faces/PerformanceFace.tsx` no longer contains the string `function parseDecisions(` (regression guard against re-inlining).
3. `web/components/library/faces/PerformanceFace.tsx` no longer contains the string `interface ReviewerCalibration {` (regression guard).
4. `web/components/library/faces/PerformanceFace.tsx` imports from `@/lib/reviewer-decisions`.
5. **Q5 path audit regression guard** — `grep "/tasks/{" web/components/library/faces/` returns zero matches across all face files (catches future drift if a face accidentally references the legacy task path).
6. `web/components/agents/reviewer/DecisionsStreamPane.tsx` continues to import `parseDecisions` from `@/lib/reviewer-decisions` (regression guard against the canonical parser being moved or renamed without updating this consumer).

Combined gate target: 6/6 passing.

### Render parity

| Service | Affected | Why |
|---|---|---|
| API | No | FE-only. |
| Unified Scheduler | No | FE-only. |
| MCP Server | No | FE-only. |
| Output Gateway | No | Untouched. |

**No env vars. No schema. No DB migrations.**

### Singular Implementation discipline

- After ADR-239, exactly one parser exists for `/workspace/review/decisions.md` content (`parseDecisions` in `reviewer-decisions.ts`). The `PerformanceFace` inline copy is deleted.
- After ADR-239, exactly one definition of `ReviewerCalibration` exists (in `reviewer-decisions.ts`). The `PerformanceFace` inline interface is deleted.
- The `aggregateReviewerCalibration` helper has one implementation. Future consumers (Round 5 Item 10) compose with it; do not re-derive.

---

## Risks

**R1 — Calibration shape regression.** Lifting `parseDecisions(content): ReviewerCalibration` from inline to `aggregateReviewerCalibration(decisions): ReviewerCalibration` is a refactor that crosses a layer boundary. Mitigation: the inner logic is lifted verbatim, only the input shape changes (string → ReviewerDecision[]). Test gate assertions catch the import path; visual smoke confirms the calibration display renders identically. PerformanceFace is the only consumer; one call site to verify.

**R2 — `ReviewerDecision` field coverage for calibration.** `ReviewerDecision` (the canonical parser output) may not carry every field the inline calibration parser used (e.g., specific identity sub-classifications). Mitigation: implementation reads `PerformanceFace`'s inline parser body and threads any missing fields through `parseDecisions` first if needed (extending the canonical parser is preferable to keeping a parallel parser). If `parseDecisions` needs a field extension, ADR-239 lands the extension as part of D1.

**R3 — Memo–reality drift logged but not retroactively edited.** The companion memo predicted three pieces of work; reality found one. Per ADR-236 Rule 2 (historical preservation), the memo stays as authored. Mitigation: this ADR's "What implementation-time investigation found" section is the canonical record; future-me reading the memo finds the redirect via this ADR's link.

**R4 — `aggregateReviewerCalibration` API surface.** Picking the right function name + signature affects future composability. Mitigation: name follows the verb-noun convention common in the codebase (`formatActionType`, `classifyIdentity`, etc.); signature accepts `ReviewerDecision[]` and returns `ReviewerCalibration` — a pure transformation, no I/O, no React.

**R5 — Operator visual regression.** Calibration display in `PerformanceFace` is operator-visible. Mitigation: calibration logic is lifted verbatim; visual smoke required on the alpha-trader workspace before commit. Manual smoke is the visual gate — the test gate catches structural drift only.

---

## Phasing

Single commit, sized small (~60–80 LOC delta total). Linear:

1. Lift `ReviewerCalibration` interface to `reviewer-decisions.ts`.
2. Author `aggregateReviewerCalibration` in `reviewer-decisions.ts`, lifted from `PerformanceFace` inline logic.
3. Refactor `PerformanceFace.tsx` — import + delete inline parser + adjust call site.
4. Author `api/test_adr239_decisions_parser_unification.py` — 6 assertions.
5. Run all gates (ADR-231 / ADR-233 P1 / ADR-233 P2 / ADR-234 / ADR-237 / ADR-238 / ADR-239).
6. Add `[2026.04.29.N]` CHANGELOG entry.
7. Atomic commit + push.

---

## Closing

ADR-239 is small. The companion memo predicted larger; implementation-time investigation found a cleaner state than the memo assumed. ADR-236 R5's discipline applies: this ADR honors what's actually there rather than what the memo predicted. The user-visible "trader cockpit re-write" the memo named honestly remains a follow-up: ADR-241 (platform-live), ADR-225 amendment (bundle wiring), Round 5 Item 10 (cockpit↔snapshot convergence) are the surfaces where "rewrite-feel" delivery lives.

What ADR-239 does deliver: one parser per substrate file. The `decisions.md` substrate now has exactly one TS parser, exactly one calibration aggregator, and two consumers (`DecisionsStreamPane` for full-stream display, `PerformanceFace` for calibration aggregate) composing with the same source. Singular Implementation rule 1 honored at the substrate-parser layer.
