# ADR-266 — `/workspace` Surface: Content Discipline + Program Drawer Collapse

> **Status**: **Proposed** (2026-05-11)
> **Authors**: KVK, Claude
> **Amends**: [ADR-244](ADR-244-workspace-settings-surface.md) (workspace settings surface), [ADR-245](ADR-245-frontend-kernel-three-layer-content-rendering.md) (L1/L2/L3 model)
> **Builds on**: [ADR-246](ADR-246-tp-meta-awareness-workspace-surface.md) (TP awareness of the workspace surface), [ADR-209](ADR-209-authored-substrate.md) (revision metadata)
> **Preserves**: ADR-244 D7 (chat is the edit surface — no inline edit affordances), ADR-245 (L2 parsers + L3 components), ADR-235 D1 (write primitives unchanged)

---

## Context

The `/workspace` page assembled by ADR-244 + ADR-245 is structurally sound — three reads, four cards, chat-as-edit-surface, multi-surface variant reuse — but operator-facing it reads as **a wall of mixed information with no clear posture**. Operator audit (KVK, 2026-05-11) surfaced concrete sloppiness:

**Block-by-block (current screenshot):**

1. **Active program card** renders `current_phase` as a bare uppercase token (`OBSERVATION`) with no key. Tagline is bundle-author voice, not operator-actionable. Deactivate is the most prominent button on the page.
2. **"Platform connections needed"** header renders even when all gaps are satisfied. The row reads `trading · requires trading · ✓ Connected` — the capability slug shown twice, the platform display name (Alpaca) absent.
3. **"Switch program"** list includes the currently-active program, doubling its visual weight. alpha-commerce shows two redundant hedges (`(Reference)` in title + `COMING SOON` badge). Bundle metadata prose surfaces directly to the operator.
4. **MandateCard** delivers a 200-word paragraph where the L2 parser was specced (per WORKSPACE-COMPONENTS.md §1) to extract a one-sentence Primary Action. Below it, 12 success-criteria bullets render at full prose weight with `**bold lead**` markdown leaking through as literal asterisks and inline backticks (`_operator_profile.md`) leaking as raw paths. ADR-244 D7's "no file paths visible" invariant is broken.
5. The page has **one verb** (`Refine in chat →`) at the bottom of each card, and no posture line at the top to tell the operator what the page is for or how editing works.

The root causes split into three distinct classes:

- **Class A — content scope**: program lifecycle (rare-but-catastrophic actions) and workspace setup (daily-relevant configuration) sit at equal visual weight on one page. The operator's actual relationship to them differs by an order of magnitude.
- **Class B — parser ↔ component contract drift**: `MandateCard` promises a one-sentence Primary Action; the bundle template's `## Primary Action` is a 200-word paragraph. The L2 parser correctly extracts what the section says; the L3 component has no graceful-degradation logic, so it dumps the full section as text. Markdown inside extracted fields is rendered as plain text rather than parsed or stripped.
- **Class C — copy hygiene**: capability slugs leak as user-facing strings (`trading requires trading`), bundle phase enums render bare (`OBSERVATION`), bundle taglines are developer-voice prose, contradictory headers ("needed → connected") render side by side.

Together: the page is **doing what its components were specced to do**, but the spec itself was incomplete on three fronts. This ADR closes those fronts.

---

## Decisions

### D1 — Single page, program lifecycle collapses into a drawer

`/workspace` stays one route. The four concept cards (Mandate, Autonomy, Principles, Identity/Brand) are the page's content. Program lifecycle (active program, switch, deactivate, capability gaps) collapses into a drawer at the bottom of the page, default-collapsed, with a single-line summary:

```
[ ▸  Running alpha-trader  ·  Alpaca connected  ·  Manage program ]
```

Rationale:
- Daily content (the four cards) gets full page weight.
- Lifecycle controls (touched ≤ once per workspace lifetime) are reachable in one click but no longer compete for attention.
- Operator can always see *which* program is active without expanding (single-line summary).
- Capability gaps surface in the summary line ("**1 platform needed**") when present, drawing attention only when something is wrong.

Rejected alternatives:
- Two routes (`/workspace` + `/workspace/program`) — premature; ADR-244 D6 already collapsed the OnboardingModal, splitting now would re-expand surface area without operator demand.
- Drawer expanded by default — defeats the purpose; the lifecycle weight is exactly what we're moving away from.

### D2 — Posture line under the page title

Single line, always present:

> *Your workspace's standing configuration. Read here, edit by chatting with YARNNN.*

Resets operator expectation: this page describes what's set, the chat changes it. No inline forms expected.

### D3 — MANDATE.md schema discipline (Primary Action = one sentence)

**`## Primary Action` is canonically one declarative sentence**, period. This is the schema YARNNN's chat agent enforces when writing MANDATE.md. The L2 parser extracts the first sentence as the headline; any prose after the first sentence is treated as supporting detail.

Schema (canonical headings, in order):
- `## Primary Action` — one sentence, the value-moving external write
- `## Success Criteria` — bullet list, terse (one line each)
- `## Boundary Conditions` — bullet list, terse (one line each)
- Other sections (operator-authored: edge hypothesis, rules of operation, etc.) are **valid** but not surfaced in the card. They are read by the LLM and visible in the source via "View full mandate" expand.

Bundle template alignment: the alpha-trader bundle's `MANDATE.md` is rewritten to honor this schema. The `## Primary Action` section becomes one sentence; the existing prose moves to `## What this operation is` (already exists) and `## Rules of operation` (already exists). No semantic loss; structural sharpening only.

YARNNN prompt update (`api/agents/prompts/chat/onboarding.py` or workspace profile): the mandate-write guidance names the schema explicitly. CHANGELOG entry per discipline 7.

### D4 — Graceful degradation in every L3 card

Every card defines its **schema-met path** (full structured render) and its **schema-absent path** (degraded but legible render). Never dump prose. Per-card matrix:

| Card | Schema-met render | Schema-absent render |
|---|---|---|
| **Mandate** | One-sentence Primary Action as callout + ≤3 top success criteria + boundary count + "View full mandate ▾" | First sentence of file as excerpt (truncated to 1 line) + "Mandate set but not in canonical structure — refine in chat to sharpen" + "View full ▾" |
| **Autonomy** | Already correct — discrete enum, no degradation needed | Falls back to "Manual" with explanatory tooltip |
| **Principles** | Per-domain ceiling + reject-condition count, expandable | "Principles set but no machine-parseable thresholds — refine in chat" + "View full ▾" |
| **Identity/Brand** | Already correct (uses excerpts) | Already handles empty + present states correctly |

"View full ▾" expands inline; renders the source file as prose with markdown parsed (not raw asterisks). No file paths visible per ADR-244 D7. The expansion is read-only — editing still routes through chat.

### D5 — Parser-to-component invariants (closes ADR-245 gap)

ADR-245 specced L2 parsers and L3 components but did not spec the **render contract** for fields the parser returns. Closes here:

- **Markdown in extracted fields must be either parsed or stripped.** If a field is "the bullet text", asterisks for bold are stripped (or rendered via a small inline-markdown renderer). Backticks for code are either rendered as `<code>` or stripped — never leaked as literal characters.
- **No raw file paths in operator-facing strings.** If MANDATE.md prose references `/_operator_profile.md`, the parser strips backtick-wrapped path tokens or the renderer hides them. Per ADR-244 D7.
- **No raw enum tokens in operator-facing strings.** `current_phase: "observation"` renders as "Paper-trading mode (no live capital)" via a per-program lookup; not as bare `OBSERVATION`. The lookup table lives in the bundle MANIFEST or ships with the bundle.

Implementation note: a small `web/lib/content-shapes/_render.ts` helper exports `stripInlineMarkdown(s: string): string` and `parseInlineMarkdown(s: string): ReactNode`. Cards pick which to use per field.

### D6 — Copy hygiene pass on the program block

Coordinated cleanup applied in the same commit as the layout change:

- **"Platform connections needed" header** renders only when at least one gap is unmet. When all are met, render a one-line affirmation `✓ All required platforms connected` in the drawer summary.
- **Platform display names** replace capability slugs in operator-facing strings. `trading` → `Alpaca`, `commerce` → `Lemon Squeezy`, etc. The mapping lives in a single registry `web/lib/platform-display.ts` (one source of truth — discipline 1).
- **"Switch program" list** excludes the currently-active program. If only the active program exists in the registry, the list collapses to "More programs coming soon" (single line).
- **Bundle phase token** renders via display lookup, not raw enum (per D5). For alpha-trader: `observation` → "Paper-trading (no live capital)", `paper_execution` → "Paper execution", `live_execution` → "Live trading".
- **Bundle taglines** stay (they're program identity), but the "(Reference)" parenthetical and "COMING SOON" badge are deduplicated — only one signal per row.

### D7 — Per-card "Last updated" via ADR-209 revision metadata

Each card surfaces the most-recent revision's `created_at` + `authored_by` for its source file. Format: small muted line under the card title:

> *Updated 3 days ago by you · 4 revisions*

For the merged Identity/Brand card: shows whichever sub-file is more recent.

This costs zero LLM. The data is already in `workspace_file_versions` (ADR-209). Surfaced via existing `api.workspace.listRevisions(path, limit=1)` call (already shipping per ADR-209 Phase 4). One additional batched call per card; folded into the bundle endpoint per D8.

### D8 — Single bundled endpoint replaces 6 file-fetches

Current: section calls `getState()` + 4 cards each call `getFile(path)` for 1–2 paths = 6 file reads + 1 state call on every page mount.

New: single endpoint `GET /api/workspace/setup-bundle` returns:

```typescript
{
  state: WorkspaceStateResponse,                     // existing shape from /workspace/state
  mandate:    { content: string, lastRevision: RevisionMeta | null },
  autonomyYaml: { content: string, lastRevision: RevisionMeta | null },
  principlesProse: { content: string, lastRevision: RevisionMeta | null },
  principlesYaml:  { content: string, lastRevision: RevisionMeta | null },
  identity:   { content: string, lastRevision: RevisionMeta | null },
  brand:      { content: string, lastRevision: RevisionMeta | null },
}
```

`WorkspaceConfigSection` calls once, parses each content via the existing L2 parsers, passes parsed `data` + `lastRevision` props to each card. Cards keep their self-fetch path as a fallback for the `/agents` reuse surface (preserves singular-implementation discipline — one card, two data-source modes selected by prop presence).

After activation/deactivation, refresh re-runs the bundle endpoint. The staleness window where cards show pre-fork content disappears.

---

## What this ADR does NOT do

- **Does not split into two routes.** D1 keeps `/workspace` as the single canonical home (ADR-244 commitment preserved).
- **Does not introduce inline edit forms.** ADR-244 D7 holds — chat is the edit surface for every field except autonomy level (which DelegationCard already handles via `setLevel()` direct mutation per WORKSPACE-COMPONENTS.md §2).
- **Does not add LLM calls on the read path.** Schema enforcement (D3) happens at write time in YARNNN's prompt, not at read time. Graceful degradation (D4) is pure-TS string handling. "Last updated" (D7) reads existing revision metadata.
- **Does not change ADR-209, ADR-235, or ADR-245's primary contracts.** This ADR amends ADR-244 (page content scope) and tightens ADR-245 (render contract).
- **Does not touch the chat overlay or cockpit faces.** Per ADR-245's L3-component reuse principle, those surfaces continue using the same cards at `compact` / `headline` variants. D4 graceful degradation applies to all variants automatically.

---

## Implementation Plan

Four phases, each landing in a green state.

### Phase 1 — Backend: bundled endpoint + revision surfacing

- Add `GET /api/workspace/setup-bundle` in `api/routes/workspace.py` returning the shape from D8. Parallel `asyncio.gather` for all 6 file reads + state. One Pydantic response model. Single endpoint per discipline 1 — does not cohabit with the 6 individual file routes (those stay because other surfaces consume them).
- Each file response includes `lastRevision: { id, created_at, authored_by, message } | null` derived from `workspace_file_versions` (ADR-209). One additional query per file; batched.
- `web/lib/api/client.ts` — add `api.workspace.getSetupBundle()`.

### Phase 2 — Frontend: parsers + render helpers + per-card data props

- Add `web/lib/content-shapes/_render.ts` with `stripInlineMarkdown()` + `parseInlineMarkdown()`. Pure TS, no React in `strip*`; React node return in `parse*`.
- Add `web/lib/platform-display.ts` — single registry mapping capability slug → operator-facing platform name. Used by D6 program block + capability-gap rendering.
- Add `web/lib/program-phase-display.ts` — single registry mapping `(programSlug, phase)` → human label. Bundle MANIFEST is the source-of-truth long-term; this registry is a thin lookup that reads from the bundle metadata returned by `/programs/activatable`.
- Update `MandateCard` to:
  - Accept optional `data?: MandateData` + `lastRevision?: RevisionMeta` props (falls back to self-fetch when absent).
  - Render the schema-met path with one-sentence Primary Action callout + ≤3 success criteria (markdown-stripped via D5).
  - Render the schema-absent path with first-sentence excerpt + "Mandate set but not in canonical structure" hint + "View full ▾".
  - Surface `lastRevision` as muted timestamp line under the title (D7).
- Update `PrinciplesCard`, `IdentityBrandCard`, `DelegationCard` to accept `data?` + `lastRevision?` props (preserves existing self-fetch path).
- `WorkspaceConfigSection`: refactored to call `getSetupBundle()` once, parse each content via existing L2 parsers, pass `data` + `lastRevision` to each card.

### Phase 3 — Frontend: layout + program drawer + posture line

- Add `<WorkspacePostureLine>` component — single line under PageHeader.
- Extract `<ProgramLifecycleDrawer>` from the inline 150-LOC block in `WorkspaceConfigSection.tsx`. Default collapsed. Single-line summary uses display-name registry (D6). Capability-gap count shown in summary when > 0.
- Reorder section: posture line → 4 concept cards → program drawer (bottom).
- Apply D6 copy hygiene throughout: header conditional rendering, switch-list filter, phase token via lookup.

### Phase 4 — Bundle template + YARNNN prompt + docs sync

- Rewrite `docs/programs/alpha-trader/reference-workspace/context/_shared/MANDATE.md`'s `## Primary Action` section to a single declarative sentence. Existing prose moves to `## What this operation is` (already in template) — no semantic loss.
- YARNNN workspace prompt: add explicit MANDATE.md schema guidance per D3. `api/prompts/CHANGELOG.md` entry.
- `docs/design/WORKSPACE-COMPONENTS.md` v1.1: add D4 graceful-degradation matrix, D5 render-contract invariants, D7 revision metadata, D8 bundled-endpoint pattern.
- `docs/adr/ADR-244-workspace-settings-surface.md`: status note pointing to ADR-266 amendment.
- `docs/adr/ADR-245-frontend-kernel-three-layer-content-rendering.md`: status note pointing to ADR-266 D5 closure.

---

## Acceptance

- `/workspace` page mounts with one HTTP call (`getSetupBundle()`) instead of 7. Verified via DevTools network panel.
- MandateCard shows a one-sentence Primary Action callout, never a 200-word paragraph. When the source file lacks a one-sentence Primary Action, the schema-absent fallback renders without prose dump.
- No `**bold**`, no inline backtick paths, no raw enum tokens visible anywhere on the page.
- Program lifecycle collapses to a single line at the bottom of the page when no capability gaps exist; expands inline on click.
- Switch-program list excludes the active program. If no other activatable programs exist, the list renders "More programs coming soon" (one line).
- Each card shows a "Last updated" line driven by `workspace_file_versions` data.
- Per-test pattern: one regression gate `api/test_adr266_workspace_surface.py` covering: bundle endpoint shape, schema-met vs schema-absent parser output for MANDATE.md, capability-gap copy hygiene, switch-list active-program filter, posture-line presence in rendered HTML.

---

## Dimensional Classification (FOUNDATIONS v6.0)

- **Channel** (Axiom 6, primary): the operator-facing surface gets clearer hierarchy + cleaner copy. Per Derived Principle 12 (Channel legibility gates autonomy), the page's legibility is upstream of operator trust in the workspace's standing config.
- **Substrate** (Axiom 1): no substrate change. MANDATE.md schema is *enforced at write time* by YARNNN's prompt, not enforced by primitive validation — operators who hand-edit non-canonical content still get graceful degradation.
- **Mechanism** (Axiom 5): D8 bundled endpoint is at the deterministic end of the spectrum (parallel file reads, no judgment). D3 schema enforcement is a prompt-side guidance, also deterministic from the operator's perspective.

---

## Cross-references

- [ADR-244](ADR-244-workspace-settings-surface.md) — Workspace Settings Surface (this ADR's primary parent; D1 + D7 amended)
- [ADR-245](ADR-245-frontend-kernel-three-layer-content-rendering.md) — Three-Layer Content Rendering (this ADR closes the render-contract gap via D5)
- [ADR-246](ADR-246-tp-meta-awareness-workspace-surface.md) — TP awareness of workspace surface (downstream — TP prompt update for D3 schema lives in ADR-246's prompt module)
- [ADR-209](ADR-209-authored-substrate.md) — Authored Substrate (D7 surfacing reads existing revision metadata)
- [docs/design/WORKSPACE-COMPONENTS.md](../design/WORKSPACE-COMPONENTS.md) — Concept component catalog (v1.1 update lands with this ADR)
