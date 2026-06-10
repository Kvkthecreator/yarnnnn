/**
 * Compositor types — ADR-225.
 *
 * TS shape for the /api/programs/surfaces response. Mirrors the
 * Pydantic-equivalent shape returned by services.composition_resolver.
 */

export interface BundleMetadata {
  slug: string;
  title: string;
  tagline?: string;
  current_phase?: string | null;
  current_phase_label?: string | null;
  phases: Array<{ key: string; label: string; description?: string }>;
}

// ---------------------------------------------------------------------------
// Binding taxonomy — 6 types per ADR-225 §2
// ---------------------------------------------------------------------------

export type Binding =
  | { type: 'file'; path: string; paths?: string[]; filter?: Record<string, unknown> }
  | { type: 'frontmatter'; path: string; fields?: string[] }
  | { type: 'task_output'; task_slug: string; selector?: 'latest' | string }
  | { type: 'action_proposals'; filter?: Record<string, unknown> }
  | { type: 'narrative'; filter?: Record<string, unknown> }
  | { type: 'directory'; path: string };

// ---------------------------------------------------------------------------
// Component declarations
// ---------------------------------------------------------------------------

export interface ComponentDecl {
  kind: string;
  source?: string; // key into MiddleDecl.bindings
  binding?: Binding; // inline binding (for components in bands[] without a bindings dict)
  filters?: Record<string, unknown>;
  attribution_schema?: string[];
  default_collapsed?: boolean;
}

// ---------------------------------------------------------------------------
// Middle declarations — ADR-225 §4 + Phase I (slug-only match resolution)
// ---------------------------------------------------------------------------

/**
 * Archetype enum — mirrors `api/services/kernel_surfaces.py::ARCHETYPES`.
 *
 * ADR-198 originally named five (document/dashboard/queue/briefing/stream).
 * ADR-297 D1 added two content shapes (browser/roster) and ADR-297 D11
 * added three structural roles (input/navigator/chrome) for chrome
 * surfaces under the Universal Surface Application axiom. ADR-331 D1 added
 * `sequence` (the guided ordered presentation of substrate — `/setup`).
 *
 * Drift between this union and the Python tuple is a regression-gate
 * failure target — the Phase 1 gate compares both.
 */
export type Archetype =
  | 'document'
  | 'dashboard'
  | 'queue'
  | 'briefing'
  | 'stream'
  | 'browser'
  | 'roster'
  | 'input'
  | 'navigator'
  | 'chrome'
  | 'sequence';

/**
 * LayoutRegion — named compositor mount points (ADR-297 D11).
 *
 * The compositor partitions registered surfaces by `default_region`
 * and mounts each region's surface(s) at the matching JSX slot in
 * ShellCompositor.tsx. Visibility policy (`default_visibility`) is
 * orthogonal — a region can hold an always-mounted, summon-only, or
 * pinned-only surface.
 *
 * Today's regions:
 *   - `main` — primary content area (one surface today; multi-surface
 *     composition is the D10 forward horizon)
 *   - `main-rail` — the dockable command rail docked to the right of
 *     `main`'s window area (ADR-316). A flex sibling of SurfaceViewport
 *     that *reduces* the surface area rather than occluding it. Today:
 *     the chat command rail. On mobile it degrades to a full-screen
 *     overlay (the surface can't be co-visible below 640px).
 *   - `top` — top-of-viewport chrome region
 *   - `bottom-floating` — bottom-floating affordance (today: Dock)
 *   - `bottom-fixed` — bottom-fixed input region (today: ChatComposer)
 *   - `floating-overlay` — modal-style overlay summoned over `main`
 *     (today: Launcher)
 */
export type LayoutRegion =
  | 'main'
  | 'main-rail'
  | 'top'
  | 'bottom-floating'
  | 'bottom-fixed'
  | 'floating-overlay';

/**
 * Surface visibility policy (ADR-297 D11) — when the compositor mounts
 * a surface. Orthogonal to LayoutRegion.
 *
 *   - `always` — mounted whenever any authenticated surface is active
 *   - `summon` — mounted only when explicitly opened (Launcher overlay)
 *   - `pinned-only` — mounted only if pinned by operator (reserved)
 */
export type SurfaceVisibility = 'always' | 'summon' | 'pinned-only';

/**
 * Phase I (post-merge sweep, 2026-05-10): the legacy 4-tier match
 * resolution (task_slug → output_kind+condition → output_kind →
 * agent_role/class) collapses to one tier — task_slug. Per ADR-261 D1's
 * "one execution shape" + ADR-262 D1's slug-templated convention, every
 * recurrence renders through the universal middle (`DeliverableMiddle`)
 * unless a bundle SURFACES.yaml names the recurrence's slug to override.
 *
 * `output_kind`, `condition`, `agent_role`, `agent_class` fields are
 * removed from `MiddleMatch`. Existing bundle SURFACES.yaml entries
 * that target by `task_slug` continue to work unchanged.
 */
export interface MiddleMatch {
  task_slug?: string;
}

export interface MiddleDecl {
  match: MiddleMatch;
  archetype: Archetype;
  bindings?: Record<string, Binding>;
  components: ComponentDecl[];
  /**
   * Optional chrome override. When present, replaces the universal
   * kernel-default chrome for the matched task. Both metadata and
   * actions are independently optional — a bundle may override only
   * one and inherit the kernel default for the other.
   */
  chrome?: ChromeDecl;
}

/**
 * Chrome declaration — metadata strip + actions row in WorkDetail's
 * SurfaceIdentityHeader. Per ADR-225 Phase 3 + Phase I, chrome flows
 * through the compositor seam alongside the middle. The universal
 * kernel default lives in `kernel-defaults.ts`.
 */
export interface ChromeDecl {
  metadata?: ComponentDecl;
  actions?: ComponentDecl[];
}

// ---------------------------------------------------------------------------
// Tab block shapes
// ---------------------------------------------------------------------------

export interface TabListBlock {
  pinned_tasks?: string[];
  pinned_shortcuts?: Array<{ label: string; path: string }>;
  featured?: string[];
  featured_domains?: string[];
  group_default?: string;
  filters_default?: Record<string, unknown>;
  banner?: string;
  components?: ComponentDecl[];
  default_collapsed?: boolean;
  reviewer?: { principles_default?: string };
  /**
   * Bundle-supplied home configuration (key renamed cockpit→home by
   * ADR-312 D2).
   *
   * ADR-243 Phase B: `program_sections` is the primary mechanism — an
   * ordered list of named section components the program declares for
   * the Home's composed slots, rendered below `HomeHeader` (the
   * Constitution band) when the bundle is active. Each section is
   * independently registered in `LIBRARY_COMPONENTS`; the `order` field
   * controls display sequence. Operator (or YARNNN) can reorder or remove
   * sections by editing their workspace SURFACES.yaml.
   *
   * When `program_sections` is present → HomeRenderer renders
   * HomeHeader + the program-declared sections.
   * When absent → HomeRenderer renders the constitution-band CTA
   * (the honest Phase-1 cold-start home, ADR-312 D6) — there is no
   * kernel-default four-face stack (deleted by ADR-273, confirmed
   * deleted by ADR-312).
   *
   * The legacy per-face binding keys (money_truth.live_source,
   * performance.components, tracking.operational_state) remain in the
   * open-schema Record for backward compat; new programs use
   * program_sections.
   */
  home?: {
    program_sections?: Array<{ kind: string; order: number }>;
    [key: string]: unknown;
  };
}

export interface TabDetailBlock {
  middles?: MiddleDecl[];
}

export interface BandDecl {
  id: string;
  compose_mode: 'surface' | 'document' | 'surface_embeds_document';
  components: ComponentDecl[];
  empty_state?: { copy?: string; pointer?: string };
}

export interface TabBlock {
  list?: TabListBlock;
  detail?: TabDetailBlock;
  bands?: BandDecl[];
  reviewer?: { principles_default?: string };
}

export interface CompositionTree {
  tabs: Record<string, TabBlock>;
  chat_chips: string[];
}

// ---------------------------------------------------------------------------
// Atomic Surfaces — ADR-297 D3 (Phase 1: type-level only; consumed in Phase 2)
// ---------------------------------------------------------------------------
//
// `Surface` is the registry entry for an atomic operator-facing surface
// per ADR-297. Mirrors the Python kernel_surfaces.KERNEL_SURFACES entry
// shape plus a `tier` field added by the resolver.
//
// `tier` values:
//   - "kernel" — universal; present in every workspace (Feed, Cadence,
//     Delegation, Mandate, Principles, Identity, Brand, Files, Agents,
//     Program, Queue, Activity)
//   - "program:{slug}" — contributed by an active program bundle's
//     SURFACES.yaml surfaces[] block
//   - "composed" — operator-authored (forward horizon per ADR-297 D10;
//     no entries today)

export type SurfaceTier =
  | 'kernel'
  | `program:${string}`
  | 'composed';

/**
 * The windowed registers (ADR-309 2026-06-01; cleaved by ADR-312 2026-06-02).
 * Mirrors `api/services/kernel_surfaces.py::register`.
 *
 * ADR-312 D5 split ADR-309's single `settings` register, which conflated
 * the OS configuring itself with the operation declaring what it is:
 *
 *   - `intent`       — the operation's authored intent: the constitution
 *                      (Mandate, Principles, Identity). Surfaced first-class
 *                      as the Home's Constitution band, NOT a config drawer.
 *   - `os-config`    — the OS configuring itself (Autonomy, Pace, Connectors,
 *                      Program, Settings). Glanceable in menu-bar vitals.
 *   - `application`  — Applications: open files + live state. Artifacts are
 *                      files opened by Applications via the type→application
 *                      association layer.
 *
 * Absent on chrome surfaces (the window manager's own framing — neither
 * register). FE↔BE coherence is guarded in test_adr297_phase1.py.
 */
export type SurfaceRegister = 'intent' | 'os-config' | 'application';

export interface Surface {
  slug: string;
  /**
   * ADR-309 — which windowed register this surface belongs to. Present on
   * every content surface; absent on chrome.
   */
  register?: SurfaceRegister;
  title: string;
  archetype: Archetype;
  substrate_paths: string[];
  icon_key: string;
  default_pinned: boolean;
  /**
   * URL the launcher navigates to when the operator selects the
   * surface. Empty string ("") for chrome surfaces (top-bar, dock,
   * launcher, chat-composer) — they are not navigable from the
   * launcher; the launcher consumer filters out entries with empty
   * routes.
   */
  route: string;
  summary: string;
  tier: SurfaceTier;
  /**
   * ADR-297 D11 — compositor mount policy. Absent on legacy content
   * surfaces, which the compositor treats as `default_region: 'main'`
   * with `default_visibility: 'summon'` (i.e., the active atomic
   * surface mounts to `main`).
   */
  default_region?: LayoutRegion;
  default_visibility?: SurfaceVisibility;
}

// ---------------------------------------------------------------------------
// API response
// ---------------------------------------------------------------------------

export interface SurfacesResponse {
  schema_version: 1;
  active_bundles: BundleMetadata[];
  composition: CompositionTree;
  /**
   * ADR-297 Phase 1 (additive): flat registry of every atomic surface
   * available in this workspace. The launcher + dock (Phase 2) consume
   * this list as their single source of truth. During the transitional
   * Phase 1 state, `composition` remains the source for the legacy
   * 4-tab nav and `surfaces` is emitted but not yet rendered by the
   * shell. Phase 3 collapses `composition` once every consumer has
   * migrated to `surfaces`.
   */
  surfaces: Surface[];
}
