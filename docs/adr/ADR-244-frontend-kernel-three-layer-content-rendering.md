# ADR-244: Frontend Kernel Architecture — Three-Layer Content Rendering Model

> **Status**: **Phase 1 + Phase 2 Implemented** (2026-05-01). Phase 1 ratified the model + shipped registry stub (commit `c642173`, 8/8 gate). Phase 2 populated the registry by migrating four parsers + adding two new shape entries (this commit, 14/14 gate). Phases 3–5 deferred to follow-on commits per the phased plan in §Implementation.
> **Date**: 2026-05-01
> **Authors**: KVK, Claude
> **Dimensional classification**: **Channel** (Axiom 6) primary — codifies how operator-facing surfaces consume substrate. Secondary: **Substrate** (Axiom 1 — what the layers read), **Mechanism** (Axiom 5 — L2 lives at the deterministic end of the spectrum), **Purpose** (Axiom 3 — L3 is sited by operational meaning).
> **Builds on**: FOUNDATIONS v6.0 (six-dimensional axiomatic model), ADR-167 v9.1 (list/detail kind-aware dispatch — generalized here from `output_kind` to content-shape), ADR-168 (primitive matrix as backend kernel architecture — analogous discipline applied to FE), ADR-188 (kernel/program agnosticism), ADR-209 (Authored Substrate — the truth this model renders), ADR-215 (surface contracts + 4-shape CRUD matrix), ADR-222 (OS framing — kernel boundary discipline), ADR-225 (Compositor Layer — library scoping principle ratified here), ADR-228 (Cockpit four faces — instance of L3), ADR-235 (write-primitive routing — the substrate write contract this model honors), ADR-237 (chat dispatch — instance of L3), ADR-238 (autonomy parser + chip — instance of L2 + L3 split), ADR-239 (decisions parser — instance of L2), ADR-241 (single cockpit persona — instance of L3 consolidation), ADR-242 (cockpit bundle components — instance of L3 bundle binding).
> **Composes with**: ADR-198 (surface archetypes — Document/Dashboard/Queue/Briefing/Stream — orthogonal to L1/L2/L3; an archetype is a *use shape*, a layer is a *render layer*), ADR-216 (orchestration vs judgment — render layer is platform-fixed, doesn't speak persona), ADR-219 (narrative substrate — L1/L2 render conversation.md / recent.md identically to other markdown).
> **Amends**: ADR-167 v9.1 (KindMiddle dispatch is the produces_deliverable instance of L3-by-content-shape — the principle generalizes), ADR-225 (library scoping principle now explicit: L1 + L2 + L3 components are universal library citizens; bundles bind into L3 slots, never into per-path pages), ADR-237 (chat MessageDispatch is the canonical L3 instance for message shapes), ADR-238 (autonomy.ts is the first canonical L2 module — registry adds it without modification), ADR-239 (reviewer-decisions.ts is the second canonical L2 module — same registry entry pattern).
> **Preserves**: FOUNDATIONS axioms 1–9, ADR-209 substrate-as-truth, ADR-235 write-primitive routing, ADR-188 kernel agnosticism, ADR-222 kernel boundary, ADR-216 orchestration-vs-judgment vocabulary.

---

## Context

The codebase has been quietly evolving toward a content-shape-driven render model across multiple ADRs:

- ADR-167 introduced kind-aware middle dispatch (one shell, four middles by `output_kind`).
- ADR-225 introduced the universal library + compositor.
- ADR-228 froze cockpit at four faces fed by per-face bindings.
- ADR-237 introduced one dispatch table for chat message shapes.
- ADR-238 split autonomy into a pure-TS parser (`web/lib/autonomy.ts`) consumed by both `MandateFace` and the composer chip.
- ADR-239 lifted reviewer-decisions parsing into `web/lib/reviewer-decisions.ts`.
- ADR-241 collapsed Reviewer surface into a tab-based detail with content-shape-aware tabs.
- ADR-242 closed the bundle component layer for the cockpit faces.

What was missing: **a unifying axiomatic frame**. Without it, the model leaks back toward per-file or per-path bespoke pages every time a new substrate surface appears. The operator's question that triggered this ADR — *"am I rendering the filesystem too literally?"* — names the failure mode.

Two confusions were doing the damage:

**Confusion 1 — File-format vs content-semantics conflation.** `AUTONOMY.md` is a markdown file (format), but operationally it is *autonomy posture configuration* (semantics). Reaching for "open the markdown file" as the primary edit affordance is the wrong layer. The substrate is the file; the interface is the parsed shape.

**Confusion 2 — Substrate-as-truth (correct) leaking into render-as-mirror (incorrect).** ADR-209 establishes filesystem as truth for storage and attribution. The leak is treating that storage truth as the rendering API: one page per path, one component per file. Real operating systems don't do this — Finder shows raw bytes too as an escape hatch, but the User Profile screen renders parsed user state, not `users.json`.

This ADR ratifies the model that's already emerging across ADR-167 → ADR-242, names its three layers, maps each layer to a FOUNDATIONS axiom, and closes the three load-bearing gaps that block sustainability:

1. **Content-shape registry** — without an explicit one, L2 parsers proliferate as ad-hoc TS modules consumed inconsistently.
2. **Canonical-L3 + secondary-consumer convention** — without one, structured editors fork across multiple surfaces and drift.
3. **Per-class write contracts** — without these, structured editors will diverge in frontmatter preservation, schema validation, and round-trip integrity.

The ADR also establishes the supersede pass discipline for `docs/design/` so legacy per-page bespoke design docs are explicitly retired alongside the new model.

---

## Decisions

### D1 — Three Layers Are the Frontend Kernel Architecture

The frontend renders substrate content through exactly three layers:

| Layer | Role | Implementation locus | Axiom |
|---|---|---|---|
| **L1 — Universal Raw View** | Renders any `workspace_files` path as raw markdown / YAML / HTML / JSON. Trust signal + escape hatch. One component, one path-resolver. | `web/components/shared/WorkspaceFileView.tsx` | Substrate (Axiom 1) |
| **L2 — Content-Shape Parsers** | Pure-TS deterministic functions that read raw file content and return structured data. No state, no React, no IO. | `web/lib/content-shapes/` (NEW directory — see D3) | Mechanism, deterministic end (Axiom 5) |
| **L3 — Structured Affordances** | React components that consume L2 output and render content-aware operational UI. Sited by operational meaning, not file location. | `web/components/library/` (compositor library per ADR-225) | Channel (Axiom 6) + Purpose (Axiom 3) |

The dimensional mapping is the **axiomatic claim**: each layer occupies exactly one cell in the six-dimensional model, and the layers compose without overlap. A content shape that requires state belongs in L3, not L2. A render that requires interpretation belongs in L2 + L3, not L1.

### D2 — File-Format vs Content-Semantics Discipline

L1 dispatches on **file format** (`.md` / `.yaml` / `.json` / `.html`). L2 + L3 dispatch on **content shape** (autonomy / decisions / performance / recurrence-spec / etc.). A single file format hosts many content shapes; a single content shape may serialize as one format. This separation is non-negotiable.

The discipline rule: **before adding a new FE component or page, name the content shape and the operational moment.** "Autonomy posture, set from MandateFace and surfaced in the composer chip" is the right framing. "AUTONOMY.md viewer page" is the wrong framing.

### D3 — Content-Shape Registry

A registry lives at `web/lib/content-shapes/` as a versioned behavioral artifact (per CLAUDE.md rule 10).

**Schema** (per shape, one TS module + index):

```typescript
// web/lib/content-shapes/autonomy.ts
export const SHAPE_KEY = "autonomy";

export const PATH_GLOB = "**/AUTONOMY.md";

export type AutonomyData = { ... };

export function parse(raw: string): AutonomyData { ... }
export function serialize(data: AutonomyData): string { ... }

export const WRITE_CONTRACT: WriteContract = "configuration"; // see D5
export const CANONICAL_L3 = "MandateFace"; // see D4
```

```typescript
// web/lib/content-shapes/index.ts
export const CONTENT_SHAPES = {
  autonomy: AutonomyShape,
  decisions: DecisionsShape,
  performance: PerformanceShape,
  // ...
} as const;

export function shapeForPath(path: string): ContentShape | null { ... }
```

**Ownership**: `web/lib/content-shapes/` is owned by the FE platform. Adding a shape requires either (a) extending the kernel registry (universal shapes), or (b) shipping it in a program bundle's library extension (program-specific shapes per ADR-188). Bundle-shipped shapes follow the same schema; they are loaded but not modified by the kernel.

**Migration of existing modules**: `web/lib/autonomy.ts`, `web/lib/reviewer-decisions.ts`, `web/lib/recurrence-shapes.ts`, `web/lib/inference-meta.ts`, `web/lib/snapshot-meta.ts`, `web/lib/tp-chips.ts` migrate into `web/lib/content-shapes/{shape}.ts` with the schema above. See Phase 2 in §Implementation.

### D4 — Canonical L3 + Secondary Consumers

For each content shape there is exactly **one canonical L3** — the React component that owns the *primary* operational moment for that shape. Other surfaces that surface the same shape (chips, summaries, tooltips) are **secondary consumers**:

- Secondary consumers MUST call the same L2 parser as the canonical L3 (no re-implementing parse logic).
- Secondary consumers MUST NOT implement a separate structured editor. If a secondary surface needs to mutate, it either (a) defers to the canonical L3 by routing the user there, or (b) calls the same write primitive with the same serializer, never a divergent one.
- The canonical L3 is declared in the shape's registry entry (`CANONICAL_L3` field).

Examples (descriptive census of current state):

| Shape | Canonical L3 | Secondary consumers |
|---|---|---|
| autonomy | `MandateFace` | composer chip in `ChatPanel` |
| decisions | `DecisionsStream` (per ADR-241) | `PerformanceFace` calibration aggregate |
| performance | `MoneyTruthFace` | daily-update email summary |
| principles | `PrinciplesTab` (per ADR-241) | (none currently) |
| reviewer-verdict (msg) | `MessageDispatch` reviewer-verdict shape (per ADR-237) | (none) |
| recurrence-spec | TBD — currently no canonical L3, only L1 fallback | `WorkListSurface` recurrence chip (read-only) |
| inference-meta | `InferenceContentView` (per ADR-163) | (none) |

The "TBD" for recurrence-spec is a known gap — Phase 4 of this ADR addresses it.

### D5 — Per-Class Write Contracts

The model recognizes six content classes, each with a defined write contract that the shape's registry entry declares:

| Class | Examples | Write contract |
|---|---|---|
| **narrative** | `conversation.md`, `recent.md`, `_run_log.md`, `feedback.md`, `decisions.md`, audit logs | **append-only** by system; operator does not edit through L3 (raw L1 view only for inspection) |
| **authored_prose** | `IDENTITY.md`, `BRAND.md`, `_operator_profile.md` | **free-form**: full content replace via `WriteFile(scope='workspace')`; no schema validation; L3 is a markdown editor |
| **configuration** | `AUTONOMY.md`, `principles.md`, `_risk.md`, MANDATE.md heading marker | **structured**: L3 mutates parsed data only; shape's `serialize()` produces the file; routed through `WriteFile(scope='workspace')` per ADR-235 D1.b |
| **live_aggregate** | `_performance.md`, `_performance_summary.md`, `_tracker.md` | **read-only-from-operator**: only the system writer (back-office task / outcome reconciler) writes; L3 surfaces raw signals + parsed metrics; operator interacts via outcome → feedback path, never direct edit |
| **declaration** | `_spec.yaml`, `_recurring.yaml`, `_action.yaml`, `back-office.yaml` | **schema-validated structured**: L3 mutates parsed YAML only; shape's `serialize()` validates against ADR-231 schema; routed through `ManageRecurrence` primitive per ADR-235 D1.c, NOT direct `WriteFile` |
| **composed_artifact** | `output.html`, composed deliverables | **system-derived**: composed on demand by ADR-213 surface-pull pipeline; operator does not edit; L3 = composed view only |

The class is declared in the shape's registry entry (`WRITE_CONTRACT` field). The class determines which write primitive a structured editor calls — `WriteFile` for authored_prose / configuration; the appropriate lifecycle primitive (`ManageRecurrence`, `InferContext`) for declaration / inferred shapes per ADR-235.

### D6 — L3 Lives in the Library, Bound by SURFACES.yaml

Per ADR-225 the compositor library is the home for L3 components. Bundles never ship per-path pages. A bundle contributes to L3 by (a) shipping a library extension component, and (b) binding it via `SURFACES.yaml` into a face slot or detail middle.

Kernel-default L3 components handle universal content shapes (autonomy, principles, decisions, narrative, recurrence-spec). Bundle-supplied L3 components handle program-specific shapes (alpha-trader's portfolio chart per ADR-243). The kernel/program boundary discipline of ADR-222 + ADR-224 applies unchanged.

### D7 — Out of Scope (Explicitly Deferred)

The following are deliberately not closed by this ADR; each gets its own follow-on ADR if pressure surfaces:

- **Multi-site write coordination** (optimistic UI / contention / cache invalidation when canonical L3 + secondary consumer both attempt mutation). Current default: secondary consumers don't mutate. If this changes, a follow-on ADR addresses contention.
- **Parser shape versioning** (when a shape's frontmatter schema evolves — e.g., AUTONOMY.md gains a new field). Default: parsers tolerate missing fields and use defaults; breaking schema changes require a substrate migration. A follow-on ADR formalizes this if it becomes load-bearing.
- **Shape discovery from path alone** (today the registry has explicit `PATH_GLOB`; future could derive from frontmatter `kind:` field). Default: explicit glob.
- **Bundle library extension loading** (mechanism for programs to ship new L3 components). Sketched in ADR-225 but not formalized here.

---

## Implementation

Five phases. Each phase ships as one commit, each commit lands green (test gate passes, FE builds clean).

### Phase 1 — Ratify (this commit)

This ADR lands as **Proposed**. Adds Python regression test gate `api/test_adr244_three_layer_model.py` covering:

1. Registry directory `web/lib/content-shapes/` exists (Phase 2 will populate it; Phase 1 just creates the empty directory + index stub so the contract is on disk).
2. ADR file references all required predecessors (ADR-167, 225, 228, 237, 238, 239, 241, 242).
3. CLAUDE.md ADR registry section includes ADR-244 entry with `Implemented`/`Proposed` status flag.
4. `docs/design/` does not contain an ADR-244-superseded doc until Phase 5 lands the supersede pass.

### Phase 2 — Build Content-Shape Registry, Migrate Existing Parsers

**Status: Implemented 2026-05-01.**

Creates `web/lib/content-shapes/` directory with the schema from D3. Migrates four actual parsers, adds two new shape entries, populates the registry.

**Migrations shipped:**

- `web/lib/autonomy.ts` → `web/lib/content-shapes/autonomy.ts` (✓)
- `web/lib/reviewer-decisions.ts` → `web/lib/content-shapes/decisions.ts` (✓)
- `web/lib/inference-meta.ts` → `web/lib/content-shapes/inference-meta.ts` (✓)
- `web/lib/snapshot-meta.ts` → `web/lib/content-shapes/snapshot.ts` (✓)

**New shape entries:**

- `performance.ts` — parser extracted from `MoneyTruthFace.tsx` inline `parseFrontmatter`. Phase 3 audit will refactor MoneyTruthFace to import from this module.
- `principles.ts` — Phase 2 ships a stub (returns raw markdown wrapped). The structured threshold parser arrives in Phase 4 alongside the threshold-editor L3 affordance.

**Registry populated.** `web/lib/content-shapes/index.ts` imports every shape's `META`, freezes the `CONTENT_SHAPES` map, and exposes `shapeForPath(path)` that walks the registered globs (skipping ephemeral-substrate sentinels like snapshot's `__chat_message__/snapshot`). All callers (11 files across `library/`, `chat-surface/`, `tp/`, `context/`, `work/details/`) migrated to `@/lib/content-shapes/{shape}` imports. Old paths deleted (Singular Implementation rule 1). Test gate `test_phase_2_no_stale_imports` enforces zero residual references.

**Phase 2 implementation-time finding (recurrence-shapes drift).** The Phase 1 spec listed `web/lib/recurrence-shapes.ts → web/lib/content-shapes/recurrence-spec.ts` as a Phase 2 migration. Phase 2 inspection found `recurrence-shapes.ts` is not a content-shape parser — it has no `parse()` of file content, no `PATH_GLOB`. It's a domain-key utility (workspace-path resolution + surface-type coercion of API-returned strings). Migrating it would have forced an artificial schema fit and obscured what the file actually is.

The recurrence-spec content shape (DECLARATION class per D5) exists conceptually — `_spec.yaml` / `_recurring.yaml` / `_action.yaml` per ADR-231. But its FE parser lives nowhere yet: server-side `api/services/recurrence.py` parses YAML; FE reads come through API endpoints, not direct YAML parsing. When Phase 4 lands the recurrence-spec L3 editor, the parser is created at that point — same demand-pull discipline as ADR-225 v2's "ship 6 components, not 14" Phase 2 refinement and ADR-239's "scope smaller than memo predicted" finding. `recurrence-shapes.ts` stays at its current path.

**Test gate**: 14/14 (Phase 1's 8 + Phase 2's 6 — module existence, schema declaration, legacy deletion, no-stale-imports, registry populated, finding logged).

### Phase 3 — Audit Existing FE for Canonical-L3 Violations

Audits every component that parses substrate content. For each finding:

1. If a component re-implements parse logic that the registry already covers → refactor to import from registry.
2. If two components implement structured-edit affordances for the same shape → designate canonical, downgrade secondary to read-only or route-through.
3. If a per-path page exists for what should be a shape-driven L3 → flag for restructure.

Specific known candidates from current code:

- `PerformanceFace.tsx` had inline `parseDecisions` (fixed in ADR-239) — verify clean.
- `MandateFace.tsx` inline `parseAutonomy` — fixed in ADR-238 — verify migration to new registry path lands.
- `MoneyTruthFace.tsx` inline `_performance.md` frontmatter parsing — migrate to `content-shapes/performance.ts`.
- `WorkListSurface.tsx` recurrence chip — verify it imports from `content-shapes/recurrence-spec.ts`.

Audit produces one commit per migration; no audit-only commits.

### Phase 4 — Per-Class Write Contracts in Shape Modules

Each shape's registry entry gains:

- `WRITE_CONTRACT` field (one of the six classes from D5).
- For `configuration` and `declaration` classes: a `serialize()` function that round-trips data → file content with frontmatter preservation.
- For `narrative` and `live_aggregate` classes: explicit `WRITE_CONTRACT = "system_owned"` so editors that try to mutate trip a TypeScript error.

Adds a typed `writeShape<S>(shape, data, opts)` helper in `web/lib/content-shapes/write.ts` that:

1. Looks up the shape's `WRITE_CONTRACT`.
2. Routes to the correct primitive (`WriteFile` for authored_prose / configuration; `ManageRecurrence` for declaration; throws for system_owned).
3. Invokes the shape's `serialize()` for structured classes.
4. Honors ADR-209 attribution requirements (passes `authored_by="operator"` on operator-initiated writes).

This phase closes the missing L3 affordances flagged in the audit:

- Autonomy toggle in `MandateFace` (ADR-238 shipped read-only chip; this phase ships the toggle).
- Principles auto-approval threshold editor in `PrinciplesTab`.
- Risk envelope editor in MandateFace (or its own face slot — TBD during phase).

### Phase 5 — `docs/design/` Supersede Pass

For each doc in `docs/design/`, classify against the new model:

| Status | Treatment |
|---|---|
| Still load-bearing | Keep in place; add ADR-244 cross-reference where relevant. |
| Superseded by ADR-244 | Add `> **Superseded by ADR-244** (date)` banner at top, move file to `docs/design/archive/`. |
| Partially superseded | Keep the still-load-bearing parts, banner the rest, link forward. |

Initial classification (subject to per-doc audit during phase):

| Doc | Classification |
|---|---|
| `SURFACE-CONTRACTS.md` | **Keep** — ADR-215 4-shape CRUD matrix is orthogonal to the layer model. Add cross-ref. |
| `COCKPIT-COMPONENT-DESIGN.md` | **Keep** — ADR-228 + ADR-242 + ADR-243 living document. Add cross-ref to L3 layer. |
| `AGENT-AND-TASK-SURFACE-PATTERNS.md` | **Audit** — likely partially superseded; per-surface bespoke patterns dissolve into shape-driven L3. |
| `TASK-OUTPUT-SURFACE-CONTRACT.md` | **Audit** — likely superseded by ADR-213 + this ADR. |
| `TASK-SETUP-FLOW.md` | **Audit** — likely partially superseded. |
| `FEEDBACK-WORKFLOW-REDESIGN.md` | **Audit** — likely superseded by ADR-181 + this ADR. |
| `SHARED-CONTEXT-WORKFLOW.md` | **Audit** — likely superseded by ADR-235. |
| `COMPOSER-INPUT-PATTERN.md` | **Keep** — UX flow doc, orthogonal. |
| `INLINE-PLUS-MENU.md` | **Keep** — UX flow doc, orthogonal. |
| `ONBOARDING-TP-AWARENESS.md` | **Keep** — orthogonal. |
| `TP-NOTIFICATION-CHANNEL.md` | **Keep** — orthogonal. |
| `USER-JOURNEY.md` | **Keep** — orthogonal. |
| `HEADLESS-PROMPT-PROFILES.md`, `PROMPT-PROFILE-EVALUATION.md` | **Keep** — backend prompt design, orthogonal. |
| `SKILLS-REFRAME.md` | **Keep** — output gateway design, orthogonal. |
| `CHANGELOG.md` | **Keep** — log. |

Phase 5 produces one commit; doc-only changes; CI green.

---

## Test Gate

`api/test_adr244_three_layer_model.py` — Python regression script. Per ADR-236 Rule 3, no JS test runner is introduced.

Phase 1 assertions (this commit):

1. `web/lib/content-shapes/` directory exists.
2. `web/lib/content-shapes/index.ts` exists (stub with placeholder `CONTENT_SHAPES = {}` + `shapeForPath` returning null is acceptable for Phase 1).
3. ADR file at `docs/adr/ADR-244-frontend-kernel-three-layer-content-rendering.md` exists.
4. ADR file references all required predecessor ADRs (167, 225, 228, 237, 238, 239, 241, 242).
5. CLAUDE.md contains an ADR-244 entry under the Key ADRs section.
6. `docs/design/` archive does not yet contain ADR-244 supersede artifacts (Phase 5 hasn't run).

Phases 2–5 add their own assertions; the gate accumulates.

---

## Open Questions (Logged for Future Decisions)

1. **Bundle library extension mechanism** — How do programs ship L3 components without forking the kernel library? ADR-225 sketches this; this ADR depends on it being workable but doesn't formalize. Resolution path: when a program needs to ship a new L3 component, file the formalization ADR.
2. **Path-glob vs frontmatter-based shape resolution** — Currently shapes declare `PATH_GLOB`. If a single path hosts multiple shapes (TBD), frontmatter `kind:` field would resolve. Defer.
3. **L1 polymorphism by file format** — `WorkspaceFileView` currently renders markdown. YAML / JSON / HTML rendering needs syntax highlighting. Trivial Phase 2 follow-up; not architectural.

---

## Implementation Notes

(To be filled in by each Phase commit's "Implementation Notes" section.)

### Phase 1 (commit `c642173`)

- ADR file authored.
- `web/lib/content-shapes/` directory created with stub `index.ts`.
- `api/test_adr244_three_layer_model.py` regression gate authored — 8/8 Phase 1 assertions pass.
- CLAUDE.md ADR registry entry added.
- Backward amend banners on predecessors (ADR-167, 225, 237, 238, 239) deferred to the phases that actually mutate predecessor code — no banner-only sweep-up in a Phase 1 ratification commit. Forward citation in this ADR's `> **Amends**` header is the canonical record.
- Phases 2–5 deferred to follow-on commits per the discipline of ADR-236 Rule 8 (drafted-pair sequencing — each phase cites its predecessor only after the predecessor reaches `Implemented`).

### Phase 2 (this commit)

- 4 parsers migrated from `web/lib/{autonomy,reviewer-decisions,inference-meta,snapshot-meta}.ts` into `web/lib/content-shapes/{autonomy,decisions,inference-meta,snapshot}.ts`. Each module gains the D3 schema fields (SHAPE_KEY, PATH_GLOB, WRITE_CONTRACT, CANONICAL_L3, META export) alongside the lifted parser body.
- 2 new shape entries: `performance.ts` (parser extracted from MoneyTruthFace inline `parseFrontmatter`), `principles.ts` (Phase 2 stub — Phase 4 lands the structured parser).
- Registry populated: `index.ts` imports each `META`, freezes `CONTENT_SHAPES`, and `shapeForPath()` matches PATH_GLOB with a lightweight glob → regex compiler that handles `**`, `*`, and `{a,b}` alternation. Ephemeral-substrate shapes (snapshot's `__chat_message__/snapshot` sentinel) are skipped at lookup time.
- 11 caller files migrated to `@/lib/content-shapes/{shape}` imports across `library/`, `chat-surface/`, `tp/`, `context/`, `work/details/`. Sed-based migration verified by `test_phase_2_no_stale_imports`.
- Old parser files DELETED at `web/lib/{autonomy,reviewer-decisions,inference-meta,snapshot-meta}.ts` per Singular Implementation rule 1.
- Test gate extended: 6 Phase 2 assertions added; 14/14 total passing.
- Implementation-time finding logged: `recurrence-shapes.ts` is a domain-key utility, not a content-shape parser. It stays at its current path. The recurrence-spec content shape (DECLARATION class) gets a parser when Phase 4's L3 editor lands.
