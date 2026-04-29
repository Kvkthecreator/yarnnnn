# ADR-238: Autonomy-Mode FE Consumption — Shared Parser, Hook, First Consumer

> **Status**: **Implemented** (2026-04-29, single commit). Round 1 of the ADR-236 frontend cockpit coherence pass — first independent Tier 1 sub-ADR. Test gate `api/test_adr238_autonomy_substrate.py` 6/6 passing. TypeScript typecheck clean. CHANGELOG entry `[2026.04.29.8]` recorded.
> **Date**: 2026-04-29
> **Authors**: KVK, Claude
> **Dimensional classification**: **Mechanism** (Axiom 5) primary — promotes the substrate-read pattern from a face-local helper into a shared FE primitive. **Substrate** (Axiom 1) secondary — `_shared/AUTONOMY.md` is the canonical autonomy substrate per ADR-217, and this ADR is the first non-cockpit consumer of that substrate.
> **Builds on**: ADR-217 (Workspace Autonomy Substrate — Implemented 2026-04-24, defines `_shared/AUTONOMY.md` schema), ADR-228 (Cockpit as Delegation Posture — Implemented 2026-04-28, contains the existing inline `parseAutonomy` + `formatAutonomySummary` in `MandateFace.tsx`), ADR-236 (Frontend Cockpit Coherence Pass — Implemented 2026-04-29, this ADR is Round 1 step 1).
> **Extends**: ADR-217 (FE consumption layer made explicit; substrate definition unchanged), ADR-225 (compositor surface gains a substrate-aware FE primitive but no new component-registry kind).
> **Preserves**: FOUNDATIONS axioms 1–9, ADR-141 (execution layers), ADR-156 (single intelligence layer — no new LLM call introduced), ADR-176 (universal specialist roster), ADR-194 v2 (Reviewer substrate), ADR-209 (Authored Substrate — autonomy reads route through `/api/workspace/file`, attribution path unchanged), ADR-216 (orchestration vs judgment), ADR-228 (four-face cockpit — `MandateFace` continues to render the same summary, just sources it from the shared module), ADR-229 (autonomy as post-judgment binding gate, server-side; this ADR does not gate verdicts).
> **Composition note for future sub-ADRs**: ADR-237 (Round 2, chat role-based design system) will accept autonomy posture as a row-level property — e.g., a Reviewer-row in chat may render differently when AUTONOMY ≥ bounded_autonomous than when manual. ADR-237 imports from `@/lib/autonomy` rather than re-deriving. ADR-240 (Round 4, onboarding-as-activation) consumes autonomy at activation time to surface "your workspace defaults to manual; you can change this later" framing during the post-fork-pre-author state.

---

## Context

ADR-217 established `/workspace/context/_shared/AUTONOMY.md` as the canonical workspace-scoped autonomy substrate, scaffolded by `workspace_init` with a generic-default-manual posture. ADR-228 Phase 2 wired the first consumer — `MandateFace.tsx` — which inlined a YAML frontmatter parser (`parseAutonomy`) and a summary formatter (`formatAutonomySummary`) to render the autonomy posture inside the cockpit's MandateFace card.

Since then, four legitimate downstream needs have been recorded in ADR-236:

1. **Chat surface autonomy awareness** (Item 1, future ADR-237). The chat role-based design system frames role-specific message rendering. Autonomy posture is a workspace-wide row property — for example, a `ProposalCard` rendered when AUTONOMY = `bounded_autonomous` should look different than the same card rendered when AUTONOMY = `manual`. The card needs a substrate-aware lookup.
2. **Composer affordance gating** (this ADR's first consumer). When a workspace declares `autonomous` mode, the chat composer should expose that posture inline so the operator can see it without leaving Chat. Today this requires opening Mandate Face in `/work` cockpit.
3. **Autonomy-aware modal confirmations** (future, Round 5 mop-up). For SUPERVISED mode, action-confirmation modals should attach a one-line summary of why approval is required. The summary text is the autonomy posture.
4. **Onboarding surface** (Item 4, future ADR-240). Activation-flow YARNNN prompts should know whether autonomy substrate has been authored beyond skeleton.

ADR-236 Rule 8 (drafted-pair sequencing) requires ADR-238 to ship the smallest legitimate substrate-read primitive that **does not prejudice ADR-237's design** — i.e., the FE module exposes data, not opinions about how role rows render. This ADR is that minimal shape.

### Why "shape α" not "shape β"

Two scopings were considered during ADR-236 hardening:

- **Shape α (this ADR)**: extracted parser + types + hook + one consumer (chat composer inline posture display). ~1 session. Composes cleanly with ADR-237 because the role grammar consumes data, not patterns.
- **Shape β** (rejected): hook + `<AutonomyGuard>` wrapper + modal-confirmation pattern + grey-out pattern + multiple consumers. 2 sessions. Risks Rule 8 violation — wires patterns ADR-237 hasn't framed yet.

Shape α is the minimal substrate-read landing. Shape β components naturally land as part of ADR-237 / ADR-239 / ADR-240 when their respective sub-ADRs draft.

### Why the parser must move out of `MandateFace.tsx`

`MandateFace.tsx`'s inline `parseAutonomy` is structurally the same parser ADR-237's chat-role rendering will need, ADR-240's activation prompt will need, and ADR-236 Item 8/10's mop-up will need. Leaving it inline means each future sub-ADR re-derives it, and that pattern has bitten YARNNN before (ADR-231 surfaced 4 separate call-sites that each re-implemented "parse TASK.md frontmatter" in slightly incompatible ways before being consolidated).

Singular Implementation says: extract once now, ADR-237 imports it, ADR-240 imports it, no future re-derivation.

---

## Decision

### D1 — Extract autonomy parsing to `web/lib/autonomy.ts`

A new module `web/lib/autonomy.ts` becomes the **single FE source** of autonomy substrate parsing and shape vocabulary. It exports:

- `AutonomyLevel` — TypeScript union: `'manual' | 'assisted' | 'bounded_autonomous' | 'autonomous'`. Matches ADR-217 D1.
- `AutonomyMeta` — parsed substrate shape (default level/ceiling, per-domain overrides).
- `parseAutonomy(content: string): AutonomyMeta` — pure function. Same lightweight YAML walk that lives in `MandateFace.tsx` today, lifted verbatim.
- `formatAutonomySummary(meta: AutonomyMeta): string` — operator-facing one-liner. Same function lifted verbatim from `MandateFace.tsx`.
- `resolveEffectiveLevel(meta: AutonomyMeta, domain?: string): AutonomyLevel | null` — small new helper. Returns the effective level for a given domain, falling back to `default.level`. Used by ADR-237 / ADR-240 / Round 5 consumers; chat composer below uses it without a domain.

The module is 100% pure TS — no React imports. This guarantees it is consumable by future server components, MCP code, or any non-React surface that might want to format autonomy text.

### D2 — `useAutonomy()` hook in `web/lib/autonomy.ts`

A small React hook layered over the pure functions:

```ts
export function useAutonomy(): {
  meta: AutonomyMeta | null;
  loading: boolean;
  effectiveLevel: AutonomyLevel | null;
  summary: string;
};
```

- Reads `/api/workspace/file?path=/workspace/context/_shared/AUTONOMY.md` via `api.workspace.getFile`.
- Returns `meta=null, loading=true` during the read.
- Returns `meta=null, loading=false` if the file is absent (skeleton state per ADR-226).
- Computes `effectiveLevel = resolveEffectiveLevel(meta)` and `summary = formatAutonomySummary(meta)` at the hook level so consumers don't re-call the helpers.
- **No mutation surface.** Operator-authored substrate is mutated through `UpdateContext(target='autonomy')` per ADR-217 (or its ADR-235 successor). The hook is read-only.
- **No domain parameter on the hook.** Domain-specific lookup is a `resolveEffectiveLevel(meta, domain)` call by the consumer if needed — keeps the hook signature stable across consumers.

The hook has the same caching shape as `MandateFace`'s current `useEffect`-based read (one fetch per mount). ADR-238 deliberately does NOT introduce a global autonomy provider / context — that's an ADR-237 concern when chat-row rendering needs the value across many components in the same render pass.

### D3 — Refactor `MandateFace.tsx` to import from `@/lib/autonomy`

Per Singular Implementation:

- Delete inline `parseAutonomy`, `formatAutonomySummary`, and the `AutonomyMeta` interface from `MandateFace.tsx`.
- Import the same names from `@/lib/autonomy`.
- The face's render output is byte-for-byte identical (the helpers are lifted verbatim).

No backwards-compatibility shim. The inline copy goes; the imported one is the only one.

### D4 — First consumer: chat composer inline autonomy chip

Wire `useAutonomy()` into `web/components/tp/ChatPanel.tsx`. Above the input form, render a discreet autonomy posture chip when the level is non-default (i.e., not `manual`):

- `manual` (or skeleton state) → **chip hidden**. No visual noise for the dominant case.
- `assisted` → small muted-tone chip: `Assisted autonomy`.
- `bounded_autonomous` → small chip with ceiling: `Bounded autonomy · ceiling $20,000`.
- `autonomous` → small accent-tone chip: `Autonomous`.

The chip is **read-only**. Clicking it does nothing in this ADR (ADR-237 may later route it to a posture modal; ADR-238 does not pre-build that surface). Hover/focus shows the same `formatAutonomySummary` text.

The chip lives directly above the `<form onSubmit={handleSubmit}>` block at `ChatPanel.tsx:317`. Conditional render: present only when `effectiveLevel && effectiveLevel !== 'manual'`. Class name follows the existing chat-surface rounded-pill pattern; specific Tailwind class composition documented in the implementation file rather than this ADR.

**This is the first non-cockpit consumer of `useAutonomy`.** Subsequent consumers (Round 5 mop-up, ADR-237's role grammar, ADR-240's activation prompts) compose with the same hook.

### D5 — No new API endpoints, no new primitives, no schema changes

The hook reads through the existing `/api/workspace/file` endpoint. No new route. No new primitive in `services/primitives/`. No DB migration. The substrate file already exists at the canonical path per ADR-217 + ADR-226 + the workspace_init scaffold.

This is deliberate per ADR-236 Scope Guards 1, 4, 6 (no backend work, no DB migrations, no new MCP tools).

---

## What this ADR does NOT do

- **Does not gate the composer's submit button.** That's a Shape β concern — depends on what "submit while in OBSERVATION mode" should actually do (block? warn? proceed?). ADR-237 frames it.
- **Does not introduce confirmation modals.** Same reason; depends on the role grammar.
- **Does not parse the `never_auto` field** mentioned in ADR-217 D2's schema. The first consumer (chip display) doesn't need it. When a future consumer (ADR-237 ProposalCard rendering, or Round 5 modal-confirmation) needs `never_auto`, it extends `parseAutonomy` and the test gate. **Singular Implementation** — we don't ship parser fields with no reader.
- **Does not add a global React context.** A future ADR-237 sub-phase introduces `<AutonomyProvider>` if-and-only-if multi-component-in-one-render-pass autonomy reads surface as a real performance concern. Today the hook fetches once per face-or-composer mount; that's fine.
- **Does not touch server-side autonomy logic.** ADR-229's `should_auto_execute_verdict` gate is server-side and unchanged.
- **Does not extract the same pattern for MANDATE.md or BRAND.md.** They have one consumer each (`MandateFace`, `BrandSection`); the extraction is only justified once a second consumer surfaces. Today, only AUTONOMY has multiple downstream needs.

---

## Implementation

### Files created (3)

- `web/lib/autonomy.ts` (~120 LOC)
  - `AutonomyLevel` union type.
  - `AutonomyMeta` interface.
  - `parseAutonomy(content)` — lifted verbatim from `MandateFace.tsx`.
  - `formatAutonomySummary(meta)` — lifted verbatim from `MandateFace.tsx`.
  - `resolveEffectiveLevel(meta, domain?)` — new helper.
  - `useAutonomy()` — React hook, ~30 LOC.
  - One module-level constant: `AUTONOMY_PATH = '/workspace/context/_shared/AUTONOMY.md'` (also lifted verbatim — it's currently duplicated between `MandateFace.tsx` and `SubstrateEditor.tsx`'s editable-prefixes list; ADR-238 does NOT touch the editable-prefixes list, just centralizes the read-side constant).
- `api/test_adr238_autonomy_substrate.py` — Python regression gate (consistent with the rest of the repo's test conventions; FE has no test infrastructure today and ADR-238 deliberately does not introduce one — see "Test gate" below).
- `docs/adr/ADR-238-autonomy-mode-fe-consumption.md` (this file).

### Files modified (3)

- `web/components/library/faces/MandateFace.tsx`
  - Delete inline `parseAutonomy`, `formatAutonomySummary`, `AutonomyMeta`, `AUTONOMY_PATH` constant.
  - Import the same names from `@/lib/autonomy`.
  - The MANDATE_PATH constant + `parseMandate` + `MandateMeta` interface stay inline — they're MandateFace-specific and have no second consumer (per the principle in "What this ADR does NOT do").
  - The face's render output is unchanged.
- `web/components/tp/ChatPanel.tsx`
  - Import `useAutonomy` from `@/lib/autonomy`.
  - Render the autonomy chip in the input region above the form when `effectiveLevel && effectiveLevel !== 'manual'`.
  - Total addition: ~12 LOC including the hook call + conditional JSX.
- `api/prompts/CHANGELOG.md`
  - One entry: `[2026.04.29.N]` covering ADR-238's intent + the lift (no prompt-text change, but the entry records the surface change for future drift detection).

### Files NOT modified

- `api/services/workspace_init.py` — substrate scaffold unchanged.
- `api/services/primitives/*` — no new primitives.
- `web/components/workspace/SubstrateEditor.tsx` — its editable-prefixes list still references `AUTONOMY.md` literally; that's the *write* surface and is governed by a different concern. Centralizing the write-side constant is a future hygiene pass.
- ADR-217, ADR-228, any historical ADR — sub-ADR adds itself; doesn't edit predecessors per Rule 2.

### Test gate

`api/test_adr238_autonomy_substrate.py` asserts six invariants. No frontend test runner is introduced — Rule 3's "test gates required for Tier 1" is satisfied by a Python regression script that reads the FE source files (consistent with the ADR-231 invariants gate pattern).

1. `web/lib/autonomy.ts` exists and exports `parseAutonomy`, `formatAutonomySummary`, `resolveEffectiveLevel`, `useAutonomy`, `AutonomyLevel`, `AutonomyMeta`.
2. `web/components/library/faces/MandateFace.tsx` no longer contains the strings `function parseAutonomy(` or `function formatAutonomySummary(` (regression guard against re-inlining).
3. `web/components/library/faces/MandateFace.tsx` imports from `@/lib/autonomy`.
4. `web/components/tp/ChatPanel.tsx` imports `useAutonomy` from `@/lib/autonomy`.
5. `api/services/workspace_init.py` continues to scaffold `SHARED_AUTONOMY_PATH` (regression guard against substrate sunset that would orphan ADR-238).
6. `api/services/workspace_paths.py` exposes `SHARED_AUTONOMY_PATH = "context/_shared/AUTONOMY.md"` (path is workspace-relative on the Python side; the FE constant in `lib/autonomy.ts` is the absolute `/workspace/`-prefixed form). The regression guard catches Python-side drift on the relative path; FE drift is caught by assertion #1.

Combined gate target: 6/6 passing. No JS test runner. If a future ADR surfaces a real need for FE component testing, that ADR scaffolds vitest as a sub-phase — not this one.

### Render parity

| Service | Affected | Why |
|---|---|---|
| API (yarnnn-api) | No | No new endpoints, no backend code change. |
| Unified Scheduler | No | Reads autonomy via existing service-level helpers; no FE code runs there. |
| MCP Server | No | No tool surface change; ADR-169 three-tool surface preserved. |
| Output Gateway | No | Untouched. |

**No env var changes. No schema changes. No new services.**

### Singular Implementation discipline

- The two autonomy parser implementations (inline in MandateFace + new in `lib/autonomy.ts`) cannot coexist after this commit. The inline goes; the lib import is the only path.
- The chip is the only autonomy display surface in the chat composer — no parallel "info banner" or "header pill" implementations.
- `useAutonomy` is the only hook reading `AUTONOMY.md` for FE consumption; future consumers import it.

---

## Risks

**R1 — Bundle size impact.** `web/lib/autonomy.ts` is small (~120 LOC); no risk. Mentioned only because Rule 6's dimensional classification table accounts for surface mass.

**R2 — Hook fetch deduplication.** `MandateFace` and `ChatPanel` both render in some surfaces (e.g., `/work`'s cockpit + the chat panel embedded inside a future tab). Each calls `useAutonomy()` independently — two fetches of the same file. Mitigation: deferred. If profile shows it as a hot path, a follow-on ADR adds `<AutonomyProvider>` context; until then the duplication is one cached HTTP call (Next.js fetch cache) per surface mount.

**R3 — Path constant drift.** `AUTONOMY_PATH` exists in three places today: `MandateFace.tsx` (read), `SubstrateEditor.tsx` (editable-prefixes write list), and Python's `services/workspace_paths.py` (`SHARED_AUTONOMY_PATH`). ADR-238 centralizes the FE *read* constant in `lib/autonomy.ts` only. The other two stay separate because they're write/Python concerns. Mitigation: test gate assertion #6 catches Python-side drift; FE write-side drift is a different ADR.

**R4 — Autonomy substrate absent in older workspaces.** Workspaces created before ADR-217 may not have `AUTONOMY.md` scaffolded. The hook returns `meta=null` cleanly; the chip stays hidden; no error surface. Migration is implicit — `workspace_init.initialize_workspace` is idempotent and re-runs scaffold-missing-substrate paths on next signup hit; old workspaces self-heal on first activation.

**R5 — `MandateFace` render parity.** Lifting the parser must not change the byte-output. Mitigation: parser code is moved verbatim, no logic changes; visual parity verified by manual smoke during implementation; no automated visual regression.

---

## Phasing

Single commit, sized small (~250 line diff total including the ADR doc). The dependency graph is linear: lib module exists → MandateFace refactors → ChatPanel adds chip → test gate validates → CHANGELOG entry → commit.

1. Author `web/lib/autonomy.ts` (lifted code + new `resolveEffectiveLevel` + `useAutonomy`).
2. Refactor `MandateFace.tsx` to import; verify render parity by reading the resulting file.
3. Add chip render in `ChatPanel.tsx`.
4. Author `api/test_adr238_autonomy_substrate.py` regression gate.
5. Add `[2026.04.29.N]` CHANGELOG entry.
6. Atomic commit + push.

---

## Closing

ADR-238 is the smallest legitimate substrate-read landing under ADR-236 Rule 8. It extracts an existing parser into a shared module, adds one new helper (`resolveEffectiveLevel`), wires one new consumer (chat composer chip), and codifies the test gate via a Python regression script. The deliberate refusal to introduce confirmation modals, grey-outs, or a global provider is what makes Round 1 land cleanly without prejudicing Round 2 (ADR-237's role grammar) — the next sub-ADR consumes data this one already exposes, rather than re-defining vocabulary it would be wrong to predate.

The composition note at the top of this ADR records, in advance, how ADR-237 and ADR-240 will compose with `@/lib/autonomy`. Future-me reading those ADRs later will find a clear citation back to this one, satisfying Rule 8's `Builds on:` discipline.
