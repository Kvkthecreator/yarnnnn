# Work Compositor Refactor — Implementation Plan

**Status:** Archived 2026-04-27 — execution complete. All 8 commits landed; decisions absorbed into [ADR-225 Phase 3](../../adr/ADR-225-compositor-layer.md), [SURFACE-CONTRACTS.md v2.0](../SURFACE-CONTRACTS.md), and [docs/architecture/compositor.md](../../architecture/compositor.md). Preserved here as the planning trail.

**Scope:** Extend the compositor seam on `/work` from "middle content area only" to "full surface" — chrome, list, and cockpit all flow through the same resolver pattern. Singular implementation: one resolver, one match resolution, one extension surface.

**Decided (operator + assistant, 2026-04-27):**
1. Chrome flows through compositor (observation #3 — yes).
2. List + cockpit flow through compositor (observation #1 — yes, by symmetry).
3. Singular, unified approach. No dual paths, no chrome-vs-content seam disparity.

**Method:** One ratified plan → one execution PR (with sub-commits for reviewability) → ADR amendment + SURFACE-CONTRACTS v2.0 in same PR.

---

## Part 1 — The Pattern

The compositor today has one shape: **a resolver consults bundle-supplied declarations against a matching context, falls through to kernel defaults when no bundle match.** That shape is correct; we're applying it uniformly.

After this refactor, every Work surface element passes through the pattern:

| Element | Today | After |
|---|---|---|
| Detail middle (content area) | MiddleResolver via `tabs.work.detail.middles[]` | Same — already shipped |
| Detail metadata strip (chrome) | Hardcoded per-kind switch in `WorkDetail.tsx` | Resolved via `tabs.work.detail.middles[].chrome.metadata` with kernel default per `output_kind` |
| Detail actions row (chrome) | Hardcoded per-kind switch in `WorkDetail.tsx` | Resolved via `tabs.work.detail.middles[].chrome.actions` with kernel default per `output_kind` |
| List pinned tasks | Not consumed; YAML field present, ignored | Resolved via `tabs.work.list.pinned_tasks` |
| List banner | Not consumed; YAML field present, ignored | Resolved via `tabs.work.list.banner` |
| Cockpit panes | Hardcoded composition in `BriefingStrip` | Resolved via `tabs.work.list.cockpit_panes[]` with kernel default sequence |

**Singular implementation discipline:** The `<MiddleResolver>` name already overfits to "middle." Renaming it would touch ~15 call sites and ADRs. The refactor expands the component's responsibility but keeps its name; any fresh design doc clarifies that "MiddleResolver" is a historical name — the resolver dispatches the full work-detail surface (chrome + middle), not just the middle. ADR-225 amendment ratifies this.

---

## Part 2 — Schema Extensions

All schema additions are additive. Existing `MiddleDecl` shape from ADR-225 stays valid. Existing alpha-trader `SURFACES.yaml` continues to work after the refactor lands; bundles authored without the new fields fall through to kernel defaults.

### 2.1 `MiddleDecl.chrome` — optional chrome override per detail middle

```ts
// web/lib/compositor/types.ts (extended)

export interface MiddleDecl {
  match: MiddleMatch;
  archetype: Archetype;
  bindings?: Record<string, Binding>;
  components: ComponentDecl[];
  chrome?: ChromeDecl;  // NEW — optional chrome override
}

export interface ChromeDecl {
  metadata?: ComponentDecl;  // single component for the metadata strip
  actions?: ComponentDecl[]; // ordered list of action components
}
```

When `chrome` is absent on a matched bundle middle, the resolver uses the kernel-default chrome for the task's `output_kind` (existing four chromes — see Part 3).

When `chrome` is present, both `metadata` and `actions` are optional individually — a bundle may override only the metadata (keep kernel default actions) or vice versa.

### 2.2 `TabListBlock.cockpit_panes` — optional cockpit composition

```ts
export interface TabListBlock {
  // ... existing fields ...
  cockpit_panes?: ComponentDecl[];  // NEW — replaces hardcoded BriefingStrip composition
}
```

When present, replaces the kernel-default cockpit pane sequence (NeedsMePane → SnapshotPane → SinceLastLookPane → IntelligenceCard).

When absent (today's case), kernel defaults render — the BriefingStrip's current behavior is preserved as the kernel-default cockpit composition.

### 2.3 No backend resolver changes

[api/services/composition_resolver.py](api/services/composition_resolver.py) reads YAML, returns dict. Adding `chrome` under `middles[]` and `cockpit_panes` under `list` requires zero resolver code changes — they pass through the existing tab-block merge logic. Multi-bundle merge handling for `cockpit_panes`: append-with-dedup like `middles[]` (first match wins per existing `_merge_list_or_detail_block` rules).

**One backend addition:** `_merge_list_or_detail_block` needs a `cockpit_panes` case alongside `middles` (line ~248-249). Three lines of code.

### 2.4 ADR-225 schema amendment scope

ADR-225 §2 (API contract shape) needs an amendment paragraph documenting:
- `chrome` field on `MiddleDecl`
- `cockpit_panes` field on `TabListBlock`
- The decision principle: "the compositor seam covers the full work surface, not just the content area"

The 4-tier match resolution itself (§4) stays unchanged. The 6-type binding taxonomy (§2) stays unchanged. We're adding two declarative slots to existing tab blocks, not changing the resolver semantics.

---

## Part 3 — Kernel-Default Componentization

The current per-kind metadata strips and actions clusters in [WorkDetail.tsx:139-370](web/components/work/WorkDetail.tsx) need to become **library components** so the resolver can dispatch them as kernel defaults the same way it dispatches bundle middles.

### 3.1 Extracted components

Eight components extracted from inline `WorkDetail.tsx` definitions into `web/components/library/`:

```
web/components/library/
├── kernel-chrome/
│   ├── DeliverableMetadata.tsx        (was inline in WorkDetail.tsx:139)
│   ├── TrackingMetadata.tsx           (was inline at WorkDetail.tsx:187)
│   ├── ActionMetadata.tsx             (was inline at WorkDetail.tsx:242)
│   ├── MaintenanceMetadata.tsx        (was inline at WorkDetail.tsx:282)
│   ├── DeliverableActions.tsx         (was inline at WorkDetail.tsx:309)
│   ├── TrackingActions.tsx            (was inline at WorkDetail.tsx:317)
│   ├── ActionActions.tsx              (was inline at WorkDetail.tsx:325)
│   └── MaintenanceActions.tsx         (was inline at WorkDetail.tsx:368)
```

These components register in `LIBRARY_COMPONENTS` like any bundle component. Their `kind` strings — `KernelDeliverableMetadata`, `KernelDeliverableActions`, etc. — are convention only. The resolver doesn't distinguish kernel from bundle; both are library components dispatched by `kind`.

### 3.2 Kernel-default registry

A new `web/lib/compositor/kernel-defaults.ts` declares the kernel-default chrome per `output_kind`:

```ts
// web/lib/compositor/kernel-defaults.ts

export const KERNEL_DEFAULT_CHROME: Record<string, ChromeDecl> = {
  produces_deliverable: {
    metadata: { kind: 'KernelDeliverableMetadata' },
    actions: [{ kind: 'KernelDeliverableActions' }],
  },
  accumulates_context: {
    metadata: { kind: 'KernelTrackingMetadata' },
    actions: [{ kind: 'KernelTrackingActions' }],
  },
  external_action: {
    metadata: { kind: 'KernelActionMetadata' },
    actions: [{ kind: 'KernelActionActions' }],
  },
  system_maintenance: {
    metadata: { kind: 'KernelMaintenanceMetadata' },
    actions: [],  // intentionally empty; matches today's MaintenanceActions = null
  },
};

export const KERNEL_DEFAULT_COCKPIT_PANES: ComponentDecl[] = [
  { kind: 'KernelNeedsMePane' },
  { kind: 'KernelSnapshotPane' },
  { kind: 'KernelSinceLastLookPane' },
  { kind: 'KernelIntelligenceCard' },
];
```

Singular implementation: this file is the **only** place that knows what kernel defaults look like. Resolver consults it after match resolution returns null for a bundle override.

### 3.3 BriefingStrip dissolution

`web/components/work/briefing/BriefingStrip.tsx` becomes a thin renderer that loops `cockpit_panes` (resolved from composition or from `KERNEL_DEFAULT_COCKPIT_PANES`) and dispatches each through `LIBRARY_COMPONENTS`. The four pane components (NeedsMePane, SnapshotPane, SinceLastLookPane, IntelligenceCard) move to `web/components/library/kernel-cockpit/` and register in the library.

The hardcoded composition in BriefingStrip.tsx (lines 50-74) is **deleted** — singular implementation. The cockpit composition lives in declarations only, kernel default or bundle.

---

## Part 4 — Resolver Extension

The FE resolver gains two new public functions alongside `resolveMiddle`:

### 4.1 `resolveChrome`

```ts
// web/lib/compositor/resolver.ts (extended)

export function resolveChrome(
  ctx: ResolutionContext,
  middles: MiddleDecl[],
): ChromeDecl {
  // Try to find a matching middle with a chrome override.
  const matched = resolveMiddle(ctx, middles);
  if (matched?.chrome) {
    // Bundle middle declares chrome — partial overrides allowed.
    return {
      metadata: matched.chrome.metadata
        ?? KERNEL_DEFAULT_CHROME[ctx.task.output_kind ?? 'produces_deliverable']?.metadata,
      actions: matched.chrome.actions
        ?? KERNEL_DEFAULT_CHROME[ctx.task.output_kind ?? 'produces_deliverable']?.actions,
    };
  }
  // No bundle override — kernel default for the kind.
  return KERNEL_DEFAULT_CHROME[ctx.task.output_kind ?? 'produces_deliverable']
    ?? KERNEL_DEFAULT_CHROME.produces_deliverable;
}
```

### 4.2 `resolveCockpitPanes`

```ts
export function resolveCockpitPanes(
  composition: CompositionTree,
): ComponentDecl[] {
  const declared = composition.tabs?.work?.list?.cockpit_panes;
  return declared && declared.length > 0
    ? declared
    : KERNEL_DEFAULT_COCKPIT_PANES;
}
```

### 4.3 Existing `resolveMiddle` unchanged

The 4-tier match resolution stays exactly as it is. We're adding sibling resolvers, not modifying the existing one.

---

## Part 5 — WorkDetail Refactor

`WorkDetail.tsx` shrinks from ~515 lines to ~150. The kind-switch in lines 425-492 is **deleted** (singular implementation). What remains:

```tsx
// web/components/work/WorkDetail.tsx (after)

export function WorkDetail({ task, agents, refreshKey, ... }: WorkDetailProps) {
  const { data: composition } = useComposition();
  const middles = getDetailMiddles(composition.composition, 'work');

  const chrome = resolveChrome(
    { task: { slug: task.slug, output_kind: task.output_kind ?? null } },
    middles,
  );

  const editPrompt = `Help me edit the task "${task.title}". Ask me what I want to change before making any updates.`;

  // Action handlers passed to chrome action components via context:
  const chromeContext = {
    task,
    agents,
    mutationPending,
    pendingAction,
    actionNotice,
    onRunTask,
    onPauseTask,
    onEdit: () => onOpenChat(editPrompt),
  };

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="shrink-0">
        <SurfaceIdentityHeader
          title={task.title}
          metadata={<ChromeRenderer decl={chrome.metadata} ctx={chromeContext} />}
          actions={<ChromeRenderer decls={chrome.actions} ctx={chromeContext} />}
        />
        {task.output_kind !== 'system_maintenance' && <ObjectiveBlock task={task} />}
      </div>

      <div className="flex-1 overflow-auto min-h-0">
        <MiddleResolver task={task} refreshKey={refreshKey} onSourcesUpdated={onSourcesUpdated} />
        <FeedbackStrip task={task} onOpenChat={onOpenChat} />
      </div>
    </div>
  );
}
```

`<ChromeRenderer>` is a new ~30-line component in `web/components/library/ChromeRenderer.tsx` that mirrors `MiddleResolver`'s component-dispatch pattern: looks up `decl.kind` in `LIBRARY_COMPONENTS`, passes context props.

**Action handler threading:** Today's per-kind action clusters take props like `onPause`, `onFire`, `onEdit`. These need to reach kernel-default action components. Two options:

- **A. React context.** A `WorkDetailActionsContext` provider in WorkDetail wraps the chrome render. Kernel action components consume via `useContext`. Bundle-supplied action components opt in if they need lifecycle actions.
- **B. Render-prop-style chromeContext threading.** The `<ChromeRenderer>` accepts a `ctx` prop and passes it as a prop to every action component.

Plan picks **A (React context)** because it scales better when bundle authors want to write custom action components without learning a prop-threading convention. Kernel components consume the context; bundle components can ignore it or consume specific fields.

`WorkDetailActionsContext` shape:

```ts
interface WorkDetailActionsContextValue {
  task: Task;
  agents: Agent[];
  mutationPending: boolean;
  pendingAction: 'run' | 'pause' | null;
  actionNotice: { kind: 'info' | 'success' | 'error'; text: string } | null;
  onRunTask: (slug: string) => void;
  onPauseTask: (slug: string) => void;
  onEdit: (prompt?: string) => void;
}
```

Lives in `web/components/library/WorkDetailActionsContext.tsx`.

---

## Part 6 — List-Mode Integration

### 6.1 Pinned tasks

`WorkListSurface.tsx` reads `composition.tabs.work.list.pinned_tasks` and pins them at the top of the appropriate group(s). When absent, no pinning. Pure data wiring; ~10 lines of change.

### 6.2 Banner

`WorkListSurface.tsx` reads `composition.tabs.work.list.banner` and renders a `<BundleBanner>` component above the list. `BundleBanner` already exists at [web/components/library/BundleBanner.tsx](web/components/library/BundleBanner.tsx) (per ADR-225 Phase 2 — currently unused on `/work`); wire it in.

### 6.3 Cockpit composition

`page.tsx` (line ~381) currently mounts `BriefingStrip` directly. After refactor, mounts `<CockpitRenderer>` which:

1. Calls `resolveCockpitPanes(composition)`.
2. Loops the declarations, dispatches each through `LIBRARY_COMPONENTS`.

`CockpitRenderer` is ~25 lines in `web/components/library/CockpitRenderer.tsx`. The existing `BriefingStrip` component is **deleted** — singular implementation; the kernel-default cockpit panes registry IS the new BriefingStrip.

### 6.4 The `?agent=` filter behavior preserved

When `?agent=` is active, page.tsx skips mounting `<CockpitRenderer>` (today's behavior — ADR-206 deliberate focus shift). The agent-filter behavior is preserved exactly; we're just changing what's inside the strip when it does mount.

---

## Part 7 — alpha-trader Manifest Updates

After the schema extension lands, alpha-trader's `SURFACES.yaml` becomes the **first concrete consumer** of the new fields. Author the extensions same-PR so the wiring gets validated end-to-end:

```yaml
# docs/programs/alpha-trader/SURFACES.yaml (extended)

tabs:
  work:
    list:
      pinned_tasks: [trading-signal, portfolio-review]  # (existing — now consumed)
      group_default: output_kind                         # (existing)
      filters_default:                                   # (existing)
        output_kind: produces_deliverable
      cockpit_panes:                                     # NEW
        - kind: TradingProposalQueue
          filters: { proposal_type: trading, status: pending }
        - kind: PerformanceSnapshot
          source: /workspace/context/portfolio/_performance.md
        - kind: KernelSinceLastLookPane                  # reuse kernel default for this slot
        - kind: KernelIntelligenceCard

    detail:
      middles:
        - match: { task_slug: portfolio-review }
          archetype: dashboard
          bindings:
            performance: /workspace/context/portfolio/_performance.md
            positions: /workspace/context/portfolio/_positions.md
            risk: /workspace/context/portfolio/_risk_state.md
          components:
            - kind: PerformanceSnapshot
              source: performance
            - kind: PositionsTable
              source: positions
            - kind: RiskBudgetGauge
              source: risk
          chrome:                                        # NEW
            metadata:
              kind: TradingPortfolioMetadata             # NEW component to author
            actions:
              - kind: KernelDeliverableActions           # reuse kernel actions

        - match: { task_slug: trading-signal }
          archetype: queue
          bindings:
            proposals: /action_proposals
          components:
            - kind: TradingProposalQueue
              source: proposals
              filters: { proposal_type: trading, status: pending }
          # No chrome override — falls through to kernel produces_deliverable chrome
```

Bundle authors learn the pattern: chrome is optional; reusing kernel components by `kind` reference is allowed and encouraged. New bundle-specific chrome components ship to the library.

One new bundle-shaped component authored: `TradingPortfolioMetadata` (showing "Last sync: 30s ago · 12 positions" instead of "Last output: 3h ago"). Lives in `web/components/library/`. Registers in `LIBRARY_COMPONENTS`.

---

## Part 8 — Documentation Updates

### 8.1 ADR-225 amendment

ADR-225 (Compositor Layer) gains a Phase 3 amendment section:

> **Phase 3 — Unified Compositor Seam (2026-04-27)**
>
> The Phase 2 implementation landed `<MiddleResolver>` for the detail middle (content area). Phase 3 extends the same resolver pattern to: detail chrome (metadata + actions), list-mode pinned tasks + banner, and cockpit panes. The seam is now uniform: every Work surface element passes through resolver → bundle match → kernel default fallback.
>
> Schema extensions: `MiddleDecl.chrome?: ChromeDecl` (optional chrome override per matched middle); `TabListBlock.cockpit_panes?: ComponentDecl[]` (optional cockpit pane sequence).
>
> Kernel defaults registered in `web/lib/compositor/kernel-defaults.ts` per `output_kind`. Singular implementation: this is the only place kernel chrome shape lives.
>
> Hardcoded BriefingStrip composition deleted; the kernel-default cockpit panes registry is the new source. Hardcoded per-kind metadata + actions clusters in WorkDetail.tsx deleted; the kernel-default chrome registry is the new source.
>
> alpha-trader SURFACES.yaml extended same-commit to validate end-to-end.

### 8.2 SURFACE-CONTRACTS.md v2.0

The flagship rewrite Bucket B-1 lands as part of this PR (no separate discourse needed — the unified-seam decision settles the load-bearing open questions from the prior catch-up CHANGELOG):

- **Part 0 — Composition layer** preamble: every tab's contract describes kernel defaults; bundle overrides extend via the manifest. The contract describes the kernel surface; bundles are appendix-shaped.
- **Work tab contract** rewritten around the unified resolver pattern. Detail mode: chrome + middle both compositor-resolved. List mode: pinned tasks + banner + cockpit panes compositor-resolved.
- **R6 candidate ratified:** "Surfaces never branch on `program_slug`. Specialization happens via composition manifest, never via FE conditionals."
- Reference link to ADR-225 Phase 3 for the four-tier match resolution; one-line summary in the doc; "Source of truth: ADR-225" footer per the prior open question.

### 8.3 Other doc updates

- `docs/architecture/` — possibly add `compositor.md` (the architecture-level doc home open question from prior discourse). Decided in this plan: **yes, add it**, sibling to `authored-substrate.md`. Names the resolver pattern, the binding taxonomy, the kernel-default registry, the singular-implementation discipline. Cross-link from SURFACE-CONTRACTS rather than restate.
- `docs/design/CHANGELOG.md` — entry summarizing the Phase 3 landing.
- `docs/design/_audit-work-2026-04-27.md` — archive (rename to `archive/_audit-work-2026-04-27.md`) since its observations are absorbed into the canonical docs.
- `docs/design/_plan-work-compositor-2026-04-27.md` (this doc) — archive same way.

---

## Part 9 — Execution Order

Reviewable sub-commits in one PR. Each sub-commit lands in a green state (build passes, tests pass).

| # | Commit | Scope | Test gate |
|---|---|---|---|
| 1 | Schema + types extension | `types.ts` + `composition_resolver.py` `_merge_list_or_detail_block` `cockpit_panes` case | Build passes; existing tests pass; new TS types compile |
| 2 | Kernel-default chrome componentization | Extract 8 components from WorkDetail.tsx into `web/components/library/kernel-chrome/`; register in `LIBRARY_COMPONENTS`; add `kernel-defaults.ts` | Build passes; WorkDetail.tsx still uses inline kind switch (next commit replaces it) |
| 3 | `resolveChrome` + `<ChromeRenderer>` + WorkDetail refactor | New resolver functions; `WorkDetailActionsContext`; WorkDetail.tsx kind-switch deleted; chrome flows through resolver | Build passes; manual smoke test all four kinds in detail mode; alpha-trader portfolio-review middle still renders (bundle middle path); kernel chrome renders for non-overridden kinds |
| 4 | Cockpit pane componentization | Extract 4 BriefingStrip panes into `web/components/library/kernel-cockpit/`; register in `LIBRARY_COMPONENTS`; BriefingStrip composition logic moves to `kernel-defaults.ts` | Build passes; cockpit panes still render (kernel default path) |
| 5 | `resolveCockpitPanes` + `<CockpitRenderer>` + page.tsx refactor + BriefingStrip deletion | New resolver function; CockpitRenderer; page.tsx mounts CockpitRenderer instead of BriefingStrip; BriefingStrip.tsx deleted | Build passes; cockpit on /work renders identically to before; `?agent=` filter still hides cockpit |
| 6 | List pinned + banner wiring | `WorkListSurface.tsx` consumes `pinned_tasks` and `banner`; BundleBanner wired in | Build passes; alpha-trader pinned_tasks render at top of relevant groups; observation-phase banner renders |
| 7 | alpha-trader manifest extension + new TradingPortfolioMetadata component | SURFACES.yaml gains `chrome` + `cockpit_panes`; new library component; registers | Build passes; alpha-trader cockpit shows trading-shaped panes; portfolio-review chrome shows trading-portfolio metadata |
| 8 | Doc updates | ADR-225 Phase 3 amendment; SURFACE-CONTRACTS v2.0; new `docs/architecture/compositor.md`; CHANGELOG entry; archive `_audit-work-` and `_plan-work-` docs | All grep gates pass (no references to deleted BriefingStrip path; no live references to old kind-switch pattern) |

**Total estimated diff:** ~600 lines added, ~500 lines deleted (mostly WorkDetail.tsx kind-switch, BriefingStrip composition, with new library components offsetting). Net: smaller and more uniform.

---

## Part 10 — Risks + Mitigations

### 10.1 Risk: composition cache means refactor isn't tested against bundle changes

`useComposition()` caches once on mount. During development, manifest changes require a full reload. **Mitigation:** ensure `useComposition` exposes a `reload()` callback for manual refresh in dev. Acceptable cost; not blocking.

### 10.2 Risk: chrome action handler threading is fragile

Action handlers (`onPause`, `onFire`, `onEdit`) need to reach kernel-default chrome action components. The React context approach (Part 5) is conventional; risk is bundle authors writing custom action components that don't read context and silently fail. **Mitigation:** kernel-default action components serve as canonical examples; documentation in `compositor.md` shows the context shape; runtime warning if a bundle action component renders without consuming context (dev-mode only).

### 10.3 Risk: `?agent=` filter logic spans page.tsx and CockpitRenderer

Today's behavior: page.tsx skips mounting BriefingStrip when `?agent=` is set. After refactor, page.tsx skips mounting `<CockpitRenderer>` under the same condition. **Mitigation:** keep the gate in page.tsx (one place, one decision). CockpitRenderer doesn't need to know about the agent filter.

### 10.4 Risk: kernel chrome components reading `task.last_run_at` doesn't match the "operational vs historical" rule

The audit observation #2 noted that metadata strips read `task.last_run_at` directly, which is "operational." After the refactor, kernel chrome components still read this — *the rule is preserved*. The "operational vs historical" boundary becomes contract-explicit in SURFACE-CONTRACTS v2.0 Part 0. **Not a regression; the refactor makes the boundary visible at the doc layer.**

### 10.5 Risk: bundle authors author chrome that diverges from kernel UX patterns

A bundle could author a metadata strip that's structurally different from the kernel pattern (e.g., a multi-line metadata panel instead of a one-line strip). **Mitigation:** document the chrome contract in `compositor.md` — metadata is "one-line operational signal," actions are "in-row buttons." Bundle authors are expected to honor the contract; deviation is a code-review concern, not a hard constraint. The compositor doesn't enforce visual conventions; that's the design system's job.

---

## Part 11 — What This Plan Does NOT Cover

Out of scope deliberately:

- **Inline editor (Thrust 1).** Picked direction (TipTap, directory-registry-tagged inline-editable). Separate plan.
- **Agents page hybrid (Thrust 2).** Substrate-shape vs chat-shape principle. Separate plan, depends on directory-registry tagging schema from Thrust 1.
- **Activation flow UX (Bucket B-2 ACTIVATION-FLOW.md).** Onboarding card + four operating-mode states. Separate doc.
- **Cross-bundle composition.** Multi-program-per-workspace. Out of scope per ADR-225 §8 + ADR-226 §7.
- **Renaming `MiddleResolver`.** Considered, rejected — too many call sites; clarification at doc layer is sufficient.

---

## Awaiting Ratification

This plan is the artifact for stage A → stage B transition. Once ratified, execution proceeds in the order in Part 9. Sub-commits ship under one PR title:

> `feat(adr-225 phase 3): unified compositor seam — chrome, list, cockpit`

with sub-commit subject lines naming each row from the Part 9 table.

**Single ratification ask:** does the plan's shape match the unified-seam decision? Specifically Parts 2 (schema), 3 (kernel-default componentization), and 5 (WorkDetail refactor) — these are the three load-bearing structural choices.
