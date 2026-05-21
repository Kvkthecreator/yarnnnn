# ADR-297 — Surfaces as Substrate Mirror: Atomic Surfaces, Summon Index, Compositor as Registry

> **Status:** Proposed (2026-05-21)
> **Authors:** KVK, Claude
> **Supersedes:** [ADR-244](ADR-244-workspace-settings-surface.md) (workspace settings surface as container — replaced by atomic kernel surfaces) · [ADR-266](ADR-266-workspace-surface-content-discipline.md) (workspace page-as-container reshape — replaced by atomic + index) · [ADR-243](ADR-243-schedule-surface.md) (Schedule surface as a tab — folds into atomic Cadence surface) · the 4-tab nav portion of [ADR-214](ADR-214-agents-page-consolidation.md) (Feed/Work/Agents/Files framing — dissolves into pinned-surface dock + summon index)
> **Amends:** [ADR-205](ADR-205-workspace-primitive-collapse.md) F1 (chat-first landing — replaced by last-used home) · [ADR-225](ADR-225-compositor-layer.md) (compositor extended from middle-component-resolver to full surface-registry) · [ADR-198](ADR-198-surface-archetypes.md) (every surface declares its archetype) · [ADR-251](ADR-251-system-agent-reviewer-first-class-surfaces.md) (Reviewer-page tab structure — governance content moves to atomic surfaces, Reviewer page shrinks to Reviewer-substance only)
> **Preserves:** [FOUNDATIONS](../architecture/FOUNDATIONS.md) Axioms 1–9 · [ADR-209](ADR-209-authored-substrate.md) (attribution model) · [ADR-222](ADR-222-agent-native-operating-system-framing.md) (kernel/userspace boundary — this ADR enacts the boundary at the surface layer) · [ADR-216](ADR-216-orchestration-surface-vs-judgment-persona.md) (orchestration vs judgment taxonomy) · [ADR-223](ADR-223-program-bundle-specification.md) (bundle structure) · [ADR-213](ADR-213-surface-pull-composition.md) (compose-on-demand)
> **Companion discourse:** [`docs/design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md`](../design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md) (parked design discussion that produced this ADR's convergence) · [`docs/architecture/cadence-and-wakes.md`](../architecture/cadence-and-wakes.md) §15 item 4 (operator-visible cadence surface — closed by this ADR's atomic Cadence surface)

---

## Context

Three sessions of frontend work (ADR-244 → ADR-251 → ADR-266) iterated on a **page-as-container** model: `/workspace` rendering four governance concepts as inline cards, Reviewer-page tabs mirroring some of the same content, `/schedule` as a separate-but-related cadence surface, four top-level tabs (Feed · Work · Agents · Files) as the nav spine. Each iteration tightened the model but left recurring symptoms:

1. **Container churn.** Every new authored concept triggered re-litigation of *"which container does this go in?"* — Workspace page, Reviewer tab, Settings, or new top-level surface. The cadence/wake surfacing question (the prompt for this ADR's discourse session) was the fourth instance.
2. **Surface duplication.** ADR-266 explicitly said `/workspace` *"replaces the Mandate/Autonomy/Principles tabs on the YARNNN agent detail."* The Reviewer page still renders the same `DelegationCard` and `PrinciplesCard` components inside its Autonomy and Principles tabs. Two surfaces, one substrate — Singular Implementation violated for ~7 months.
3. **Substrate atomicity vs surface coupling.** Each authored concept already has its own substrate file (`MANDATE.md`, `_autonomy.yaml`, `principles.md`, `IDENTITY.md`, `BRAND.md`, `_recurrences.yaml`, `_hooks.yaml`, `standing_intent.md`). The kernel treats them as atomic per FOUNDATIONS Axiom 1. The container model is the **only** layer that violates that atomicity.
4. **Compositor underused.** [ADR-225](ADR-225-compositor-layer.md) shipped a working compositor layer that already supports per-bundle SURFACES.yaml composition. The compositor's output is currently scoped to middle-component resolution inside fixed surfaces. The full-surface composition capability already exists in the code; it's not yet exposed at the shell level.
5. **OS framing canonized but not enacted at the surface layer.** [ADR-222](ADR-222-agent-native-operating-system-framing.md) canonized YARNNN as an Agent-Native OS where kernel/program/userspace boundaries are literal. The substrate layer honors this rigorously (kernel substrate files, per-bundle `_recurrences.yaml`, operator-writable workspace content). The surface layer doesn't yet — kernel surfaces, program surfaces, and operator concepts are bundled together on container pages.

This ADR closes all five gaps with one structural principle: **surface shape and surface authorship both mirror substrate**. The implementation is continuous with existing infrastructure (extends ADR-225's compositor) rather than a green-field rebuild.

---

## Foundational principle

> **Surface shape and surface authorship both mirror substrate.**

The corollaries:

1. **Atomicity** — Substrate is atomic (one concept per file). Surfaces are atomic (one concept per surface). 1:1 mapping between substrate file class and surface.
2. **Authorship tiers** — Substrate has three authorship tiers (kernel / program-bundle / workspace-operator). Surfaces have the same three tiers. Each surface inherits the tier of its substrate.
3. **Attribution** — Substrate writes carry `authored_by` per ADR-209. Surfaces display provenance where it aids operator understanding.
4. **Composability** — Substrate is composable (operator/Reviewer authors new files via primitives). Surfaces can become composable (Thesis 2, forward horizon — see §Forward horizon).

This principle subsumes and clarifies the prior surface-model attempts. There is no need to choose a container's "right" home for a concept — each concept lives where its substrate lives, at its own surface.

---

## Decisions

### D1 — Atomic surfaces, one per substrate concept

Every operator-authored governance concept becomes its own self-contained surface. The page-as-container model dissolves.

**Kernel surfaces** (universal — every YARNNN workspace has these):

| Surface | Substrate | Archetype (ADR-198) |
|---|---|---|
| Feed | session_messages (chat narrative) | Stream |
| Cadence | `/workspace/_recurrences.yaml` + `/workspace/_hooks.yaml` + `/workspace/review/standing_intent.md` + execution_events telemetry | Dashboard |
| Delegation | `/workspace/context/_shared/_autonomy.yaml` | Document |
| Mandate | `/workspace/context/_shared/MANDATE.md` | Document |
| Principles | `/workspace/review/principles.md` + `/workspace/review/_principles.yaml` | Document |
| Identity | `/workspace/context/_shared/IDENTITY.md` | Document |
| Brand | `/workspace/context/_shared/BRAND.md` | Document |
| Files | `workspace_files` (all paths) | Browser (raw substrate viewer; ADR-198 catalog extends with Browser as needed) |
| Agents | `agents` table + per-agent substrate | Roster (extends ADR-198 catalog) |
| Program | `/workspace/_program.yaml` + bundle MANIFEST | Document |
| Queue | `action_proposals` (pending) | Queue |
| Activity | `execution_events` | Stream |

Container surfaces dissolve. Specifically:
- `/workspace` (current four-card render) → dissolved; the URL becomes a redirect to the index for backward compatibility (or removed if no inbound links remain after migration).
- `/agents?agent=reviewer` Autonomy + Principles tabs → dissolved; deep-links redirect to atomic Delegation / Principles surfaces. Reviewer page shrinks to Reviewer-substance-only (Identity, Capabilities, Activity).
- `/schedule` (ADR-243) → folds into atomic Cadence surface.
- Settings page (Billing · Usage · Account) retains only billing/usage/danger-zone content; workspace governance migrates out.

### D2 — Three authorship tiers, mirroring substrate

| Tier | Substrate scope | Surface authoring | Indexed when |
|---|---|---|---|
| **Kernel** | Universal substrate (`_autonomy.yaml`, `MANDATE.md`, etc. — present in every workspace) | Platform code in `web/components/library/` (canonical files) | Always (every workspace) |
| **Program** | Bundle-shipped substrate (per-program `SURFACES.yaml`, domain folders, program-specific task slugs) | Bundle files at `docs/programs/{slug}/SURFACES.yaml` + components at `web/components/library/programs/{slug}/` | When bundle is active for the workspace |
| **Composed** | Operator/Reviewer-authored arbitrary substrate (future custom views, ad-hoc compositions) | `WriteFile` to workspace per ADR-209 (forward horizon — see §Forward horizon) | When composed surface declaration exists in workspace |

The substrate location *is* the boundary. Adding a new surface follows a deterministic test:

- Does it render substrate that every YARNNN workspace has? → Kernel surface.
- Does it render substrate that only a specific program's workspaces have? → Program surface (lives in the bundle).
- Does it render substrate that's operator-arbitrary? → Composed surface (forward horizon).

No new boundary vocabulary required; the principle is **substrate-location-determines-surface-tier**.

### D3 — Compositor as full surface registry

[ADR-225](ADR-225-compositor-layer.md)'s compositor extends from middle-component-resolver to the **full surface registry for the shell**. Specifically:

- Kernel surfaces become "default bundle" entries the compositor always emits (a `kernel` pseudo-bundle in the composition output).
- Program surfaces continue to flow from per-bundle SURFACES.yaml when the bundle is active (existing ADR-225 behavior, scope-expanded).
- The compositor's output schema gains a top-level `surfaces[]` array — flat list of all available surfaces for the workspace, each entry declaring slug, title, archetype, tier (`kernel | program:{slug} | composed`), substrate paths, icon, default-pinned-flag.
- Composed surfaces (forward horizon) register through the same schema; the compositor reads workspace-authored composition manifests in addition to bundle-shipped ones.

The shell components (dock + summon index + atomic surface routes) consume this compositor output as their single source of truth. There is no parallel surface registry in the frontend code.

**Singular Implementation discipline**: the existing `KindMiddle` switch in `WorkDetail.tsx` (the legacy compositor consumer per ADR-225 Phase 2) deletes. All surface resolution flows through the extended compositor.

### D4 — Summon-first index, not destination-based hub

The index of all available surfaces is an **overlay**, not a route.

- **Trigger**: visible icon affordance in the persistent shell chrome (top-right; canonical placement for global launchers); also voice-summonable in future (operator's note — voice deferred but the overlay is designed to be summon-source-agnostic).
- **Behavior**: opens over the current context without context-switching the underlying surface. Operator types or scrolls to find a surface, Enter or click navigates to it; Escape dismisses without effect.
- **Subtle tier grouping**: surfaces group visually by tier with small section headers (e.g. *"Workspace"* / *"Trader"* / *"Custom"*). Provenance is legible — operator sees "this surface exists because I'm running alpha-trader" — without the tier metadata feeling load-bearing.
- **Content**: every surface from the compositor's registry, scoped to the active workspace's bundles. Composed surfaces appear when present.

**No keyboard-only constraint** — the icon is the primary affordance; keyboard hotkey is a power-user enhancement, not the required entry point. (Operator preference noted: summon-first, not keyboard-first. Voice is the forward direction beyond keyboard.)

### D5 — Pinned-surface dock with Feed-only default

The shell carries a **dock** — a persistent row of always-visible surface icons.

- **Position**: bottom of viewport (desktop; canonical Dock-pattern), bottom-nav (mobile).
- **Defaults**: Feed only. Every other surface is summon-only until the operator pins it.
- **Pinning**: operator pins any surface from the index via a contextual action (long-press, right-click, or pin-button on the surface header). Pinned surfaces persist per-workspace in a `pinned_surfaces` array (likely `user_memory` or new `user_preferences` table; finalized at implementation).
- **Pin order**: drag-reorderable within the dock.
- **Discoverability**: the launcher icon (D4) is always visible adjacent to the dock; operators discover non-pinned surfaces through it.

**Rationale for Feed-only default**: operator's explicit choice. New operators see a minimal shell, discover surfaces organically through the launcher as they need them. The dock grows with operator expertise; it doesn't presuppose what matters.

### D6 — Last-used home (macOS-natural)

On workspace open, the operator lands on the **most-recently-active surface**.

- First-time operators (no surface history) land on Feed (the only default-pinned surface).
- Subsequent visits restore the surface and, where applicable, the within-surface state (selected file, scroll position — implementation-detail-level).
- The chat-first landing of [ADR-205 F1](ADR-205-workspace-primitive-collapse.md) is superseded: Feed remains the *first-time* default but not the perpetual one.

Persisted per-workspace in the same store as pinned-surface preferences.

### D7 — Shell chrome simplifies

The 4-tab nav (Feed · Work · Agents · Files) dissolves. The new shell:

- **Top chrome**: brand mark (left), launcher icon + user menu (right). No nav tabs.
- **Bottom chrome**: dock with pinned surfaces (desktop); bottom-nav-equivalent on mobile.
- **PageHeader** (per existing ADR-167 v2 amendment): retained per-surface for title + provenance + per-surface actions. Its navigation role (breadcrumb-as-mode-switch) dissolves; provenance role remains.

`web/components/shell/ToggleBar.tsx` deletes. `web/lib/routes.ts` shrinks dramatically — most top-level route constants become surface-slug references resolved through the compositor.

### D8 — Migration discipline (Singular Implementation)

This ADR enacts in **one ratification + one implementation PR** per migration phase. No dual-render, no transitional shell-chrome-coexists-with-launcher, no progressive disclosure. Either the new model is live or the old one is.

Migration phases:

- **Phase 1 — Compositor extension**: extend ADR-225 compositor schema to emit full `surfaces[]` registry including kernel surfaces. Backend-only; no frontend visible change. Surfaces are still rendered through existing routes/components.
- **Phase 2 — Shell rebuild**: top-chrome + dock + launcher land. Existing routes preserved during this PR but linked from the launcher, not the deleted nav tabs. Atomic surfaces that don't yet exist as separate routes get created (Cadence, etc.). Container surfaces (`/workspace` four-card render) atomized into their constituent atomic surfaces.
- **Phase 3 — Container deletion**: `/workspace` container, Reviewer Autonomy/Principles tabs, `/schedule` standalone surface deleted (URLs redirect to atomic equivalents). `WorkspaceConfigSection.tsx`, `ReviewerDetail.tsx`'s Autonomy/Principles branches, etc. deleted. Singular Implementation enforced — no parallel code paths.

Phase 1 is independent (ships without UX change). Phases 2 + 3 must land together for Singular Implementation discipline; deferred-deletion violates this ADR's spirit.

### D9 — Mobile follows conventional patterns

Desktop and mobile diverge on shell mechanics, converge on substrate:

| Layer | Desktop | Mobile |
|---|---|---|
| Dock | Bottom row, click-to-navigate | Bottom-nav, tap-to-navigate |
| Launcher | Overlay (modal-shaped, opens over context) | Destination route (full-screen — overlays on small viewports are anti-pattern per iOS/Android conventions) |
| Atomic surfaces | Same content, side-by-side affordances where viewport permits | Same content, full-width, stacked sections |
| Pinned defaults | Same (Feed-only) | Same (Feed-only) |

Acceptable compromises noted: mobile loses summon-on-top-of-context; gains bottom-nav muscle memory. Operator accepts this convention boundary explicitly.

### D10 — Forward horizon: composed surfaces (Thesis 2, not designed)

The substrate-mirror principle naturally extends to **composed surfaces** — operator or Reviewer-authored views that combine substrate reads, kernel components, and program components into custom dashboards. The architectural slots are reserved in this ADR (D2 tier 3, D3 compositor schema accommodates composed entries, D4 index displays composed group) but the **authoring path is not designed here**.

A future ADR — provisional title *"Composed Surfaces — Operator-Authored Views"* — will specify:
- Authoring primitive (operator chat-driven? Reviewer mid-loop? Both?)
- Persistence shape (workspace file at `/workspace/views/{slug}.yaml`? new substrate?)
- Component vocabulary (which kernel/program components are composable?)
- Discovery + sharing patterns

This ADR commits to **not blocking** that direction. Specifically: the surface registry schema (D3) accommodates a `tier: composed` entry; the launcher (D4) supports a "Custom" section; the dock (D5) accepts composed surfaces in the pinned set with no special-casing. We don't build the authoring path; we don't preclude it.

---

## What this ADR does NOT do

- **Does not specify the surface registry schema in detail.** Schema design lands in the Phase 1 implementation PR (compositor extension), informed by ADR-225's existing schema. ADR fixes principles, not field names.
- **Does not build composed-surface authoring.** Forward horizon only (D10).
- **Does not rename existing primitives.** All authoring primitives (`Schedule`, `ManageHook`, `WriteFile`, etc.) unchanged.
- **Does not change substrate.** Every substrate path and schema preserved. This is purely a frontend reshape.
- **Does not amend FOUNDATIONS or GLOSSARY.** No new axioms; this is the surface-layer enactment of existing axioms (1 — Substrate; 6 — Channel) and OS framing (ADR-222).
- **Does not specify cadence-surface design.** The atomic Cadence surface exists per D1's enumeration but its archetype/content/interactions are spec'd in implementation. The `cadence-and-wakes.md` canon doc already provides the substrate map; the surface design follows from it.

---

## Implementation outline (for the follow-on PR)

Sketch only — full PR plan accompanies Phase 1 commit:

1. **Compositor schema extension** (`api/services/composition_resolver.py`): emit top-level `surfaces[]` array with full kernel + program registry. Kernel surfaces declared in `api/services/kernel_surfaces.py` (new) or equivalent canonical location.
2. **Surface registry types** (`web/lib/compositor/types.ts`): extend with `Surface` type — slug, title, archetype, tier, substrate_paths, icon_key, default_pinned, route.
3. **Shell rebuild** (`web/components/shell/`): replace `ToggleBar` + breadcrumb-as-nav with `Dock` + `LauncherButton` + `LauncherOverlay`. PageHeader simplifies to title + provenance + per-surface actions.
4. **Atomic surface routes**: ensure every kernel surface has a route. Cadence is the largest net-new surface (consumes content from `cadence-and-wakes.md` §10 lifecycle + §11 authoring surfaces + §9 telemetry).
5. **Surface state persistence**: `pinned_surfaces` + `last_active_surface` in user preferences (`user_memory` table or new `user_preferences` per implementation review).
6. **Container deletion** (Phase 3): `WorkspaceConfigSection.tsx`, Reviewer Autonomy/Principles tab branches, `/schedule` page, related route constants — all deleted in the same PR per Singular Implementation.
7. **Cross-link updates**: every link in the codebase pointing to `/workspace`, `/agents?agent=reviewer&tab=autonomy`, `/agents?agent=reviewer&tab=principles`, `/schedule` updates to atomic-surface equivalents. Grep-and-rename pass.
8. **Mobile**: separate composition for mobile shell (bottom-nav + launcher-as-destination). Possibly a separate PR after desktop lands.
9. **CHANGELOG**: `api/prompts/CHANGELOG.md` entry if any TP prompt references container surfaces (likely none, but verify).
10. **ADR status flip**: this ADR moves from Proposed → Implemented on the PR that lands Phases 2 + 3.

---

## Companion docs to update

When this ADR ratifies:

- [`docs/design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md`](../design/SURFACE-MODEL-ATOMIC-VS-CONTAINER.md) — status note added: *"Discussion converged 2026-05-21. Ratified by ADR-297."* Doc preserved as historical artifact of how the decision was reached.
- [`docs/architecture/cadence-and-wakes.md`](../architecture/cadence-and-wakes.md) — §15 item 4 (operator-visible cadence surface) crossed off with reference to ADR-297's atomic Cadence surface.
- [`docs/architecture/FOUNDATIONS.md`](../architecture/FOUNDATIONS.md) — no axiom changes. Optional: one-sentence note in Axiom 6 (Channel) section that "atomic surfaces mirror substrate concepts per ADR-297."
- [`docs/architecture/SERVICE-MODEL.md`](../architecture/SERVICE-MODEL.md) — compositor row updated to note expanded scope (full surface registry vs middle-component-resolver only).
- [`docs/design/WORKSPACE.md`](../design/WORKSPACE.md) — surface-contracts section rewritten to reflect the dock + launcher shell.
- [`CLAUDE.md`](../../CLAUDE.md) — ADR-297 summary added in the alphabetical-ADR section.

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Discoverability gap for new operators** (no nav tabs, launcher needs learning) | Launcher icon always visible in shell chrome; Feed-only default ensures operators see *something* immediately; first-time onboarding can prompt "try the launcher" once |
| **Mobile divergence introduces dual-implementation risk** | Mobile follows conventional bottom-nav + destination-launcher pattern; same compositor output; only the shell render diverges |
| **Container deletion breaks bookmarks/inbound links** | URL redirects from old container routes to atomic equivalents; grep pass for code-level link updates |
| **ADR-225 compositor extension is non-trivial** | Phase 1 lands compositor change *before* shell rebuild; backend-only, no UX change, derisks the shell PR |
| **Operator confusion during migration** | Singular Implementation discipline — when the PR lands, the new model is live entirely. No half-states. Old shell deleted, new shell mounted, in one PR. |
| **Composed-surface authoring pressure surfaces before ADR ready** | D10 commits to non-blocking; if pressure surfaces early, the schema accommodates a stub Custom group with a "coming soon" placeholder |

---

## Acceptance criteria for "Implemented"

- Phase 1 (compositor extension) merged.
- Phase 2 + 3 (shell rebuild + container deletion) merged in single PR.
- No surface uses the page-as-container pattern. Every authored substrate concept has its own atomic surface.
- 4-tab nav (`ToggleBar.tsx`) deleted from `web/components/shell/`.
- `/workspace` URL redirects to launcher (or is removed if no inbound links remain).
- Reviewer page renders Identity · Capabilities · Activity only.
- Launcher icon visible in top-right of shell chrome on every authenticated route.
- Dock renders at bottom (desktop) / bottom-nav (mobile) with default Feed-pinned.
- Last-used surface persists across workspace opens.
- Operator's bookmarks pointing to old container URLs resolve via redirects.
- This ADR's status flips Proposed → Implemented in commit message.
