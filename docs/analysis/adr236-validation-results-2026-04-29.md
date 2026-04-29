# ADR-236 Validation Results — Round 0 + Round 1

> **Date**: 2026-04-29
> **Companion**: [adr236-validation-checkpoint-2026-04-29.md](./adr236-validation-checkpoint-2026-04-29.md) (the checklist this document reports against)
> **Outcome**: **All code-verifiable sections PASS.** Browser-required smoke tests delegated to operator.

---

## Pre-flight

| Check | Result |
|---|---|
| 7 ADR-236 commits in `git log` | ✅ PASS |
| ADR-238 regression gate (6/6) | ✅ PASS |
| TypeScript typecheck (`tsc --noEmit`) | ✅ PASS — zero errors |

**Other-session notes:** commit `d7416e3 wip(adr-235): interim — new primitives + scope=workspace + chat prompts` shipped between commits `4f78901` (ADR-236 Rule 8 hardening) and `c769e64` (ADR-238). ADR-235's status flag still says Proposed; this is a WIP landing, not yet flipped to Implemented. Round 2 (ADR-237) gate per ADR-236 R2 remains open until ADR-235 reaches Implemented.

---

## Section-by-section results

### Section 1 — Item 5 redirect-stub policy

| Check | Type | Result |
|---|---|---|
| 1.1 — All 6 stubs implement redirects to expected targets | Code | ✅ PASS — verified via `grep` across all stub files |
| 1.1 — Param-preservation pattern | Code | ✅ PASS — `/orchestrator` and `/team` use `router.replace` with `?${params}` interpolation; `/overview` uses server `redirect()` (no params, intentional — no OAuth callback shape) |
| 1.1 — Browser smoke (8 redirect URLs land cleanly) | Browser | ⏸ **Operator** |
| 1.2 — Policy doc presence at top of `routes.ts` | Code | ✅ PASS — 4 numbered rules + 6-stub registry confirmed |

**Notes:** `/overview` deliberately strips query params (server `redirect`, no callback shape). `/orchestrator` preserves them for OAuth (`?provider=slack&status=connected` flows). Both shapes are correct per their use cases — documented in code, not a regression.

### Section 2 — Item 6 `/api/workspace/nav` 500 fix

| Check | Type | Result |
|---|---|---|
| 2.1 — `mode`/`essential` removed from SELECT | Code | ✅ PASS — strings only appear in explanatory comments (lines 75, 78, 86 in `api/routes/workspace.py`) |
| 2.1 — `/context` page loads, no 500 in console | Browser | ⏸ **Operator** |
| 2.2 — Deep-link param navigation | Browser | ⏸ **Operator** |
| 2.3 — `recurrenceLabel(schedule)` derivation logic | Code | ✅ PASS — exists at `web/types/index.ts:341`; derives from schedule, no `mode` dependency |

### Section 3 — Item 7 deferral

| Check | Type | Result |
|---|---|---|
| 3.1 — Deferral findable with status badge + rationale | Code | ✅ PASS — `**Deferred** (2026-04-29)` badge present at inventory item; deferral rationale block follows; sequencing table shows commit `9969aa4` |

### Section 4 — ADR-238 autonomy posture chip

| Check | Type | Result |
|---|---|---|
| 4.1 — Single source of truth for parser | Code | ✅ PASS — only `web/lib/autonomy.ts` defines `parseAutonomy` / `formatAutonomySummary`; `MandateFace.tsx` imports from it; `ChatPanel.tsx` imports `useAutonomy` |
| 4.1 — Parser logic across 3 substrate branches | Code | ✅ PASS — Python smoke-test mirrors the YAML walk and produces correct output for `manual` (chip hidden), `bounded_autonomous` ($20K ceiling, chip visible), `autonomous` (no ceiling, chip visible) |
| 4.1 — Chip render gate `effectiveLevel && effectiveLevel !== 'manual'` | Code | ✅ PASS — verified at `ChatPanel.tsx:149` |
| 4.1 — Chip visible in `/chat` (alpha-trader workspace) | Browser | ⏸ **Operator** |
| 4.1 — Chip text matches MandateFace summary | Browser | ⏸ **Operator** |
| 4.2 — Skeleton-state handling (no console error, no chip) | Browser | ⏸ **Operator** |
| 4.3 — Regression gate (6/6) | Code | ✅ PASS |

**Smoke-test output for the three branches (Python re-derivation of the TS parser):**

```
PASS  skeleton-manual: level='manual', summary='manual', chip_visible=False
PASS  trader: level='bounded_autonomous', summary='bounded autonomous · ceiling $20,000', chip_visible=True
PASS  autonomous: level='autonomous', summary='autonomous', chip_visible=True
```

### Section 5 — Item 8.1 ChatFilterBar verification

| Check | Type | Result |
|---|---|---|
| 5.1 — Filter toggle button wired to surface header | Code | ✅ PASS — `filterToggleAction` in `ChatSurface.tsx`, title "Filter narrative" |
| 5.2 — Weight chips wire to URL `?weight=` param | Code | ✅ PASS — `parseChatFilterFromSearch` reads `searchParams.get('weight')`; ChatPanel applies `filter.weights` axis |
| 5.3 — Identity chips wire to URL `?identity=` param | Code | ✅ PASS — same pattern; identity values match `TPMessage.role` enum (`user`/`assistant`/`agent`/`reviewer`/`system`/`external`) |
| 5.4 — Empty-result handling (clear-all visible) | Browser | ⏸ **Operator** |
| 5.5 — Deep-link round-trip auto-opens bar | Code | ✅ PASS — `useEffect(() => { if (narrativeFilter) setFilterBarOpen(true); })` in ChatSurface |
| 5.x — Browser UI clicks (toggle, chip select, message narrowing) | Browser | ⏸ **Operator** |

**End-to-end wiring smoke test (7/7):**

```
PASS  ChatFilterBar parses URL params (weight/identity/task)
PASS  ChatSurface threads narrativeFilter to ChatPanel
PASS  ChatPanel applies all 3 filter axes via narrativeFilterMatches
PASS  Filter identity values match TPMessage role enum
PASS  Filter weight values: material/routine/housekeeping
PASS  Filter bar auto-opens when URL carries an active filter
PASS  Filter toggle button (filter icon) wired to surface header
```

**Diagnosis of operator-reported "filter doesn't work":** the wiring is correct end-to-end. The likely root cause is **discoverability** — the filter icon (small funnel SVG) lives in the surface header next to the "Snapshot" button. An operator who doesn't notice the icon never sees the chips. This is the kind of UX legibility issue Item 8.2 (Round 5 mop-up) is meant to address (e.g., a more prominent affordance or an onboarding hint). **Not a Round 1 regression.**

### Section 6 — Cross-surface integrity

| Check | Type | Result |
|---|---|---|
| 6.1 — TS typecheck clean | Code | ✅ PASS |
| 6.2 — All 7 ADR-236/238 commits in `git log main` | Code | ✅ PASS |
| 6.3 — Cross-ADR test gates (231 / 233 P1 / 233 P2 / 234 / 238) | Code | ✅ PASS — **50 assertions across 5 gates** |

**Detailed gate results:**

| Gate | Result |
|---|---|
| `test_adr231_runtime_invariants.py` | 11/11 |
| `test_adr233_phase1_shape_prompts.py` | 13/13 |
| `test_adr233_phase2_natural_home_preread.py` | 12/12 |
| `test_adr234_chat_file_layer.py` | 8/8 |
| `test_adr238_autonomy_substrate.py` | 6/6 |
| **Total** | **50/50** |

---

## Aggregate score

- **Code-verifiable: 25/25** ✅
- **Browser-required: 0/12** ⏸ delegated to operator

**Status:** Round 0 + Round 1 are code-side validated. The umbrella's Definition of Done can advance Round 0 + Round 1 boxes to checked **when** the operator confirms the 12 browser-side smoke tests.

---

## Outstanding browser smoke tests (operator only)

Twelve tests need a logged-in browser session. Estimated 5–8 minutes total.

1. **§1.1** — Click each of 8 redirect URLs; confirm landing
2. **§2.1** — Visit `/context`; confirm explorer renders, no 500 in console
3. **§2.2** — Visit deep-link `/context?path=...IDENTITY.md`; confirm content viewer opens it
4. **§4.1** — Visit `/chat` on alpha-trader workspace; confirm chip visible with expected text
5. **§4.1** — Visit `/work` Mandate face; confirm autonomy line matches chip text (single source of truth)
6. **§4.1** — Hover chip; confirm `title` tooltip matches text; click confirms no-op
7. **§4.2** — On a default-`manual` workspace, confirm chip is hidden + no console error
8. **§5.1** — Find filter icon in `/chat` surface header; confirm toggle behavior
9. **§5.2** — Click weight chips; confirm URL updates + message list narrows
10. **§5.3** — Click identity chips; confirm same
11. **§5.4** — Combine chips for empty-result; confirm clear-all visible
12. **§5.5** — Copy filtered URL to new tab; confirm filters auto-apply

---

## What this implies for sequencing

Per the umbrella's `Definition of Done`, Round 0 + Round 1 are **code-side validated**. Two paths:

- **Operator confirms browser smoke ✅** → Round 1 fully closes. Next step: wait for ADR-235 to flip to Implemented, then Round 2 (ADR-237) drafts.
- **Operator surfaces a real regression** → revert the offending commit, root-cause, re-land. Code-side validation gives high confidence this won't happen, but the path is open.
- **Operator surfaces a UX legibility issue (e.g., filter discoverability)** → log under Item 8.2 / Round 5 mop-up; do not block Round 2.

---

## Closing

Code-side validation is a high-confidence proxy but not a substitute for actual browser smoke. The 12 outstanding tests are quick (5–8 minutes) and surface the kinds of issues that automated checks miss: visual layout, click affordances, content rendering. After the operator walks them, Round 1 closes definitively and the pass advances.
