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
// Middle declarations — ADR-225 §4 4-tier match resolution
// ---------------------------------------------------------------------------

export type Archetype = 'document' | 'dashboard' | 'queue' | 'briefing' | 'stream';

export interface MiddleMatch {
  task_slug?: string;
  output_kind?: string;
  condition?: Record<string, unknown>;
  agent_role?: string;
  agent_class?: string;
}

export interface MiddleDecl {
  match: MiddleMatch;
  archetype: Archetype;
  bindings?: Record<string, Binding>;
  components: ComponentDecl[];
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
// API response
// ---------------------------------------------------------------------------

export interface SurfacesResponse {
  schema_version: 1;
  active_bundles: BundleMetadata[];
  composition: CompositionTree;
}
