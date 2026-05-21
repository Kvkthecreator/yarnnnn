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

export type Archetype = 'document' | 'dashboard' | 'queue' | 'briefing' | 'stream';

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
   * Bundle-supplied cockpit configuration.
   *
   * ADR-243 Phase B: `program_sections` is the primary mechanism.
   * An ordered list of named section components rendered below
   * `CockpitHeader` when the bundle is active. Each section is
   * independently registered in `LIBRARY_COMPONENTS`; the `order`
   * field controls display sequence. Operator (or YARNNN) can reorder
   * or remove sections by editing their workspace SURFACES.yaml.
   *
   * When `program_sections` is present → CockpitRenderer renders
   * CockpitHeader + sections only (no four-face stack).
   * When absent → CockpitRenderer falls through to kernel-default
   * four-face stack.
   *
   * The legacy per-face binding keys (money_truth.live_source,
   * performance.components, tracking.operational_state) are superseded
   * by program_sections for workspaces that declare sections. They
   * remain in the open-schema Record for backward compat with any
   * workspaces that haven't migrated, but new programs should use
   * program_sections instead.
   */
  cockpit?: {
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

export interface Surface {
  slug: string;
  title: string;
  archetype: Archetype;
  substrate_paths: string[];
  icon_key: string;
  default_pinned: boolean;
  route: string;
  summary: string;
  tier: SurfaceTier;
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
