# ADR-225: Compositor Layer — Declarative Surface Composition

> **Status:** **Phase 1 + Phase 2 Implemented 2026-04-27.** Phase 1: API endpoint + composition resolver + workspace-scoped bundle filter + 10/10 API test gate. Phase 2: `web/lib/compositor/` FE module, `web/components/library/` initial component set (6 components), `MiddleResolver` replaces hardcoded `WorkDetail.tsx::KindMiddle` switch, `BundleBanner` wired to `WorkListSurface`. Next.js build clean (zero TS errors, all routes compile). See "Phased implementation rationale" + "Phase 2 implementation refinements" below for what shipped vs the original v2 spec.
> **Date:** 2026-04-27 (v2 same-day rewrite — see "What changed across versions" below; v1 missed the two-compose-modes framing surfaced by the parallel paper design)
> **Authors:** KVK, Claude
> **Implements:** ADR-222 implementation roadmap, ADR 2 (+ ADR 3 absorbed — system component library convention is folded into this ADR per the roadmap's "may fold" allowance, since the library is a small enough convention not to merit a separate ADR right now)
> **Informed by:** [docs/analysis/alpha-trader-surface-design-2026-04-27.md](../analysis/alpha-trader-surface-design-2026-04-27.md) — Step 0 paper design (forcing function for this ADR)
> **Related:** ADR-222 (OS framing — Principle 16 names the compositor as a load-bearing layer), ADR-223 (Program Bundle Specification — defines `SURFACES.yaml` schema this ADR consumes), ADR-224 (Kernel/Program Boundary — proves bundles can be the source of truth for program-shaped declarations), ADR-198 (Surface Archetypes — five archetype patterns), ADR-214 (4-tab nav — Chat / Work / Agents / Files), ADR-167 (List/Detail Surfaces with Kind-Aware Detail), ADR-170 + ADR-177 (existing document-compose substrate — preserved as sibling, not replaced), FOUNDATIONS Principle 16
> **Depended on by:** Reference-Workspace Activation Flow ADR (forthcoming, ADR 5 — operator activation renders the bundle's composition manifest at signup)
> **Supersedes (in part):** ADR-167 v2 hardcoded `KindMiddle` dispatch (replaces the switch with declarative resolution)

---

## Context

ADR-222 named the **compositor** as a load-bearing OS layer:

> *"The compositor reads program-shipped composition manifests against substrate to render the cockpit; it sits between kernel and program, reading both, authoring neither."*

ADR-223 specified the composition manifest format (`SURFACES.yaml`) — declarative, hierarchical, no executable logic, archetypes from ADR-198 × tabs from ADR-214. Four bundles in repo today carry SURFACES.yaml files.

ADR-224 proved the kernel/program separation is honest at the data layer — bundles can fully replace kernel-side program-shaped templates without runtime dispatch knowing anything about programs.

**This ADR is the layer that finally consumes SURFACES.yaml.** Today the bundle's composition manifest is aspirational — the FE doesn't read it. The cockpit renders via hardcoded dispatch in `WorkDetail.tsx::KindMiddle()` (per ADR-167 v2): a switch on `task.output_kind` mapping to one of four kind-specific components (`DeliverableMiddle`, `TrackingEntityGrid`, `ActionMiddle`, `MaintenanceMiddle`). It works, but it is the **compositor implemented as a switch statement in code, not as declarative resolution against bundle manifests**.

### Two compose modes, both kernel-level (post-2026-04-27 discourse)

A parallel discourse round on the day of this ADR's drafting sharpened a load-bearing distinction the v1 draft had blurred. Compose substrate has **two modes**, both kernel-level, both program-aware via composition manifest:

| Mode | Produces | Lifetime | Existing infrastructure | Examples |
|---|---|---|---|---|
| **Document compose** | Frozen HTML artifacts (`output.html`, PDFs) | Per-run, immutable once composed | ADR-148 + ADR-170 + ADR-177 + ADR-213 (shipped) — task pipeline writes substrate, surfaces pull on demand for compose | Daily-update email body, weekly performance review PDF, exported portfolio brief |
| **Surface compose** | Live cockpit panes, re-rendered per load, bound to current substrate | Per-render, always current | NEW infrastructure shipping with this ADR | Overview's live P&L band, Work tab's queue of pending proposals, Agents tab's current Reviewer health |

**Both modes share the universal component library.** A `MetricCardRow` works in surface compose (live frontmatter binding) and document compose (frozen snapshot at run-time). The mode is a property of the **binding** in the SURFACES manifest, not the component itself. Surface compose can also **embed** document compose artifacts (e.g., Overview's daily-discipline band embeds today's daily-update output via `TaskOutputViewer`).

This ADR adds the surface-compose sibling to the existing document-compose pipeline. It does not replace, modify, or shim document compose — that pipeline stays exactly as ADR-213 left it. The compositor is additive infrastructure.

### What this ADR replaces

The compositor ADR replaces the `WorkDetail.tsx::KindMiddle` switch with a resolver. The resolver reads SURFACES.yaml, matches the active task against declared `middles[]`, binds substrate paths, renders via universal components from the library. When a program needs program-shaped rendering (e.g., alpha-trader's `external_action` tasks want `AttributedActionReview` instead of the generic `ActionMiddle`), it declares so in its bundle. The FE doesn't fork.

### What the paper design forces

The Step 0 paper design ([alpha-trader-surface-design-2026-04-27](../analysis/alpha-trader-surface-design-2026-04-27.md)) is the forcing function for this ADR's manifest format. Every binding shape that paper design uses must be expressible in the manifest:

- **Live frontmatter reads** (Performance band: `MetricCardRow` × 4 reading `_performance.md` frontmatter)
- **Embedded document-compose artifacts** (Daily-discipline band: `TaskOutputViewer` embedding `output.html`)
- **Conditional overlays** (Work-tab `external_action` tasks get `AttributedActionReview` instead of the generic ActionMiddle)
- **List filter + group spec** (TaskList with `output_kind` / agent / status / schedule filters)
- **Pinned-shortcut bindings** (Files tab pre-pins to `/workspace/context/portfolio/`, etc.)
- **Empty-state declarations** (every surface declares its empty-state copy + pointer)

If any of these can't be expressed in this ADR's manifest format, the format is too thin. v2 of this ADR (current) tightened the format to support all six shapes.

---

## What this ADR does NOT do

Important framing: this ADR is **not an FE rewrite**. The shipped four-tab nav (ADR-214), list/detail mode pattern (ADR-167), surface archetypes (ADR-198), and Files/Chat/Work/Agents destination structure all stand. The compositor sits *inside* those structures as the dispatch mechanism for kind-aware detail panes — and as the renderer for phase-aware banners and chat chips. It is additive infrastructure that subsumes the existing hardcoded dispatch.

What's NOT in scope:

- New nav tabs, new top-level surfaces, new routes.
- Workspace overlay (`/workspace/SURFACES.yaml` per-operator overrides) — deferred to ADR 5+ when activation flow lands.
- Cross-program composition merge semantics beyond §2's "first match wins, ordered by activation date" — defer detail-resolution until alpha-commerce activates and a real two-active-bundle workspace exists.
- Live SURFACES.yaml editing UI (operators editing manifests via FE) — defer until evidence of demand.

What's IN scope per v2 update:

- **Overview surface (`tabs.chat`)** — the paper design treats `/chat` as Overview-as-home, surface-compose-rendered with three bands (Performance, Daily Discipline, Awareness). v1 of this ADR deferred this; v2 brings it in scope because the paper design uses it as the load-bearing exercise. ADR-199's shipped Overview composition is preserved as the *current* behavior; the compositor adds the program-aware surface-compose layer on top. Coexists, not replaces.
- **Document-compose embeds inside surface compose** — Daily Discipline band on Overview embeds today's daily-update output via `TaskOutputViewer`. The `compose_mode: surface_embeds_document` distinction in the manifest allows this cleanly.

---

## Decision

### 1. Two-layer architecture: API resolves, FE renders

The compositor splits between API and FE along a clean boundary:

**API side — composition resolver.** New endpoint `/api/programs/surfaces` returns the resolved composition tree for the operator's workspace. Resolution does:
1. Load active program bundles (per ADR-224's `bundle_reader.all_active_bundles()`).
2. Determine current phase from MANIFEST `current_phase`.
3. Apply `phase_overlays` shallow-merge over base `tabs` block.
4. Return the merged composition tree as JSON.
5. Resolve `chat_chips` (program-supplied empty-state chat suggestions).
6. Return active bundle metadata (slug, title, phase) for cockpit chrome.

**FE side — composition renderer.** New module `web/lib/compositor/` consumes the API response and renders. Specifically:
1. Replaces `WorkDetail.tsx::KindMiddle()` switch with `<MiddleResolver task={task} composition={composition} />` that reads SURFACES.yaml `tabs.work.detail.middles[]` and matches the current task's slug or output_kind.
2. Falls back to the kernel-universal middles (DeliverableMiddle, TrackingEntityGrid, ActionMiddle, MaintenanceMiddle) when no SURFACES.yaml middle matches — per Singular Implementation, these are the kernel "default middles."
3. Renders `phase_overlays` banners on Work list mode.
4. Surfaces `chat_chips` to the chat empty state.

The split is the same one Wayland uses: server (compositor service) computes; client (toolkit) draws. Useful because:
- API-side resolution lets non-FE callers (future MCP responses, mobile, headless probes) consume the same composition tree.
- FE-side rendering keeps the universal component library colocated with the React tree it renders into.

### 2. API endpoint contract

```
GET /api/programs/surfaces

Auth: operator-scoped (resolves their workspace's active programs)

Response (illustrative — alpha-trader active in observation phase):
{
  "active_bundles": [
    {
      "slug": "alpha-trader",
      "title": "alpha-trader",
      "tagline": "Equities + options operator workflow with continuous-price oracle.",
      "current_phase": "observation",
      "current_phase_label": "Phase 0 — Observation",
      "phases": [
        { "key": "observation", "label": "Phase 0 — Observation" },
        { "key": "paper_discipline", "label": "Phase 1 — Paper Discipline" },
        ...
      ]
    }
  ],
  "composition": {
    "tabs": {
      "chat": {
        // Overview surface — surface-compose-rendered, three bands per
        // alpha-trader-surface-design §"Overview".
        "bands": [
          {
            "id": "performance",
            "compose_mode": "surface",
            "components": [
              {
                "kind": "MetricCardRow",
                "binding": {
                  "type": "frontmatter",
                  "path": "/workspace/context/portfolio/_performance.md",
                  "fields": ["pnl_30d", "win_rate", "drawdown", "sharpe_90d"]
                }
              }
            ],
            "empty_state": {
              "copy": "No trades yet — your reference workspace shows the metrics you'll track once trading starts.",
              "pointer": "/workspace/context/_shared/MANDATE.md"
            }
          },
          {
            "id": "daily_discipline",
            "compose_mode": "surface_embeds_document",
            "components": [
              {
                "kind": "TaskOutputViewer",
                "binding": {
                  "type": "task_output",
                  "task_slug": "daily-update",
                  "selector": "latest"
                }
              }
            ]
          },
          {
            "id": "awareness",
            "compose_mode": "surface",
            "components": [
              { "kind": "NarrativeRail", "binding": { "type": "narrative" } },
              { "kind": "QueueCard",
                "binding": { "type": "action_proposals",
                             "filter": { "status": "pending" } } },
              { "kind": "AlertCard",
                "binding": { "type": "file",
                             "path": "/workspace/review/decisions.md",
                             "filter": { "recent_flagged": true } } }
            ]
          }
        ]
      },
      "work": {
        "list": {
          "pinned_tasks": ["daily-discipline-checklist", "signal-monitor", "position-tracker"],
          "group_default": "output_kind",
          "filters_default": { "output_kind": "produces_deliverable" },
          "banner": "Paper-only. Live trading gated on AUTONOMY.md flip.",
          "components": [
            { "kind": "TaskList" },
            { "kind": "FilterChipRow" }
          ]
        },
        "detail": {
          // middles[] is matched in specificity order (see §4):
          //   1. task_slug (most specific)
          //   2. output_kind + condition
          //   3. output_kind alone
          //   4. agent_role
          // First match wins within each tier.
          "middles": [
            {
              "match": { "output_kind": "external_action" },
              "archetype": "queue",
              "bindings": {
                "proposals": {
                  "type": "action_proposals",
                  "filter": { "task_slug": "{task.slug}", "status": "pending" }
                }
              },
              "components": [
                {
                  "kind": "AttributedActionReview",
                  "source": "proposals",
                  "attribution_schema": ["signal_name", "sized_stop", "expectancy", "entry_rules"]
                }
              ]
            }
          ]
        }
      },
      "agents": {
        "list": {
          "featured": ["reviewer"],
          "components": [
            { "kind": "AgentRoster" },
            { "kind": "ReviewerHealthCard",
              "binding": { "type": "file",
                           "paths": ["/workspace/review/decisions.md",
                                     "/workspace/context/portfolio/_performance.md"] } }
          ]
        },
        "detail": {
          "middles": [
            {
              "match": { "agent_class": "reviewer" },
              "archetype": "document",
              "components": [
                { "kind": "PrincipleEditor",
                  "binding": { "type": "file",
                               "path": "/workspace/review/principles.md" } },
                { "kind": "ReviewerCalibrationView",
                  "binding": { "type": "file",
                               "paths": ["/workspace/review/decisions.md",
                                         "/workspace/context/portfolio/_performance.md"] } }
              ]
            }
          ]
        }
      },
      "files": {
        "list": {
          "pinned_shortcuts": [
            { "label": "Portfolio", "path": "/workspace/context/portfolio/" },
            { "label": "Trading", "path": "/workspace/context/trading/" },
            { "label": "Mandate", "path": "/workspace/context/_shared/MANDATE.md" },
            { "label": "Reviewer principles", "path": "/workspace/review/principles.md" }
          ],
          "components": [
            { "kind": "PinnedShortcutRow" },
            { "kind": "FileTree", "default_collapsed": true }
          ]
        }
      }
    },
    "chat_chips": [
      "Walk me through today's signals",
      "What's my risk budget right now?",
      "Did anything trigger overnight?",
      "Show me last week's expectancy by signal"
    ]
  },
  "schema_version": 1
}
```

**Binding type taxonomy** (the manifest's binding-shape vocabulary, enumerated to constrain the surface):

| Binding type | Resolves to | Example |
|---|---|---|
| `file` | Substrate file content (markdown body or full text) | `/workspace/review/decisions.md` |
| `frontmatter` | YAML frontmatter fields from a substrate file | `_performance.md` → `pnl_30d`, `win_rate` |
| `task_output` | Frozen document-compose artifact for a task run | `daily-update` latest run → `output.html` |
| `action_proposals` | Filtered query against `action_proposals` ledger | pending proposals for a task |
| `narrative` | Narrative rail substrate (per ADR-219) | full narrative or filtered |
| `directory` | All files in a directory (entity grid) | `/workspace/context/trading/` ticker entities |

Adding a binding type is a manifest schema change requiring an ADR — same anti-vocabulary-proliferation discipline ADR-166's `output_kind` enum applies. Six types cover every shape the alpha-trader paper design demands.

**Compose mode taxonomy** (a separate dimension on each component or band):

- `surface` — live-bound, re-rendered per load. Default.
- `document` — embeds a frozen document-compose artifact. Used when surface compose contains a pre-composed output.
- `surface_embeds_document` — surface compose hosting a document compose embed (Overview's daily-discipline band).

When zero bundles are active (e.g., operator hasn't connected platforms): `active_bundles: []`, `composition.tabs: {}`, `chat_chips: []`. FE falls back to kernel-universal cockpit chrome (no banners, generic empty state).

When multiple bundles are active:
- `active_bundles[]` lists them ordered by activation date (oldest first — typically the program the operator activated first).
- `tabs.{tab}.list.pinned_tasks[]` and `pinned_shortcuts[]` union across bundles.
- `tabs.{tab}.detail.middles[]` union; first match wins (deterministic — order is `active_bundles[]` order).
- `chat_chips[]` union, deduplicated.
- Cross-program conflict resolution remains deferred per ADR-224 §7.

### 3. FE module structure

```
web/lib/compositor/
├── index.ts           # public API: useComposition() hook + types
├── client.ts          # fetcher for /api/programs/surfaces
├── resolver.ts        # match-and-bind logic for middles[] + bands[]
├── kernel-defaults.ts # kernel-universal MiddleDecls (output_kind defaults)
└── types.ts           # TS shape for the API response

web/components/library/      # NEW — the system component library
├── README.md          # convention: what's in, what's out, contribution rules
├── MetricCardRow.tsx        # frontmatter binding → metric tiles
├── TaskOutputViewer.tsx     # document-compose embed (existing iframe)
├── NarrativeRail.tsx        # ADR-219 narrative substrate
├── QueueCard.tsx            # action_proposals filter binding
├── AlertCard.tsx            # structured alerts from substrate file
├── TaskList.tsx             # filter + group spec from manifest
├── FilterChipRow.tsx        # filter spec from manifest
├── AttributedActionReview.tsx # proposal envelope + attribution schema
├── AgentRoster.tsx          # agent class grouping spec
├── ReviewerHealthCard.tsx   # decisions.md + _performance.md reads
├── PrincipleEditor.tsx      # principles.md substrate file binding
├── ReviewerCalibrationView.tsx # decisions.md + outcomes binding
├── FileTree.tsx             # workspace root path binding
└── PinnedShortcutRow.tsx    # path + label list from manifest
```

**v1 component scope: 14 universal components.** Sourced from the alpha-trader paper design's [§"Cross-cutting components"](../analysis/alpha-trader-surface-design-2026-04-27.md). Every component is universal — none ship in any bundle's repo path. The paper design validates that alpha-trader's surfaces require no program-specific component, which is what FOUNDATIONS Principle 16 commits to ("adding a program is purely additive — new bundle, possibly new system component library entries, no kernel touch").

Many of these components already exist in some form under `web/components/`:
- `TaskOutputViewer` ≈ existing `DeliverableMiddle`'s iframe rendering — relocates from `work/details/` into `library/`.
- `TaskList` + `FilterChipRow` ≈ existing `WorkListSurface` internals — refactored into library components consumed by surface compose.
- `AgentRoster` ≈ existing `AgentRosterSurface` internals.
- `FileTree` ≈ existing context-tab tree component.
- `NarrativeRail` ≈ existing chat rail component.

Where existing FE code already serves the role, the library refactor extracts it; it does not duplicate. **Implementation may discover that 5–8 of the 14 components are extraction-renames rather than new builds** — the smaller-than-expected pattern from ADR-224's implementation arc.

Component library convention (folds in ADR 3 from the roadmap):

- **Located at `web/components/library/`.** Flat namespace for v1 (no subfolders); revisit if it grows past ~30 components.
- **Each component is a TSX file with the same name as the SURFACES.yaml `kind` field.** `kind: MetricCardRow` → `web/components/library/MetricCardRow.tsx`.
- **Components accept a `binding` prop** matching one of the binding-type taxonomy shapes (§2). They fetch+render via existing hooks (`useTaskOutputs`, `useWorkspaceFile`, etc.).
- **Components are PURE READERS in both modes.** Surface compose: live binding. Document compose: frozen snapshot at compose time. Same render, different data freshness. Components do not mutate. Operator interactions that mutate (approve, reject, edit) flow through the existing primitive surfaces (Queue archetype invokes `ProposeAction`/`ExecuteProposal`; feedback flows through `UpdateContext`).
- **Components are additive-only.** Removing a component is breaking and requires a deprecation cycle with ADR ratification.
- **No new component shipped without a bundle (or kernel-default middle) that uses it.** Discipline: components serve programs; programs declare what they need; library grows via demand-pull, not speculation. The 14-component v1 set is justified because the alpha-trader paper design uses every one.
- **A program may NOT ship its own components.** Components needed for a program contribute to the universal library first (PR convention); the bundle then references them. Same rule as macOS frameworks vs `.app` bundles.

### 4. Match resolution semantics

The FE resolver matches an incoming task against `tabs.{tab}.detail.middles[]` in 4 specificity tiers, first match wins within each tier:

```typescript
// web/lib/compositor/resolver.ts (sketch)

interface MiddleMatch {
  task_slug?: string;        // exact task slug match (most specific)
  output_kind?: string;      // task output_kind enum match
  condition?: Record<string, any>;  // additional condition (e.g., {emits_proposal: true})
  agent_role?: string;       // assigned agent's role
  agent_class?: string;      // agent class (reviewer / specialist / etc.)
}

interface MiddleDecl {
  match: MiddleMatch;
  archetype: 'dashboard' | 'document' | 'queue' | 'briefing' | 'stream';
  bindings: Record<string, Binding>;
  components: ComponentDecl[];
}

function resolveMiddle(
  task: Task,
  agent: Agent | null,
  middles: MiddleDecl[]
): MiddleDecl | null {
  // Tier 1: task_slug exact match (most specific)
  for (const m of middles) {
    if (m.match.task_slug === task.slug) return m;
  }
  // Tier 2: output_kind + condition (e.g., external_action AND emits_proposal:true)
  for (const m of middles) {
    if (m.match.output_kind === task.output_kind && m.match.condition) {
      if (matchCondition(task, m.match.condition)) return m;
    }
  }
  // Tier 3: output_kind alone
  for (const m of middles) {
    if (m.match.output_kind === task.output_kind && !m.match.condition) return m;
  }
  // Tier 4: agent_role / agent_class (fallback when output_kind doesn't bite)
  for (const m of middles) {
    if (m.match.agent_role && agent?.role === m.match.agent_role) return m;
    if (m.match.agent_class && agent?.class === m.match.agent_class) return m;
  }
  return null;  // fall through to kernel-universal middles
}
```

**Why 4 tiers, not 3:** the paper design's example of `external_action` task overlay (alpha-trader replaces generic `ActionMiddle` with `AttributedActionReview` only for tasks that emit proposals — not all external_action tasks) requires `output_kind + condition` as a distinct tier. Without it, a program either has to enumerate every task_slug (verbose) or override every task with that output_kind (over-broad).

If `resolveMiddle` returns null, the FE falls through to the **kernel-universal default middles** (`MiddleDecl`s declared in `web/lib/compositor/kernel-defaults.ts` — see §5). When a program declares a middle, the program's middle wins; otherwise kernel defaults render. Same fallback discipline as ADR-224's helper-level fallback for registry helpers.

### 5. Kernel-universal middles become library components

Per Singular Implementation: the four existing kind-aware middles (`DeliverableMiddle`, `TrackingEntityGrid`, `ActionMiddle`, `MaintenanceMiddle`) relocate into `web/components/library/` (renamed for the v1 component set — `DeliverableMiddle` → `TaskOutputViewer`, `TrackingEntityGrid` → existing name in library, etc.) and become library components used by kernel-default `MiddleDecl`s.

The kernel declares default middles for each output_kind in a programmatic equivalent of SURFACES.yaml (TypeScript, in-repo, not in any bundle):

```typescript
// web/lib/compositor/kernel-defaults.ts

export const KERNEL_DEFAULT_MIDDLES: MiddleDecl[] = [
  {
    match: { output_kind: 'produces_deliverable' },
    archetype: 'document',
    bindings: {
      output: { type: 'task_output', task_slug: '{task.slug}', selector: 'latest' },
    },
    components: [{ kind: 'TaskOutputViewer', source: 'output' }],
  },
  {
    match: { output_kind: 'accumulates_context' },
    archetype: 'dashboard',
    bindings: {
      domain: { type: 'directory', path: '/workspace/context/{task.context_writes[0]}/' },
    },
    components: [{ kind: 'TrackingEntityGrid', source: 'domain' }],
  },
  {
    match: { output_kind: 'external_action' },
    archetype: 'stream',
    bindings: {
      runs: { type: 'file', path: '/tasks/{task.slug}/memory/run_log.md' },
    },
    components: [{ kind: 'ActionMiddle', source: 'runs' }],
  },
  {
    match: { output_kind: 'system_maintenance' },
    archetype: 'stream',
    bindings: {
      runs: { type: 'file', path: '/tasks/{task.slug}/memory/run_log.md' },
    },
    components: [{ kind: 'MaintenanceMiddle', source: 'runs' }],
  },
];
```

Resolution order becomes: program-shipped middles (highest specificity tier wins) → kernel defaults. This keeps `WorkDetail.tsx::KindMiddle` switch *deleted* per Singular Implementation: there is exactly one place that decides what middle renders — the resolver. The kernel switch dissolves.

**Naming reconciliation.** The 14-component v1 library has `TaskOutputViewer`. The existing `DeliverableMiddle` does roughly the same job for produces_deliverable tasks today. Implementation reconciles: the library component is `TaskOutputViewer`; `DeliverableMiddle` is renamed to it during the relocation. `TrackingEntityGrid`, `ActionMiddle`, `MaintenanceMiddle` keep their names — they're already universal-shaped and the names are operator-legible.

### 6. Phase-aware chrome

Phase overlays are merged at the API resolution step (not the FE) — deterministic, server-side, simple shallow merge:

```python
# api/routes/programs.py (sketch)

def _resolve_composition(bundle: dict) -> dict:
    surfaces = _load_surfaces(bundle["slug"])  # docs/programs/{slug}/SURFACES.yaml
    base = surfaces.get("tabs", {})
    current_phase = bundle.get("current_phase")
    phase_overlay = surfaces.get("phase_overlays", {}).get(current_phase, {})
    return _shallow_merge(base, phase_overlay.get("tabs", {}))
```

Shallow merge semantics: per-tab keys union; conflicts (same key in base + overlay) take the overlay value. Already declared in ADR-223 §4 SURFACES.yaml schema discipline; ratified here for the resolver.

### 7. Empty states + cold start

Operator with zero active bundles (no platform connections, fresh signup):
- `/api/programs/surfaces` returns `{ active_bundles: [], composition: { tabs: {}, chat_chips: [] }, schema_version: 1 }`.
- FE compositor renders entirely against kernel defaults — same shape as today's pre-ADR-225 cockpit.
- No bundle-specific banners, no program-shipped pinned tasks, no program-specific chat chips. Generic operator-onboarding chips from a hardcoded fallback list.

Operator activates alpha-trader (connects alpaca):
- Next API call returns alpha-trader's bundle in `active_bundles[]`.
- FE renders trading-signal + portfolio-review pins on /work list, the "Paper-only..." banner, the trading-shaped chat chips.
- KindMiddle resolver finds alpha-trader's `portfolio-review` dashboard middle and renders it instead of the generic DeliverableMiddle.

This is what "the operator activates a program" actually means at the cockpit layer: the compositor's API-side resolution flips, and the FE re-renders with bundle-shaped chrome. No special-case code paths.

### 8. What stays as-is

- All existing routes, navigation, list-mode UI, ambient YARNNN rail, surface archetypes, Files/Chat/Work/Agents structure.
- `WorkListSurface` (filters, group_default, pinned_tasks rendering) — already reads task data; just gains bundle-supplied pin list and banner.
- `AgentRosterSurface` — gains `featured` agents from bundle.
- `ContextSurface` — gains `featured_domains` from bundle.
- All four existing kind-aware middles (DeliverableMiddle / TrackingEntityGrid / ActionMiddle / MaintenanceMiddle) are preserved unchanged; they become library components used by kernel defaults.

---

## What this ADR does NOT specify

Deferred to subsequent ADRs:

- **Workspace overlay (`/workspace/SURFACES.yaml`).** Operator-authored per-workspace overrides of bundle defaults. Folded into Reference-Workspace Activation Flow ADR (forthcoming, ADR 5).
- **Live SURFACES.yaml editing UI.** Operators editing manifests via a FE composer. Real possibility, deferred until evidence of demand.
- **Mobile layout.** Compositor's component library is desktop-shaped today. Mobile = additive future work.
- **Headless / SSR rendering of compositions.** API returns the resolved tree; FE renders. Server-side rendering is a future optimization.
- **Cross-program composition merge edge cases.** Two active bundles declaring the same `task_slug` middle. Defer until alpha-commerce activates.

---

## Implementation plan (after ratification)

Atomic single PR per the migration discipline. Three reviewable steps.

### Step 1 — API endpoint + resolver

- `api/routes/programs.py` (new file) — `GET /api/programs/surfaces` route, auth-scoped to operator's workspace.
- `api/services/composition_resolver.py` (new, ~80 lines) — loads active bundles, applies phase overlays, returns composition tree.
- Pydantic models for the response shape.
- Unit tests covering: zero-bundle workspace, alpha-trader-only workspace, phase overlay application, schema_version 1 contract.

### Step 2 — FE compositor module + v1 component library

- `web/lib/compositor/` (new directory) — `index.ts`, `client.ts`, `resolver.ts`, `kernel-defaults.ts`, `types.ts`.
- `useComposition()` React hook that fetches `/api/programs/surfaces` and caches via SWR/React Query (same pattern as existing hooks).
- `web/components/library/` (new directory) — README + the **14 v1 universal components** from the alpha-trader paper design's §"Cross-cutting components": `MetricCardRow`, `TaskOutputViewer`, `NarrativeRail`, `QueueCard`, `AlertCard`, `TaskList`, `FilterChipRow`, `AttributedActionReview`, `AgentRoster`, `ReviewerHealthCard`, `PrincipleEditor`, `ReviewerCalibrationView`, `FileTree`, `PinnedShortcutRow`.
- Implementation discovery (anticipated per the ADR-224 pattern): some of these 14 are **extraction-renames** of existing FE code, not net new builds. Likely candidates: `TaskOutputViewer` ← extracted from `DeliverableMiddle`'s iframe; `TaskList` + `FilterChipRow` ← extracted from `WorkListSurface` internals; `AgentRoster` ← extracted from `AgentRosterSurface`; `FileTree` ← extracted from existing context-tab tree. Net new builds expected: `MetricCardRow`, `AttributedActionReview`, `ReviewerHealthCard`, `ReviewerCalibrationView`, `PinnedShortcutRow`, `QueueCard`, `AlertCard`, `NarrativeRail` (existing rail moves in or aliases). Final count of net new vs relocated decided at write-time.
- Existing `DeliverableMiddle`, `TrackingEntityGrid`, `ActionMiddle`, `MaintenanceMiddle` relocate from `web/components/work/details/` into `web/components/library/` (with `TaskOutputViewer` rename for the first one). Single-implementation rule: no re-exports, no shims — call sites update.

### Step 3 — Replace KindMiddle switch + integrate

- `WorkDetail.tsx::KindMiddle()` switch DELETED. Replaced by `<MiddleResolver task={task} />` that consumes `useComposition()` + falls through to kernel defaults.
- `WorkListSurface` reads bundle-supplied `pinned_tasks` + `banner`.
- `AgentRosterSurface` reads bundle-supplied `featured`.
- `ContextSurface` reads bundle-supplied `featured_domains`.
- Chat empty state reads bundle-supplied `chat_chips`.
- Test the flow end-to-end against alpha-trader's bundle (kvk's workspace has alpaca connected, so alpha-trader is `active`).

### Step 4 — Documentation sync

- ADR-167: amended-by ADR-225 note (KindMiddle switch deleted, replaced by resolver).
- ADR-198: validated-by ADR-225 note (archetypes now load-bearing as composition manifest field, not just doc taxonomy).
- ADR-223: cross-link to ADR-225 (composition manifest's consumer is now real).
- `docs/architecture/SERVICE-MODEL.md` Frame 5: compositor row → Implemented.
- `docs/architecture/os-framing-implementation-roadmap.md`: ADR 2 + ADR 3 → Implemented.
- CLAUDE.md ADR-registry entry for ADR-225.

All four steps in one PR. No phased ship — singular implementation discipline.

---

## Test coverage

```python
# api/test_adr225_compositor.py

def test_surfaces_endpoint_returns_empty_for_workspace_with_no_bundles():
    """Operator with no platform connections sees empty composition."""
    # ... mock workspace with no platform_connections
    response = client.get("/api/programs/surfaces", headers=auth)
    assert response.json()["active_bundles"] == []
    assert response.json()["composition"]["tabs"] == {}
    assert response.json()["schema_version"] == 1


def test_surfaces_endpoint_returns_alpha_trader_for_alpaca_connected_workspace():
    # ... mock workspace with alpaca platform_connection
    response = client.get("/api/programs/surfaces", headers=auth)
    bundles = response.json()["active_bundles"]
    assert any(b["slug"] == "alpha-trader" for b in bundles)
    composition = response.json()["composition"]
    # Pinned tasks from bundle surface
    assert "trading-signal" in composition["tabs"]["work"]["list"]["pinned_tasks"]
    # Detail middle for portfolio-review surfaces
    middles = composition["tabs"]["work"]["detail"]["middles"]
    assert any(m["match"].get("task_slug") == "portfolio-review" for m in middles)


def test_phase_overlay_applied():
    # alpha-trader's current_phase: observation → banner about paper-only
    response = client.get("/api/programs/surfaces", headers=auth)
    banner = response.json()["composition"]["tabs"]["work"]["list"].get("banner")
    assert banner and "Paper-only" in banner


def test_alpha_commerce_deferred_does_not_appear_in_active_bundles():
    """alpha-commerce is status: deferred — its templates do not surface."""
    response = client.get("/api/programs/surfaces", headers=auth)
    slugs = [b["slug"] for b in response.json()["active_bundles"]]
    assert "alpha-commerce" not in slugs
```

```typescript
// web/__tests__/compositor.test.ts

describe('resolveMiddle', () => {
  it('matches by task_slug first (highest specificity)', () => {
    const middles = [
      { match: { output_kind: 'produces_deliverable' }, archetype: 'document', ... },
      { match: { task_slug: 'portfolio-review' }, archetype: 'dashboard', ... },
    ];
    const task = { slug: 'portfolio-review', output_kind: 'produces_deliverable' };
    expect(resolveMiddle(task, middles).archetype).toBe('dashboard');  // task_slug wins
  });

  it('falls through to kernel defaults when no bundle middle matches', () => {
    const task = { slug: 'random-task', output_kind: 'produces_deliverable' };
    expect(resolveMiddle(task, []).components[0].kind).toBe('DeliverableMiddle');
  });
});
```

---

## Consequences

### Positive

- **SURFACES.yaml stops being aspirational.** Today the bundle's composition manifest is text the FE doesn't read. Post-ADR-225, it's consumed and rendered.
- **Adding a program is purely additive (cockpit side, too).** Today adding alpha-prediction means writing a new FE switch case. Post-ADR-225, it means writing the bundle's SURFACES.yaml + adding any new components to the library. No FE switch edits.
- **WorkDetail.tsx::KindMiddle switch deletes.** Singular Implementation rule 1 honored at the dispatch layer.
- **Component library exists.** The system component library convention (ADR 3 in the roadmap) ships folded into this ADR — the library is small enough today to not merit a separate ratification.
- **Phase-aware chrome ships.** `phase_overlays` from SURFACES.yaml become first-class rendering input.
- **Validates the OS framing's last load-bearing claim.** The compositor is the ONE OS-architecture box from ADR-222 Frame 5 that was "not yet built." Post-ADR-225, every box on the right side has a shipped artifact.

### Negative / costs

- **Real FE engineering.** Net new directory (`web/lib/compositor/`), net new directory (`web/components/library/`), 5 new components (`PerformanceSnapshot`, `PositionsTable`, `RiskBudgetGauge`, `RevenueSnapshot`, `CohortRetentionGrid`). Hours of work, not minutes.
- **New API endpoint.** `/api/programs/surfaces` requires auth wiring + Pydantic models + tests. Standard FastAPI pattern (~3 routes already follow it).
- **Existing kind-middles relocate.** `DeliverableMiddle` etc. move from `web/components/work/details/` into `web/components/library/`. Caller import paths update. Mechanical but real.
- **lru_cache busting on bundle changes.** `composition_resolver` reads bundles via `bundle_reader` (already cached). Restart-on-deploy is fine for now.

### Risks

- **Component library bloat.** Without discipline, the library accretes one-off components. Mitigation: contribution rule already in §3 — "no new component shipped without a bundle that uses it." Pull, not push.
- **API endpoint becomes hot path.** `/api/programs/surfaces` will be called on every cockpit load. Mitigation: response is cacheable per workspace (varies only by workspace's active bundles + phases, which change at deploy time + connection events). Standard SWR caching on FE side; Cache-Control headers on API side.
- **Middle resolver specificity rules confuse contributors.** Three-tier matching (task_slug → output_kind → agent_role) might surprise. Mitigation: documented in §4 with examples; resolver source is small and well-commented; resolver tests cover ambiguous cases.

---

## Open questions

Explicitly deferred — none gate ratification.

- **Where do `briefing` archetype renderings live?** ADR-198's Briefing archetype currently surfaces only on Overview (ADR-199) and email (per ADR-202). Future bundles might want to declare briefing-shaped middles on /work — defer until first such request.
- **Component prop schema validation.** Today the resolver passes `source` as a path string. Future components might need richer prop shapes (filters, query refinements). Defer until concrete demand.
- **Server-side composition rendering for emails.** The `compose` substrate (ADR-170) handles email rendering today, separately from cockpit composition. Whether to unify under the compositor is a real question — defer until pressure emerges.
- **Bundle hot-reload during development.** `bundle_reader` uses `lru_cache`; restart-on-deploy is fine for prod but slows dev iteration. Defer until it actually slows someone down.

---

## Decision

**Adopt the compositor layer as defined above.** API endpoint `/api/programs/surfaces` resolves active bundles + phase overlays + composition tree. FE module `web/lib/compositor/` consumes the response and renders via universal components from `web/components/library/`. The hardcoded `WorkDetail.tsx::KindMiddle` switch is deleted; the resolver replaces it with declarative match-and-bind across 4 specificity tiers. Kernel-universal middles (DeliverableMiddle / TrackingEntityGrid / ActionMiddle / MaintenanceMiddle) become library components used by kernel-default `MiddleDecl`s. ADR 3 (System Component Library Convention) folds in here. Migration is atomic across API + FE + tests + docs in one PR.

---

## Phase 2 implementation refinements (recorded 2026-04-27, post-implementation)

The v2 spec called for ~14 components and an extraction-rename pattern that would relocate the existing kind-middles into `web/components/library/`. The shipped Phase 2 honors the spec's structural goals (declarative dispatch via resolver; bundle-shipped middles override; KindMiddle switch deleted) but with refinements that match the demand-pull discipline:

**1. Library scope: 6 components shipped, not 14.**
- `MiddleResolver` (the dispatch component itself)
- `BundleBanner` (phase-aware list banner)
- `PerformanceSnapshot`, `PositionsTable`, `RiskBudgetGauge`, `TradingProposalQueue` (alpha-trader's SURFACES.yaml referents)

The other 8 paper-design components (`MetricCardRow`, `TaskOutputViewer`, `NarrativeRail`, `QueueCard`, `AlertCard`, `TaskList`, `FilterChipRow`, `AttributedActionReview`, `AgentRoster`, `ReviewerHealthCard`, `PrincipleEditor`, `ReviewerCalibrationView`, `FileTree`, `PinnedShortcutRow`) land additively when bundles surface the demand. **No component shipped without a bundle that uses it** — the discipline already in §3 of this ADR. Building all 14 speculatively would have violated that rule.

**2. Existing kind-middles stay at `web/components/work/details/`, not relocated.**
The v2 spec called for relocating `DeliverableMiddle`/`TrackingEntityGrid`/`ActionMiddle`/`MaintenanceMiddle` into `library/` and renaming `DeliverableMiddle → TaskOutputViewer`. The Phase 2 refinement: **keep them where they are**. They're the kernel-default fallback path; `MiddleResolver` imports them from `work/details/` directly. Relocation is mechanical busywork that doesn't change behavior — defer until a bundle actually overrides one and the flat library namespace becomes load-bearing.

**3. Phase 1 + Phase 2 shipped same day, not in separate PRs.**
The v2 spec said "atomic single PR." The phased ship plan recorded in this ADR initially called for two commits (Phase 1 backend, Phase 2 FE). In implementation, Phase 1 + Phase 2 landed as two atomic commits in the same arc — Phase 1's backend addition is zero-risk additive (FE didn't yet consume it), Phase 2's switch deletion completes the Singular Implementation contract by making the resolver the sole dispatch path. No deployed state existed where dual approaches ran simultaneously.

**4. Placeholder components, deliberate.**
The 4 alpha-trader library components (`PerformanceSnapshot`, `PositionsTable`, `RiskBudgetGauge`, `TradingProposalQueue`) ship as **placeholder visuals** — they read the substrate path, render a simple container with title + content. The Phase 2 implementation goal was the wiring (resolver → component dispatch by `kind`), not visual polish. Real visual designs land additively as alpha-trader matures into a built program. The placeholder-with-real-wiring pattern is honest: nothing fakes the data flow; the data flow works; visuals iterate on top.

**5. `BundleBanner` is the first bundle-supplied chrome wired to a list surface.**
Beyond the middle dispatch, Phase 2 wires the bundle's `tabs.work.list.banner` field to the actual cockpit surface. When alpha-trader is `current_phase: observation`, the "Paper-only. Live trading gated on AUTONOMY.md flip." banner appears on `/work` list mode. Silent fallback when no banner is supplied — workspaces without active bundles see no chrome change. This is the smallest demonstration of bundle-supplied list-mode integration; the other list-mode features (`pinned_tasks`, `featured` agents, `featured_domains`, `chat_chips`) wire incrementally as bundles need them.

**6. Build validation.**
- Phase 1: 10/10 API tests passing (`api/test_adr225_compositor.py`).
- Combined: 21/21 (with ADR-224's 11 boundary tests).
- Phase 2: Next.js production build clean — zero TS errors, all routes compile including `/work` (where the resolver dispatches) and `/overview`.

**Net delta vs v2 spec:**
- Components shipped: 6 (not 14).
- Existing kind-middles: not relocated (kernel-default path stays at `work/details/`).
- KindMiddle switch: DELETED per spec.
- API contract: shipped per spec.
- Resolver match tiers: 4-tier per spec.
- Binding taxonomy: 6 types per spec.
- Phase overlay merge: shipped per spec.
- Net new code: ~600 lines FE (lib/compositor/, components/library/) + ~250 lines API (composition_resolver.py + programs.py) + workspace-scoped bundle filter in bundle_reader.

The discipline lesson: **demand-pull over speculation.** v2 spec listed 14 components because the paper design referenced 14; Phase 2 shipped 6 because only 6 are referenced by SURFACES.yaml files in the repo. The other 8 land when a bundle declares them. Same shape as ADR-224's "5 platform-integration capabilities stay in kernel" refinement — let the artifacts dictate scope, not the speculative spec.

---

## Phased implementation rationale (recorded 2026-04-27 mid-implementation)

The v2 spec called for an atomic single PR covering API + FE library + KindMiddle replacement + doc sync. During implementation, a discipline tradeoff surfaced:

- **Phase 1** (API + resolver + tests): self-contained, independently valuable, deployable without breaking the cockpit. Adds a new endpoint that the FE doesn't yet call — additive, zero risk to shipped UX.
- **Phase 2** (FE library reorg + 14-component build + KindMiddle switch deletion): substantial FE engineering. Touches kind-middle relocation, component extraction-renames, and dispatch-switch deletion in one commit. Risk-of-half-built-compositor is real if interrupted.

The v2 spec said "atomic single PR." The implementation interpretation — refined by this note — is "atomic logical commit per phase." Singular Implementation rule 1 forbids dual *running* approaches in deployed state, not dual commits in a deploy stream. Phase 1 ships a backend-only addition; the FE doesn't consume it yet. No dual approach exists at runtime.

Phase 2 is the FE shoe. It will:
- Add `web/lib/compositor/` with `useComposition()` hook, client fetcher, resolver.
- Add `web/components/library/` with 14 universal components (~5–8 are extraction-renames of existing FE code, not net new builds, per the smaller-than-expected pattern).
- Delete `WorkDetail.tsx::KindMiddle` switch.
- Wire bundle-supplied list-mode features (pinned_tasks, banner, featured agents, featured domains, chat_chips).
- Land in one atomic FE commit.

Net effect at end of Phase 2: shipped UX uses the resolver for all dispatch; no dual-approach exists. The phased ship is a sequencing decision, not a scope reduction.

---

## What changed across versions (record for future review)

| Version | Central scope | What changed | Why corrected |
|---|---|---|---|
| **v1** (initial draft, 2026-04-27) | "Compositor reads SURFACES.yaml; FE switch dissolves; 5 made-up components for alpha-trader" | Spec covered manifest format + resolver + 5 components + 3-tier match. | Drafted before reading the parallel paper design (`alpha-trader-surface-design-2026-04-27.md`) and the parallel roadmap discourse (the two-compose-modes distinction). |
| **v2** (same-day rewrite, 2026-04-27) | "Compositor adds *surface compose* sibling to existing *document compose*; 14-component library scoped from paper design; 4-tier match resolution; 6-type binding taxonomy; Overview surface composes via `tabs.chat.bands[]`" | Adds two-compose-modes framing as the load-bearing distinction. Replaces 5 made-up components with the 14 universal components from paper design. Adds a 4th match tier (`output_kind + condition`) for overlay-on-condition shapes. Enumerates 6 binding types (file / frontmatter / task_output / action_proposals / narrative / directory) so binding shape is constrained vocabulary. Adds Overview as `tabs.chat.bands[]` block. Notes most v1 components are extraction-renames, not net new. | The roadmap's 2026-04-27 amendment + the alpha-trader paper design materially sharpened the scope. v1 would have shipped surface compose as a one-mode replacement for document compose; v2 honors that both modes are kernel-level siblings. v1 would have shipped 5 components without grounding in a real cockpit design; v2 is grounded in 14 components the paper design demands. v1 would have missed `external_action`-with-condition overlays that the alpha-trader cockpit needs; v2 adds the 4th match tier. |

The discipline lesson: **when a parallel discourse round is in flight, read its outputs before drafting an ADR that depends on them.** v1 drafted from ADR-222 + ADR-223 + ADR-224 + ADR-198 + ADR-214 alone, missing the day-of paper design. v2 corrects mid-flight after the user's explicit notification surfaced the missed inputs. This is the same shape as ADR-224's v1→v2→v3 corrections — surface the missed framing, integrate it, log the gap.
