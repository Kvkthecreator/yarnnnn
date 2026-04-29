# ADR-236 Validation Checkpoint — Round 0 + Round 1

> **Date**: 2026-04-29
> **Scope**: Manual smoke tests for everything ADR-236 has shipped through commit `c769e64` (Round 0 hygiene + Round 1 ADR-238). This checkpoint exists *before* Round 2 begins — validating what's deployed lets the operator catch regressions while the surface is small and the rationale is fresh.
> **Companion**: [ADR-236](../adr/ADR-236-frontend-cockpit-coherence-pass.md), [ADR-238](../adr/ADR-238-autonomy-mode-fe-consumption.md).
> **Run-time**: 10–15 minutes for the full sweep. Each section is independent and can be skipped if the relevant change wasn't shipped to your environment yet.

---

## Pre-flight

```bash
# Confirm you're on the validated commit
git log --oneline -8

# Expected to include:
#   c769e64 feat(adr-238): autonomy-mode FE consumption — shared parser + hook + chip
#   4f78901 docs(adr-236): harden umbrella with Rule 8 — drafted-pair sequencing
#   9969aa4 docs(adr-236): Item 7 — defer Settings extraction until first consumer surfaces
#   ca53c53 fix(adr-236): Item 6 — /api/workspace/nav 500 from dropped tasks columns
#   9aacd09 docs(adr-236): Item 5 — redirect-stub policy + docblock alignment
#   74b6f2f docs(adr-236): umbrella scoping ADR — frontend cockpit coherence pass

# Run the test gate
python api/test_adr238_autonomy_substrate.py
# Expected: 6/6 passing.

# (Optional) Full TS typecheck
cd web && npx tsc --noEmit --skipLibCheck
# Expected: clean.
```

If pre-flight fails, stop. Don't proceed to manual smoke until tests are green.

---

## Section 1 — Item 5 redirect-stub policy

**What we shipped**: codified policy in `web/lib/routes.ts`; tightened docblocks on `/memory` and `/system` stubs. Six stubs verified clean.

### 1.1 — Redirect smoke

In a logged-in browser session, paste each URL and confirm the redirect target. Each should land at the canonical route within < 2 seconds.

| URL | Expected target |
|---|---|
| `/orchestrator` | `/chat` |
| `/orchestrator?provider=slack&status=connected` | `/chat?provider=slack&status=connected` (params preserved) |
| `/team` | `/agents` |
| `/team?agent=reviewer` | `/agents?agent=reviewer` (params preserved) |
| `/overview` | `/work` |
| `/workfloor` | `/chat` |
| `/memory` | `/context?path=%2Fworkspace%2Fcontext%2F_shared%2FIDENTITY.md` |
| `/system` | `/settings?tab=system` |

**Pass criteria**: all 8 redirects land cleanly. No 404, no infinite loop, no stripped query params for the two that should preserve them.

**Fail signals to log**: a stub that doesn't redirect (would mean the file got deleted out of band); a stub that redirects to a non-canonical route (would mean ADR-236 Rule 4 — redirect-stub policy — needs amendment).

### 1.2 — Policy doc presence

Open `web/lib/routes.ts` and confirm the four numbered Redirect Stub Policy rules + the six-stub registry are present at the top.

**Pass criteria**: a future developer adding a new stub can find the policy without grep.

---

## Section 2 — Item 6 `/api/workspace/nav` 500 fix

**What we shipped**: removed dropped columns (`mode`, `essential`) from the `tasks` table SELECT in `api/routes/workspace.py::get_workspace_nav()`. FE type contract aligned.

### 2.1 — Files page loads cleanly

Navigate to `/context` (the Files surface). Watch the browser console.

**Pass criteria**:
- Left explorer panel renders a workspace tree.
- No `Failed to load explorer` text in the panel.
- No `APIError: API Error: 500` in the browser console for `/api/workspace/nav`.
- No `APIError: API Error: 500` in the browser console for `/api/workspace/tree`.

**Fail signals**:
- 500 in console → check the API logs for the actual exception. If it's still about `tasks.mode` or `tasks.essential`, the fix didn't deploy. If it's a different column, escalate to Tier 1 (the fix surfaced a deeper schema drift than Item 6 anticipated).
- Tree renders but no tasks listed under any section → that's expected if the workspace has no tasks; not a fix regression.

### 2.2 — Deep-link param preservation

Visit `/context?path=%2Fworkspace%2Fcontext%2F_shared%2FIDENTITY.md` directly.

**Pass criteria**: explorer navigates to IDENTITY.md and shows its content in the middle pane (or content viewer).

**Fail signals**: redirect to base `/context` (would mean deep-link parsing regressed); content viewer shows nothing (would mean the file is empty in your workspace, which is fine).

### 2.3 — Recurrence-label derivation

If your workspace has any tasks (recurrences), the Files explorer's task list should show their schedule labels (e.g., "Daily", "Weekly", "One-time") not "Recurring" / "Goal" / "Reactive" — those mode labels were the dropped column.

**Pass criteria**: schedule-derived labels render correctly per `recurrenceLabel()` in `web/types/index.ts`.

---

## Section 3 — Item 7 deferral

**What we shipped**: ADR-236 records the deferral; no code change. Verification is doc-only.

### 3.1 — Deferral is findable

Open `docs/adr/ADR-236-frontend-cockpit-coherence-pass.md`. Confirm Item 7 has a `**Deferred** (2026-04-29)` status badge and the deferral rationale block.

**Pass criteria**: a future-you searching "Settings extraction" in ADR-236 lands on the deferral, not silence.

---

## Section 4 — ADR-238 autonomy posture chip

**What we shipped**: shared parser at `web/lib/autonomy.ts`, refactored MandateFace, new chip in ChatPanel.

### 4.1 — Substrate state check

```bash
# Read the workspace's autonomy substrate. (Adjust user_id if needed.)
psql "$DB_URL" -c "
  SELECT path, content
  FROM workspace_files
  WHERE path = '/workspace/context/_shared/AUTONOMY.md'
  LIMIT 5;
"
```

Note your workspace's effective level. Three branches for the rest of this section:

#### Branch A — Workspace at default `manual`

This is the dominant case. The chip is hidden by design.

**Pass criteria**:
- Visit `/chat`. Above the composer, **no chip** is rendered.
- Visit `/work`. The Mandate face shows the autonomy line "manual" (sourced from the same parser).
- Verify both surfaces agree (single source of truth — the lib module).

#### Branch B — Workspace declares `bounded_autonomous` (e.g., alpha-trader)

**Pass criteria**:
- Visit `/chat`. Above the composer, a small pill chip renders with text matching `formatAutonomySummary` output — e.g., `bounded autonomous · ceiling $20,000`.
- Hover the chip — tooltip (`title` attribute) matches the chip text.
- Click the chip — **no-op** (this is the expected behavior in ADR-238; ADR-237 may later wire it).
- Visit `/work`. MandateFace shows the same summary string.
- Submit a chat message — chip stays visible during/after submit.

#### Branch C — Workspace declares `assisted` or `autonomous`

Same pattern as B but with the corresponding label (`assisted`, `autonomous`).

**Pass criteria**: chip renders with the right label; one source of truth across `/chat` and `/work`.

### 4.2 — Skeleton state (older workspaces or fresh signups)

If the workspace was created before ADR-217 and `AUTONOMY.md` doesn't exist, the hook returns `meta=null`.

**Pass criteria**:
- No console error in `/chat`.
- Chip is hidden (treated as default-manual).
- MandateFace renders "No autonomy declared" text.

### 4.3 — Backend regression gate

```bash
python api/test_adr238_autonomy_substrate.py
```

**Pass criteria**: `6/6 ADR-238 assertions passed.`

---

## Section 5 — Item 8.1 ChatFilterBar verification

**What we shipped**: nothing new in code; this is a verification of pre-existing ADR-219 Commit 5 wiring. Item 8.2 (recurring-rework) is gated on Round 2 and not validated here.

### 5.1 — Filter bar visibility toggle

On `/chat`:

1. By default, the filter bar should be **hidden**.
2. In the surface header (top-right of the chat panel), find the **filter icon** (small funnel SVG) next to the "Snapshot" button.
3. Click the filter icon — bar should reveal under the header.
4. Click again — bar hides.

**Pass criteria**: toggle cleanly opens/closes the bar with no scroll jank.

**If you can't find the filter icon**: that's a real legibility issue — log it for Item 8.2 (Round 5 mop-up).

### 5.2 — Weight filter

With the bar open:

1. Click `material` chip — the URL should update to `?weight=material`.
2. Messages in the panel should narrow to those whose `narrative.weight === 'material'` (or legacy messages defaulting to material).
3. Click `material` again to deselect — URL chip param cleared, all messages return.
4. Click both `material` and `routine` — both selected, OR-merge applies.

**Pass criteria**:
- URL updates synchronously with chip clicks.
- Message list narrows correctly on each toggle.
- Multi-select unions, doesn't intersect.

**Fail signals**:
- URL updates but message list doesn't change → likely a `narrative.weight` data issue (your messages don't carry the field). Not a filter bug.
- Message list goes empty when chips are set → expected if no messages match; the filter bar shows a "clear all" affordance.

### 5.3 — Identity filter

Same pattern as 5.2 but with the Identity row chips (You / YARNNN / Agent / Reviewer / System / External). Each chip filters by `msg.role`.

**Pass criteria**:
- Selecting "YARNNN" narrows to assistant messages.
- Selecting "User" narrows to your own messages.
- Multi-select unions correctly.

### 5.4 — Empty-result handling

Set a filter combination that matches zero messages (e.g., Weight=`housekeeping` + Identity=`Reviewer` if you've never had Reviewer housekeeping events).

**Pass criteria**:
- Message list goes empty cleanly.
- The filter bar still shows the active chips (you can clear them).
- A "clear all" affordance is visible so the operator isn't stranded.

**If clear-all isn't visible**: that's the legibility issue Item 8.2 is meant to address. Log as expected scope.

### 5.5 — Deep-link round-trip

Copy the URL with active filters (`?weight=material&identity=assistant`). Open it in a new tab.

**Pass criteria**: filters auto-apply; bar opens (URL has filters); chips render selected.

---

## Section 6 — Cross-surface integrity

### 6.1 — TS typecheck

```bash
cd web && npx tsc --noEmit --skipLibCheck
```

**Pass criteria**: zero errors.

### 6.2 — All ADR-236 commits in git log

```bash
git log --oneline --grep="adr-236\|adr-238" main
```

**Pass criteria**: 6 commits visible (umbrella, Item 5, Item 6, Item 7, Rule 8 hardening, ADR-238).

### 6.3 — ADR-235 coexistence check

Run the test gates from in-flight ADRs to confirm Round 1's commits didn't regress them.

```bash
# Whichever gates already exist for ADR-231, ADR-233, etc.
python api/test_adr231_runtime_invariants.py
python api/test_adr233_phase1_shape_prompts.py
python api/test_adr233_phase2_natural_home_preread.py
python api/test_adr234_chat_file_layer.py
python api/test_adr238_autonomy_substrate.py
```

**Pass criteria**: each gate green.

**Fail signals**: any gate failing under code that was supposed to be untouched → escalate immediately. ADR-238 explicitly did not touch ADR-231/233/234 territory.

---

## Outcome handling

### All sections pass

Round 1 is solid. Pause for Round 2 (gated on ADR-235 Implemented). The umbrella's Definition of Done shows Rounds 0 + 1 checked.

### Section X fails

Log the failure under the relevant ADR. Three escalation paths:

- **Code-level regression** (a fix that didn't deploy, a typecheck error, a 500 still surfacing) → revert the relevant commit; investigate; re-land. The umbrella's Round 0 / Round 1 boxes uncheck.
- **UX legibility issue** (ChatFilterBar is hard to discover; the chip is too quiet to notice) → log under Item 8.2 (Round 5 mop-up). Don't block Round 2.
- **Architectural surprise** (a pattern in ADR-238 doesn't compose cleanly with what ADR-237 needs) → escalate to ADR-236; amend the umbrella's Sequencing section before drafting ADR-237.

---

## What this checkpoint deliberately does NOT validate

- ADR-237 / ADR-239 / ADR-240 territory — none drafted yet, not in scope.
- ADR-235 (in flight in another session) — separate validation gate.
- Trader-cockpit Phase 3+ surfaces (ADR-228 deferred work) — Round 3 territory.
- "Make this recurring" rework — Item 8.2, gated on Round 2.
- Onboarding flow end-to-end — Round 4.

The checkpoint is bounded to what Round 0 + Round 1 actually shipped. Future rounds get their own checkpoint docs.

---

## Closing

This checkpoint is the natural mid-point of the ADR-236 pass — small enough to walk in one session, large enough to catch real regressions before Round 2 builds on top. Run it, log results, then we move on (or fix the gap surfaced) with confidence the foundation holds.
