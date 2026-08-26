/**
 * YARNNN API Types
 * ADR-005: Unified memory with embeddings
 */

// Source types for memories
// ADR-038: Added user_stated for facts entered via UI/TP
export type SourceType = "manual" | "chat" | "document" | "import" | "bulk" | "user_stated" | "conversation" | "preference";

// Source reference for imported memories (platform provenance)
export interface SourceRef {
  platform?: "slack" | "notion";
  resource_id?: string;
  resource_name?: string;
  job_id?: string;
  block_type?: string;
  metadata?: Record<string, unknown>;
}

// Memory (ADR-005: unified model) - Legacy format for domain memories
export interface Memory {
  id: string;
  content: string;
  tags: string[];
  entities: {
    people?: string[];
    companies?: string[];
    concepts?: string[];
  };
  importance: number;
  source_type: SourceType;
  source_ref?: SourceRef; // Platform provenance for imports
  project_id?: string; // null = user-scoped
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ADR-059: User context entry (key-value pairs in user_memory table)
// ADR-072: Added source_ref and source_type for provenance tracking
export interface UserContextEntry {
  id: string;
  key: string;
  value: string;
  source: string;
  confidence: number;
  source_ref?: string | null;  // ADR-072: FK to source record (agent_run_id, session_id)
  source_type?: string | null;  // ADR-072: type of source (agent_feedback, conversation_extraction, pattern_analysis)
  created_at: string;
  updated_at: string;
}

export interface MemoryCreate {
  content: string;
  tags?: string[];
  importance?: number;
  // ADR-038: Source type for proper categorization
  source_type?: SourceType;
}

export interface MemoryUpdate {
  content?: string;
  tags?: string[];
  importance?: number;
}

export interface BulkImportRequest {
  text: string;
}

export interface BulkImportResponse {
  memories_extracted: number;
  project_id: string;
}

// Workspace Upload (ADR-249: persistent uploads at /workspace/uploads/*.md)
export interface WorkspaceUpload {
  path: string;       // e.g. /workspace/uploads/acme-brief.md
  filename: string;   // original_filename from frontmatter
  word_count: number;
  uploaded_at: string; // YYYY-MM-DD
}

// ADR-331 D5: batch upload response (multi-file + .zip). The single-file
// caller gets a one-element results list — one shape, no parallel path.
export interface UploadResultItem {
  filename: string;
  success: boolean;
  workspace_path?: string | null;
  word_count?: number | null;
  error?: string | null;
}

export interface WorkspaceUploadResponse {
  results: UploadResultItem[];
  succeeded: number;
  failed: number;
}

export interface DocumentDownloadResponse {
  url: string;
  expires_in: number;
}

export interface WorkspaceUploadListResponse {
  uploads: WorkspaceUpload[];
  total: number;
  limit: number;
  offset: number;
}

// ADR-244 (2026-05-01): OnboardingStateResponse deleted — replaced by the
// inline response type on api.workspace.getState() in lib/api/client.ts.
// Workspace lifecycle is the canonical name; the type was tied to the
// "onboarding" framing that died with the modal.

// API Response types
export interface DeleteResponse {
  deleted: boolean;
  id: string;
}

// Subscription (Lemon Squeezy) — ADR-100: 2-tier model
// ADR-396: Type-B subscription — three plan tiers.
// ADR-439: `enterprise` — the sales-led tier where BYOK may be enabled.
export type SubscriptionTier = "free" | "starter" | "pro" | "enterprise";

export interface SubscriptionStatus {
  tier: SubscriptionTier;
  expires_at: string | null;
  customer_id: string | null;
  subscription_id: string | null;
  // ADR-445 Axis ① — the seat state (LIVE). Seat 1 (the owner) is free; each
  // additional human is a priced seat. `seat_billing_active` is true when the
  // workspace has billable seats beyond the owner (a paid team). A solo workspace
  // has billable_seats = 0 (owner is the free seat).
  human_seats: number;          // active human members (owner + members)
  included_seats: number;       // billing baseline: humans covered before the seat fee
  billable_seats: number;       // additional humans beyond the base (the billed seats)
  seat_fee_usd: number;         // billable_seats × additional_seat_usd (the seat-axis total)
  seat_billing_active: boolean; // billable_seats > 0 on a paid, non-exempt tier
  // ADR-445 §12.3a — comped workspace (seats + usage forced $0). The FE shows a
  // "comped" state instead of a bill; the operator's test workspaces are exempt.
  billing_exempt: boolean;
  // 2026-07-29 — the unresolved seat-sync signal. Non-null when a member change
  // did NOT reach the invoice (LS still bills the old count), so the next bill is
  // wrong in a direction the operator cannot otherwise see. Cleared by a later
  // successful sync. Null = healthy.
  seat_sync_issue: SeatSyncIssue | null;
}

/** A seat change that never reached the invoice (see `seat_sync_issue`). */
export interface SeatSyncIssue {
  at: string | null;                 // when the sync failed (ISO)
  intended_action: string;           // 'update_quantity' | 'cancel_at_period_end'
  intended_quantity: number | null;  // the seat count we tried to bill
  human_seats: number | null;        // the roster's headcount at the time
  reason: string | null;             // 'http_404' | 'exception' | …
}

// ADR-439 — BYOK legibility view (never the key). `available` is the tier gate
// (enterprise-only); `enabled`/`provider`/`configured` are the workspace's state.
export interface ByokStatus {
  available: boolean;   // tier_byok_available (enterprise) — may the toggle show at all
  enabled: boolean;     // the workspace's BYOK toggle is ON
  provider: string | null;   // which provider the stored key is for
  configured: boolean;  // a key is stored (shown as "key set" without exposing it)
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
}

/** Result of an in-app plan cancellation (2026-07-22). LS cancellation is
 *  cancel-at-period-END: access runs to `ends_at` and the tier flips on the
 *  `subscription_expired` webhook, so the surface must say WHEN it stops rather
 *  than imply it already has. `ends_at` is null when LS returned no date. */
export interface CancelResponse {
  cancelled: boolean;
  ends_at: string | null;
}

// =============================================================================
// ADR-018: Recurring Agents
// ADR-019: Agent Types System
// =============================================================================

export type AgentStatus = "active" | "paused" | "archived";
// ADR-066: Added "delivered" and "failed" for delivery-first model
// Legacy statuses (staged, reviewing, approved, rejected) kept for backwards compatibility
export type VersionStatus = "generating" | "staged" | "reviewing" | "approved" | "rejected" | "delivered" | "failed";
export type ScheduleFrequency = "daily" | "weekly" | "biweekly" | "monthly" | "custom";
// ADR-029 Phase 2: Added integration_import for Slack/Notion data sources
export type DataSourceType = "url" | "document" | "description" | "integration_import";

// Integration import source provider
export type IntegrationProvider = "slack" | "notion" | "github";

// ADR-109: Scope × Skill × Trigger Framework
export type Scope =
  | "platform"        // Single platform (inferred: 1 provider in sources)
  | "cross_platform"  // Multiple platforms (inferred: 2+ providers)
  | "knowledge"       // Accumulated /knowledge/ filesystem
  | "research"        // Knowledge + WebSearch
  | "autonomous";     // Full primitive set, agent-driven

export type Role =
  // Canonical workforce roster v5 (ADR-176: universal specialist model)
  | "researcher"
  | "analyst"
  | "writer"
  | "tracker"
  | "designer"
  | "executive"
  | "slack_bot"
  | "notion_bot"
  | "github_bot"
  | "thinking_partner"
  // The system agent's judgment rows carry role='freddie'; MessageDispatch
  // keys the freddie-bubble on it (ADR-414 §8 — was 'reviewer-bubble').
  // (Previously absent here, forcing an `as` cast on history reads — ADR-351.)
  | "freddie"
  // Legacy roles kept for backward-compat DB reads (mapped via LEGACY_ROLE_MAP)
  | "competitive_intel"
  | "market_research"
  | "business_dev"
  | "operations"
  | "marketing"
  | "digest"
  | "prepare"
  | "monitor"
  | "research"
  | "synthesize"
  | "act"
  | "custom"
  | "briefer"
  | "scout"
  | "drafter"
  | "planner"
  | "content"
  | "crm";

// =============================================================================
// ADR-109: Role Configurations
// =============================================================================

export interface DigestConfig {
  focus?: string;
  reply_threshold?: number;
  reaction_threshold?: number;
}

// PrepareConfig — no type_config fields consumed by build_skill_prompt().
export type PrepareConfig = Record<string, unknown>;

export interface SynthesizeConfig {
  subject?: string;
  audience?: "manager" | "stakeholders" | "team" | "executive";
  detail_level?: "brief" | "standard" | "detailed";
  tone?: "formal" | "conversational";
}

export interface MonitorConfig {
  domain?: string;
  signals?: string[];
}

// ResearchConfig — no type_config fields consumed by build_skill_prompt().
export type ResearchConfig = Record<string, unknown>;

export interface OrchestrateConfig {
  domain?: string;
  dispatch_rules?: string[];
}

export interface CustomConfig {
  description?: string;
  structure_notes?: string;
}

export type RoleConfig =
  | DigestConfig
  | PrepareConfig
  | SynthesizeConfig
  | MonitorConfig
  | ResearchConfig
  | OrchestrateConfig
  | CustomConfig
  | Record<string, unknown>;

export interface RecipientContext {
  name?: string;
  role?: string;
  priorities?: string[];
  notes?: string;  // ADR-104: not consumed by backend, frontend cleanup deferred
}

export interface ScheduleConfig {
  frequency: ScheduleFrequency;
  day?: string;
  time?: string;
  timezone?: string;
  cron?: string;
}

export interface DataSource {
  type: DataSourceType;
  value?: string;
  label?: string;
  // DB schema fields (from agents.sources JSONB)
  resource_id?: string;
  resource_name?: string;
  // ADR-029 Phase 2: Integration import configuration
  provider?: IntegrationProvider;  // Required when type = "integration_import"
  source?: string;                 // "inbox", "thread:<id>", "query:<query>", channel ID, page ID
}

// Quality trend for feedback loop tracking (ADR-018)
export type QualityTrend = "improving" | "stable" | "declining";

// ADR-028: Destination-first agents
// ADR-029: Destination platforms
export type DestinationPlatform = "slack" | "notion" | "email" | "download";
export type DeliveryStatus = "pending" | "delivering" | "delivered" | "failed";

export interface Destination {
  platform: DestinationPlatform;
  target?: string;  // Channel ID, page ID, or null for download
  format?: string;  // message, thread, page, markdown, html
  options?: Record<string, unknown>;
}

// ADR-087: Agent memory observation
export interface AgentObservation {
  date: string;
  source?: string;
  note: string;
}

// ADR-087: Agent memory goal
export interface AgentGoal {
  description: string;
  status: string;
  milestones?: string[];
}

// ADR-092: Review log entry (proactive/coordinator modes)
export interface AgentReviewLogEntry {
  date: string;
  action: string;  // 'generate' | 'observe' | 'sleep'
  note: string;
  next_review_at?: string;
}

// ADR-087/092/101/117/143: Agent memory structure
export interface AgentMemory {
  goal?: AgentGoal;
  created_agents?: Array<{
    date: string;
    title: string;
    agent_id?: string;
    dedup_key?: string;
  }>;
  last_generated_at?: string;
  // ADR-143/149: Unified feedback + reflections (replaces preferences, observations, supervisor_notes, review_log)
  feedback?: string;           // memory/feedback.md content (rolling 10 entries)
  reflections?: string;        // memory/reflections.md content (rolling 5 entries, ADR-149 rename)
}

// The Agent / AgentRun / AgentSession / Version / OutputManifest type family
// is DELETED (2026-08-26) with the pre-ADR-596 agent model it described:
// ADR-109 Scope x Role x Trigger over the `agents` + `agent_runs` tables.
// Both tables were EMPTY in production and the /api/agents router that served
// them is deleted. A BEING (ADR-596/600) is described by the `beings` entry on
// the lane envelope — see components/agents/AgentsSurface.tsx.

// =============================================================================
// ADR-025: Slash Commands
// =============================================================================

export type CommandTier = "core" | "beta";

export interface SlashCommand {
  name: string;
  description: string;
  command: string;
  tier: CommandTier;
  trigger_patterns: string[];
}

export interface CommandListResponse {
  commands: SlashCommand[];
  total: number;
}

// Multi-destination delivery result
export interface DestinationDeliveryResult {
  destination_index: number;
  platform: string;
  target?: string;
  status: "delivered" | "failed" | "pending";
  external_id?: string;
  external_url?: string;
  error?: string;
}

export interface MultiDestinationResult {
  total_destinations: number;
  succeeded: number;
  failed: number;
  results: DestinationDeliveryResult[];
  all_succeeded: boolean;
}

// =============================================================================
// ADR-034: Emergent Context Domains
// =============================================================================

export interface ContextDomainSummary {
  id: string;
  name: string;
  name_source: "auto" | "user";
  is_default: boolean;
  source_count: number;
  agent_count: number;
  memory_count: number;
  created_at: string;
}

export interface DomainSource {
  platform: string;  // ADR-058: Changed from 'provider' to 'platform'
  resource_id: string;
  resource_name?: string;
}

export interface ContextDomainDetail extends ContextDomainSummary {
  sources: DomainSource[];
  agent_ids: string[];
  updated_at: string;
}

export interface ActiveDomainResponse {
  domain: {
    id: string;
    name: string;
    is_default: boolean;
  } | null;
  source: "agent" | "single_domain" | "ambiguous";
  domain_count?: number;
}

// =============================================================================
// ADR-072: Jobs/Operations Status
// =============================================================================

export interface PlatformSyncStatus {
  platform: string;
  connected: boolean;
  last_synced_at?: string | null;
  next_sync_at?: string | null;
  source_count: number;
  status: "healthy" | "stale" | "pending" | "disconnected" | "unknown";
}

export interface ScheduledAgent {
  id: string;
  title: string;
  role: string;
  next_run_at: string;
  destination_platform?: string | null;
}

export interface BackgroundJobStatus {
  job_type: string;
  last_run_at?: string | null;
  last_run_status: "success" | "failed" | "never_run" | "unknown";
  last_run_summary?: string | null;
  items_processed: number;
}

export interface JobsStatusResponse {
  platform_sync: PlatformSyncStatus[];
  scheduled_agents: ScheduledAgent[];
  background_jobs: BackgroundJobStatus[];
  tier: string;
  sync_frequency: string;
}

// ADR-153: PlatformContentItem and PlatformContentResponse DELETED — platform_content sunset

// =============================================================================
// Workspace Explorer (ADR-152)
// =============================================================================

export interface WorkspaceTreeNode {
  name: string;
  path: string;
  type: 'file' | 'folder';
  updated_at?: string;
  summary?: string;
  children?: WorkspaceTreeNode[];
  // ADR-209 head-revision attribution — populated by the tree endpoint
  // when head_version_id FK resolves (may be undefined for files that
  // predate ADR-209 Phase 2 or haven't been attributed yet).
  authored_by?: string | null;
  // ADR-422 D3: the backend-supplied lucide icon NAME for a workspace ROOT
  // (from WORKSPACE_ROOTS in workspace_paths.py). Set on root nodes by
  // buildRootNodes so WorkspaceTree renders the kernel-named glyph instead of
  // a hardcoded path-string guess. Undefined on non-root nodes.
  icon_name?: string;
}

/**
 * What a click on a file row/tile/tree-node MEANT — the subset of the mouse
 * event the Files surface reads to tell SELECT from OPEN from ADDITIVE-PICK
 * from RANGE.
 *
 * One declaration, threaded to every file-listing renderer (WorkspaceTree,
 * ContentViewer's tiles + rows), so a new field cannot reach some call sites
 * and not others — the drift that let the multi-select modifier land unevenly.
 *
 * · metaKey / ctrlKey → toggle one member in or out of the selection
 * · shiftKey          → take the RANGE from the anchor to here, in the
 *                       listing's current visual order
 * · detail            → the browser's own click counter; >= 2 is a double-click
 *                       (the OPEN gesture on a fine pointer). We read the
 *                       browser's counter rather than timing clicks ourselves,
 *                       so drag-then-click never scores as an open.
 *
 * The renderers DECIDE NOTHING — they report the intent and the surface applies
 * the grammar, so there is one place the grammar lives.
 */
export interface FileClickIntent {
  metaKey?: boolean;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  detail?: number;
}

export interface WorkspaceFile {
  path: string;
  content?: string;
  summary?: string;
  updated_at?: string;
  content_type?: string;
  content_url?: string;
  metadata?: Record<string, any>;
  /** ADR-406 D2: the head revision this content reflects — hold it as the
   *  editing base and send it back via editFile's expectedHeadVersionId. */
  head_version_id?: string | null;
}

/** ADR-209 Phase 4 + ADR-266 D7: minimal revision metadata surfaced in
 *  the /workspace setup-bundle and the per-card "Updated X by Y" line.
 *  Mirrors api/routes/workspace.py::RevisionSummary. */
export interface WorkspaceRevisionSummary {
  id: string;
  authored_by: string;
  author_identity_uuid: string | null;
  message: string;
  created_at: string;
  parent_version_id: string | null;
}

/** ADR-266 D8: one entry in the bundled /workspace setup response —
 *  file content plus most-recent revision metadata. */
export interface WorkspaceFileWithRevision {
  path: string;
  content: string | null;
  last_revision: WorkspaceRevisionSummary | null;
}

// =============================================================================
// Context Pages: Shared Platform Types
// =============================================================================

export type PlatformProvider = 'slack' | 'notion' | 'github';

export type ApiProvider = "slack" | "notion" | "github";

/** Map frontend platform names to backend provider names (identity after provider streamlining) */
export const BACKEND_PROVIDER_MAP: Record<PlatformProvider, string[]> = {
  slack: ['slack'],
  notion: ['notion'],
  github: ['github'],
};

/** Get the provider to use for API calls (identity mapping) */
export const getApiProvider = (platform: PlatformProvider): ApiProvider => {
  return platform;
};

export interface IntegrationData {
  id: string;
  provider: string;
  status: string;
  workspace_name: string | null;
  created_at: string;
  last_used_at: string | null;
  metadata?: {
    email?: string;
    [key: string]: unknown;
  };
}

export interface SelectedSource {
  id: string;
  type: string;
  name: string;
  last_sync_at: string | null;
}

// ADR-172: Usage-first billing — balance is the single gate
export interface BalanceSummary {
  balance_usd: number;           // effective remaining balance
  spend_usd: number;             // total token spend this month (display only)
  is_subscriber: boolean;        // active Pro subscription
  subscription_plan?: string | null;
  next_refill?: string | null;   // ISO timestamp of next subscription billing
}

/** @deprecated Use BalanceSummary (ADR-172) */
export type TierLimits = BalanceSummary;

// The Recurrence type family is DELETED (2026-08-26). ADR-603 D5 retired
// recurrences on 2026-08-24 (0 declarations in production); these types
// outlived it only as the shape the legacy `agents`-table readers named,
// and those readers are gone. Run receipts live on the Notifications
// Activity ledger.

// Process step types (used by run-status responses)
export interface ProcessStepSummary {
  agent_type: string;
  step: string;
}

export interface ProcessStepOutput {
  step: number;
  step_name: string;
  agent_type: string;
  agent_slug: string;
  content?: string;
  tokens?: { input_tokens: number; output_tokens: number };
}
/** @deprecated Use ProcessStepOutput */
export type PipelineStepOutput = ProcessStepOutput;

export interface ProcessStepsResponse {
  steps: ProcessStepOutput[];
  process_definition?: ProcessStepSummary[];
  type_key?: string;
}
/** @deprecated Use ProcessStepsResponse */
export type PipelineStepsResponse = ProcessStepsResponse;

export interface RunStatus {
  status: 'running' | 'completed' | 'failed' | 'not_found';
  current_step: number;
  total_steps: number;
  completed_steps: Array<{
    step: number;
    step_name: string;
    agent_type: string;
    agent_slug: string;
  }>;
  started_at?: string;
  completed_at?: string;
}

// ADR-250 + ADR-265: Per-invocation execution event row (powers /activity page)
export interface ExecutionEvent {
  id: string | null;
  slug: string;
  mode: string; // judgment | mechanical (ADR-263 / ADR-265 — cost discriminator)
  trigger_type: string;
  status: "success" | "failed" | "skipped";
  error_reason: string | null;
  error_detail: string | null;
  tool_rounds: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cache_read_tokens: number | null;
  cache_create_tokens: number | null;
  cost_usd: number | null;
  duration_ms: number | null;
  created_at: string;
  // Capture-first (migration 192): the principal that caused this invocation
  // (owner user_id | foreign-LLM provider host-id like "chatgpt"/"claude.ai" |
  // agent slug). null for rows predating the migration. Drives the
  // per-principal cost rollup on the Activity surface.
  principal_id: string | null;
}
