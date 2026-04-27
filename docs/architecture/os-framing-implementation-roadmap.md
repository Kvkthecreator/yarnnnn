---
title: OS Framing — Implementation Roadmap
date: 2026-04-27
status: planning doc (not an ADR)
related:
  - docs/adr/ADR-222-agent-native-operating-system-framing.md
  - docs/architecture/FOUNDATIONS.md (Principle 16)
  - docs/architecture/GLOSSARY.md (Operating System Framing section)
  - docs/architecture/SERVICE-MODEL.md (Frame 5)
  - docs/programs/README.md
---

# OS Framing — Implementation Roadmap

> **What this is:** a planning doc that scopes the implementation ADRs the agent-native operating system framing implies. Not an ADR itself.
>
> **What this is not:** the implementation. Each item below is its own ADR + build effort, sequenced and dependency-tracked here.

ADR-222 + FOUNDATIONS Principle 16 commit the framing. The framing is meaningful only if the implementation work follows. This doc is the visible-and-trackable plan for that work.

---

## At a glance

| # | ADR (forthcoming) | Scope | Depends on | Touches code? |
|---|---|---|---|---|
| 1 | **Program Bundle Specification** | Composition manifest format, manifest schema, reference workspace conventions, dependency declaration, lifecycle states | None (foundational) | No (spec only) |
| 2 | **Compositor Layer** | FE/API infrastructure: composition resolver, component binding, surface archetype rendering, workspace overlay merger | #1 | Yes (significant) |
| 3 | **System Component Library Convention** | `web/components/library/` formalization: registration, versioning, contribution rules. May fold into #2. | None / paired with #2 | Yes (FE structure) |
| 4 | **Kernel / Program Boundary Refactor** | Split `directory_registry.py`, `task_types.py`, `orchestration.py`, `platform_tools.py` along the kernel boundary. Move program-specific declarations into program bundles. | #1 (bundles must exist as targets) | Yes (significant — registry split + caller rewiring) |
| 5 | **Reference-Workspace Activation Flow** | Operator activation as fork-the-reference + differential-authoring conversation. `workspace_init.py` extension + YARNNN prompt overlay. | #1, #2, #4 | Yes (workspace_init + prompt) |
| 6 | **Reference-Reflexive Loop** | `back-office-reference-graduation` task: drafts graduation candidates from lived workspace into reference workspace + composition manifest. | #5 | Yes (back-office task) |

Steps 1, 2/3, 4 can run in parallel after #1's spec is far enough along to unblock the others. Steps 5 + 6 depend on the earlier steps landing.

---

## ADR 1 — Program Bundle Specification

> **Drafted as [ADR-223](../adr/ADR-223-program-bundle-specification.md) on 2026-04-27.** The summary below is preserved as the roadmap-level scope record; the ADR is the canonical source.

**Goal:** formalize the program bundle layout so all current bundles (`docs/programs/alpha-trader/`, `alpha-prediction/`, `alpha-defi/`) and all future bundles share a consistent shape that the compositor + activation flow + reference-reflexive loop can rely on.

**Decisions to land:**

1. **Manifest schema.** The bundle's `README.md` is currently freeform. The ADR formalizes which sections are required vs. optional, the schema for the success bar, the schema for OS dependencies, the schema for phase milestones. Keeps the freeform discussion-grade content as required, layers structured fields for machine-readable consumption (e.g., dependency-checking).

2. **Composition manifest format.** The shape of `SURFACES.yaml` (or `.md` with structured blocks, or other format). Likely YAML for legibility + parseability. Schema: per-tab composition (what components, fed from which substrate paths, with which framings), overlay rules (per-task-output_kind overlays, per-agent-class overlays), default vs. operator-overridable fields.

3. **Reference workspace conventions.** What's in `reference-workspace/` (file shape, redaction discipline, what graduates from lived → reference). Already sketched in the discourse arc; this ADR formalizes.

4. **Dependency declaration.** Programs declare which kernel features they require (specific primitives, daemons, platform integrations). Compositor + activation flow check dependencies before activating a program.

5. **Lifecycle states.** Active program / reference SPEC / deferred / archived. Lifecycle transitions are governed (e.g., a SPEC graduating to active requires meeting preconditions documented in the SPEC itself).

**Out of scope:**
- Compositor implementation (#2)
- Code refactor to move program-specific declarations into bundles (#4)

**Dependencies:** None. This is the foundational spec.

**Touches code:** No (spec only). The current bundles will be retroactively brought into compliance after the ADR lands.

---

## ADR 2 — Compositor Layer

**Goal:** build the FE/API infrastructure that resolves a program's composition manifest against the operator's workspace substrate and renders the cockpit.

**Decisions to land:**

1. **Composition resolver location.** FE-side (Next.js component-tree resolver), API-side (returns rendered tree), or hybrid (API resolves manifest, FE renders components). Likely hybrid — API returns the resolved component-binding tree, FE renders. Determines API contract.

2. **Component binding model.** How a composition manifest references substrate paths. Static path bindings vs. queries (e.g., "all files under `/workspace/context/portfolio/`"). YAML-friendly schema.

3. **Surface archetype rendering.** How composition manifests express the five surface archetypes from ADR-198 (Document / Dashboard / Queue / Briefing / Stream). Likely each archetype is a typed composition entry; components specialize per archetype.

4. **Workspace overlay merger.** Reading `/workspace/SURFACES.yaml` overrides on top of program-default composition manifest. Three-way merge semantics (program default + workspace overlay + runtime resolution).

5. **Migration path.** The current FE has per-route layout code (e.g., Overview pane, Work tab). The ADR scopes how compositor adoption migrates this — likely a parallel resolver that progressively absorbs hard-coded surfaces, with a deprecation path for direct-render code.

**Out of scope:**
- Specific composition manifests for current programs (those are program-bundle work, land in their respective bundles)
- New components beyond what's needed to make the resolver work end-to-end

**Dependencies:** #1 (manifest format must exist). May ship in parallel with #3 (system component library).

**Touches code:** Yes — significant. New API endpoint(s), new FE infrastructure, progressive migration of existing route layouts.

---

## ADR 3 — System Component Library Convention

**Goal:** formalize `web/components/library/` as the universal component library that composition manifests reference.

**Decisions to land:**

1. **Library structure.** Where components live, registration model, naming conventions.

2. **Component contract.** What every library component must expose: props schema (substrate-path bindings, render variants), accessibility expectations, state ownership rules (read-only vs. mutating).

3. **Versioning expectations.** Additive-only. Removing a component is breaking and requires a deprecation cycle. Versioning at the component level (not library level) — individual components can evolve.

4. **Contribution rules.** When does a component go in the library vs. live in a program-specific path? Library = used by ≥2 programs, OR clear potential utility. Program-specific = only meaningful in that program's context.

5. **Bundle relationship.** A program bundle may reference any component in the library. A program may NOT ship its own components in the bundle (would break the kernel/program boundary). Components contributed *for* a program graduate into the library before the bundle uses them.

**Out of scope:**
- Specific component implementations
- The compositor's binding resolution (that's #2's scope)

**Dependencies:** May fold into #2 if the spec is short enough. Otherwise pairs with #2.

**Touches code:** Yes — FE structure formalization, possibly migration of existing components into the library convention.

---

## ADR 4 — Kernel / Program Boundary Refactor

> **Implemented [ADR-224 v3](../adr/ADR-224-kernel-program-boundary-refactor.md) on 2026-04-27.** v3 reframed the work as **template residue deletion** rather than dispatch refactor — runtime dispatch is already substrate-driven (per ADR-188 + ADR-207); the kernel registries held dead program-specific templates that already had canonical homes in bundle MANIFESTs (post-ADR-223). Bundles are consulted at three specific moments (composition / scaffolding / display metadata), not always-loaded into runtime. The shipped implementation refined v3's caller-fallback pattern to helper-level fallback (callers don't change at all; `get_task_type` / `get_directory` / `_resolve_capability` consult bundles transparently). The summary below is preserved as the roadmap-level scope record; the ADR is the canonical source. Test gate `api/test_adr224_kernel_boundary.py` (11/11 passing) enforces the boundary going forward.

**Goal:** the actual code refactor that moves program-specific declarations out of universal kernel services and into program bundles.

**Decisions to land:**

1. **`api/services/directory_registry.py` split.** Kernel-universal directories (memory, uploads, review, _shared, agents, tasks) stay in the kernel registry. Program-specific directories (e.g., `customers/`, `portfolio/`, `trading/`) move into program bundles, declared in the bundle's composition manifest or a dedicated declaration. Loaders fetch the union (kernel + active-program-bundle's directories) at runtime.

2. **`api/services/task_types.py` split.** Kernel-universal task types (back-office, daily-update) stay. Program-specific task types (`trading-digest`, `revenue-report`, etc.) move into program bundles. Loaders fetch the union.

3. **`api/services/orchestration.py` `AGENT_TEMPLATES` split.** Universal roles stay (the universal six + thinking_partner + reviewer). Program-specific agent configurations (e.g., trader-style Reviewer-principles default) move into bundles or stay as operator-authored in the persona layer.

4. **`api/services/platform_tools.py` split.** `TRADING_TOOLS`, `COMMERCE_TOOLS`, `SLACK_TOOLS`, etc. become program-bundle declarations (a program declares which platform tool surfaces it requires) rather than universal registries. The kernel exposes the platform-connection primitive; programs declare what they use.

5. **Test coverage for the split.** Existing test suites (`test_recent_commits.py`, etc.) get extended to verify the boundary is enforced — kernel registries don't reference program-specific names.

**Out of scope:**
- Program bundle format (#1)
- Compositor build (#2)
- New behavior — this is purely a refactor

**Dependencies:** #1 (bundles must be valid targets to move declarations into).

**Touches code:** Yes — significant. Registry split + caller rewiring across multiple services + test coverage.

---

## ADR 5 — Reference-Workspace Activation Flow

**Goal:** make operator activation a fork-the-reference + differential-authoring flow.

**Decisions to land:**

1. **Activation entry point.** Likely `workspace_init.py` is extended to accept a program selection at signup. Operator selects program → workspace_init copies the bundle's `reference-workspace/` files into the operator's `/workspace/` (filesystem copy, no new primitive).

2. **YARNNN prompt overlay.** The chat agent's prompt gains a differential-authoring overlay activated when a fresh workspace is detected. Conversation shape: *"This is a reference {program} workspace. Walk me through how your discipline differs from this."* Existing chat agent infrastructure; new prompt content.

3. **Compositor activation.** With the bundle selected, the compositor reads the bundle's composition manifest and renders the cockpit accordingly. Empty states render meaningfully because the forked substrate provides shape.

4. **Default vs. selection.** What happens if the operator doesn't select a program? Two options: a generic-mode default (cockpit horizontally), or a mode-picker as the first onboarding step. Likely the mode-picker — the empty-state-as-onboarding gain is forfeited under generic mode.

**Out of scope:**
- Bundle format (#1)
- Compositor (#2)
- Reverse channel — propagating reference upstream changes back to forked workspaces (that's #6's scope or a separate ADR)

**Dependencies:** #1 (bundle format), #2 (compositor must render the bundled composition), #4 (boundary refactor must have moved program-specific declarations into bundles for the activation copy to work cleanly).

**Touches code:** Yes — `workspace_init.py` extension, YARNNN prompt overlay, possibly signup flow UI.

---

## ADR 6 — Reference-Reflexive Loop

**Goal:** ship the back-office task that graduates lived workspace patterns to reference workspace canon, closing the loop sketched in the discourse arc.

**Decisions to land:**

1. **Back-office task design.** New task: `back-office-reference-graduation`. YARNNN-owned, weekly cadence (or other — TBD). Reads the lived workspace + `_performance.md` + recent feedback substrate, identifies graduation candidates, drafts reference updates as proposals against `action_proposals`.

2. **Graduation criteria.** What graduates: structure (signal definitions, principles, conventions, empty-state resolutions, FE surface needs surfaced in practice). What stays: content (specific P&L numbers, broker history, in-flight experiments not yet validated, kvk-personal preferences not validated by oracle).

3. **Redaction discipline.** Sanitization rules for `_performance.md` graduation (schema + anonymized examples, not actual numbers). API-key/credential exclusion rules (already covered by current substrate practices). Timestamp anonymization where applicable.

4. **Approval flow.** Reviewer queue handles graduation candidates same as any other proposal. Approved → diff committed to the program bundle (in-repo) with a graduation note. Authored substrate (ADR-209) tracks the revision.

5. **Source extension for cross-operator compounding.** When N+1 operators are running the same program, graduation reads from the union of lived workspaces. Multi-operator validation strengthens graduation confidence. Privacy-preserved (each lived workspace's content stays private; only structural patterns graduate).

**Out of scope:**
- Reverse channel UI (operators receiving notifications about upstream reference changes — separate concern)
- Multi-program operator handling

**Dependencies:** #5 (activation flow must be live so there's something graduating *into*).

**Touches code:** Yes — new back-office task, possibly extensions to `action_proposals` for graduation-shaped diffs.

---

## Sequencing summary

```
                 ┌─────────────────────────────────┐
                 │ ADR 1: Program Bundle Spec      │
                 │ (foundation, no code)           │
                 └───────────┬─────────────────────┘
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────┐
        │ ADR 2:   │  │ ADR 3:   │  │ ADR 4:       │
        │ Compositor│  │ Component│  │ Kernel/      │
        │ Layer    │  │ Library  │  │ Program      │
        │          │  │ (may fold│  │ Refactor     │
        │          │  │  into 2) │  │              │
        └────┬─────┘  └────┬─────┘  └──────┬───────┘
             │             │               │
             └─────────────┼───────────────┘
                           ▼
                  ┌────────────────────┐
                  │ ADR 5:             │
                  │ Reference Activation│
                  │ Flow               │
                  └─────────┬──────────┘
                            ▼
                  ┌────────────────────┐
                  │ ADR 6:             │
                  │ Reference-Reflexive│
                  │ Loop               │
                  └────────────────────┘
```

---

## Out of scope for this roadmap

These are real architectural concerns that follow from the OS framing but are explicitly NOT in this roadmap:

- **Multi-program operators.** When an operator runs alpha-trader and (later) alpha-commerce. Workspace overlay model handles single-program override; multi-program is its own design question. Defer until the second program activates.
- **Public-readable program bundle rendering.** Letting marketing surfaces render reference workspaces as public demos. Real possibility, defer until marketing pressure or evidence of utility.
- **Cross-operator compounding rendering.** When 3+ operators run the same program, the reference becomes empirically aggregated. Surfacing that empirical aggregation to operators (e.g., "5 alpha-trader operators converged on this principle") is its own design question. Real but downstream.
- **Live composition editing UI.** Letting operators edit `/workspace/SURFACES.yaml` via a visual composer. Real possibility, defer until evidence of demand.
- **Cross-program system component contributions.** When alpha-defi (if/when activated) needs a `WalletPane` component. PR convention; folds into #3.

---

## Status tracking

| ADR | Status | ETA |
|---|---|---|
| ADR 1 — Program Bundle Spec | **Implemented** ([ADR-223](../adr/ADR-223-program-bundle-specification.md), 2026-04-27) — alignment commit `3237b89`; ADR-224 implementation validated schema by exercising bundle-side enrichment without schema bump | Done |
| ADR 2 — Compositor Layer | Not started | Independent of ADR 4 per ADR-224 v3 (compositor reads SURFACES.yaml directly; runtime stays substrate-driven). Next sequenced. |
| ADR 3 — System Component Library | Not started | Pairs with ADR 2 |
| ADR 4 — Kernel/Program Boundary Refactor | **Implemented** ([ADR-224 v3](../adr/ADR-224-kernel-program-boundary-refactor.md), 2026-04-27) — bundle_reader.py + 4-capability + 4-directory + 3-task-type kernel deletions + alpha-commerce deferred bundle + 11/11 test gate | Done |
| ADR 5 — Reference Activation Flow | Not started | Depends on ADR 2 (compositor reads bundle's SURFACES.yaml at activation). alpha-commerce bundle now exists per ADR-224. |
| ADR 6 — Reference-Reflexive Loop | Not started | After ADR 5 lands |

This doc is updated as ADRs are written, ratified, and implemented.
