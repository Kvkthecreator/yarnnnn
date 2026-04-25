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

// Document (ADR-008: Document Pipeline)
export type DocumentStatus = "pending" | "processing" | "completed" | "failed";

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  storage_path?: string;
  project_id?: string; // null = user-scoped
  processing_status: DocumentStatus;
  processed_at?: string;
  error_message?: string;
  page_count?: number;
  word_count?: number;
  created_at: string;
}

export interface DocumentDetail extends Document {
  chunk_count: number;
  memory_count: number;
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  processing_status: DocumentStatus;
  message: string;
}

export interface DocumentDownloadResponse {
  url: string;
  expires_in: number;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  limit: number;
  offset: number;
}

// Onboarding State (ADR-138: check if user has any agents)
export interface OnboardingStateResponse {
  has_agents: boolean;
}

// API Response types
export interface DeleteResponse {
  deleted: boolean;
  id: string;
}

// Subscription (Lemon Squeezy) — ADR-100: 2-tier model
export type SubscriptionTier = "free" | "pro";

export interface SubscriptionStatus {
  status: SubscriptionTier;
  plan: string | null;  // ADR-172: 'pro', 'pro_yearly'
  expires_at: string | null;
  customer_id: string | null;
  subscription_id: string | null;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalResponse {
  portal_url: string;
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

// ADR-138: Task mode (moved from agents to tasks — mode is temporal behavior of work, not identity)
export type TaskMode = 'recurring' | 'goal' | 'reactive';

// ADR-163: User-facing mode label. The schema preserves three modes
// (recurring | goal | reactive) because the execution layer needs the
// distinction (goal has the revision loop, reactive is dispatch-and-done),
// but the user only ever sees two labels. All task-displaying components
// use this helper, never the raw schema value.
export type TaskModeLabel = 'Recurring' | 'One-time';
/**
 * Derive the user-facing mode label from the task's schedule, not its
 * internal mode. A task with any schedule (daily, weekly, etc.) is
 * "Recurring"; a task with no schedule (or "on-demand") is "One-time".
 * The internal mode (recurring/goal/reactive) drives execution semantics
 * only — users should never see those values.
 */
export function taskModeLabel(schedule: string | undefined | null): TaskModeLabel {
  if (!schedule) return 'One-time';
  const s = schedule.trim().toLowerCase();
  return s && s !== 'on-demand' ? 'Recurring' : 'One-time';
}

// ADR-087: Scoped chat session
export interface AgentSession {
  id: string;
  created_at: string;
  summary?: string;
  message_count: number;
}

// ADR-138: Agent is identity-only. Schedule, sources, destination moved to tasks.
export interface Agent {
  id: string;
  title: string;
  slug?: string;
  scope: Scope;
  role: Role;
  type_config?: RoleConfig;
  status: AgentStatus;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  version_count?: number;
  latest_version_status?: VersionStatus;
  origin?: 'user_configured' | 'system_bootstrap' | 'composer';
  agent_instructions?: string;
  agent_memory?: AgentMemory;
  // mode removed — ADR-138: mode is on tasks, not agents
  quality_score?: number;
  quality_trend?: QualityTrend;
  avg_edit_distance?: number;
  description?: string;
  // SURFACE-ARCHITECTURE v3 + ADR-214: agent class + owned context domain
  // 'reviewer' added by ADR-214 — Reviewer is a synthesized systemic pseudo-agent
  // (no DB row; substrate at /workspace/review/*.md per ADR-194 v2).
  agent_class?: 'specialist' | 'domain-steward' | 'synthesizer' | 'platform-bot' | 'meta-cognitive' | 'reviewer';
  context_domain?: string;  // owned domain key (e.g., "competitors"), null for synthesizers
}

export interface AgentCreate {
  title: string;
  role?: Role;
  description?: string;
  agent_instructions?: string;
}

export interface AgentUpdate {
  title?: string;
  role?: Role;
  status?: AgentStatus;
  agent_instructions?: string;
  description?: string;
}

// ADR-049: Source snapshot for tracking what data was used at generation time
export interface SourceSnapshot {
  platform: string;
  resource_id: string;
  resource_name?: string;
  synced_at: string;
  platform_cursor?: string;
  item_count?: number;
  source_latest_at?: string;
  // ADR-049 evolution: actual items consumed from this source during generation
  items_used?: number;
}


export interface AgentRun {
  id: string;
  agent_id: string;
  version_number: number;
  status: VersionStatus;
  draft_content?: string;
  final_content?: string;
  edit_distance_score?: number;
  edit_categories?: {
    additions?: string[];
    deletions?: string[];
    modifications?: string[];
  };
  feedback_notes?: string;
  created_at: string;
  staged_at?: string;
  approved_at?: string;
  // ADR-028: Delivery tracking
  delivery_status?: DeliveryStatus;
  delivery_external_id?: string;
  delivery_external_url?: string;
  delivered_at?: string;
  delivery_error?: string;
  // ADR-032: Platform-centric draft delivery
  delivery_mode?: 'draft' | 'direct';
  // ADR-049: Source snapshots for freshness tracking
  source_snapshots?: SourceSnapshot[];
  // ADR-030: Source fetch summary
  source_fetch_summary?: {
    sources_total: number;
    sources_succeeded: number;
    sources_failed: number;
    delta_mode_used: boolean;
    time_range_start?: string;
    time_range_end?: string;
  };
  // ADR-101: Execution metadata (tokens, model, provenance)
  metadata?: {
    input_tokens?: number;
    output_tokens?: number;
    model?: string;
    // ADR-049 evolution: context provenance
    platform_content_ids?: string[];
    items_fetched?: number;
    sources_used?: string[];
    strategy?: string;
    // Trigger provenance for runs tab observability (manual vs scheduled vs event)
    trigger_type?: string;
  };
}

// ADR-018: Feedback summary for learned preferences
export interface FeedbackSummary {
  has_feedback: boolean;
  total_runs: number;
  approved_runs: number;
  avg_quality?: number;  // Percentage (0-100)
  learned_preferences: string[];  // Human-readable preferences
}

// ADR-118: Rendered output file reference
export interface RenderedOutput {
  filename: string;
  url: string;
  content_type: string;
  size_bytes: number;
  render_type: string;
  updated_at?: string;
}

export interface AgentDetail {
  agent: Agent;
  versions: AgentRun[];
  feedback_summary?: FeedbackSummary;
  rendered_outputs?: RenderedOutput[];
}

export interface VersionUpdate {
  status?: "reviewing" | "approved" | "rejected";
  final_content?: string;
  feedback_notes?: string;
}

export interface AgentRunResponse {
  success: boolean;
  run_id?: string;
  version_number?: number;
  status?: string;
  message?: string;
}

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
}

export interface WorkspaceFile {
  path: string;
  content?: string;
  summary?: string;
  updated_at?: string;
  content_type?: string;
  content_url?: string;
  metadata?: Record<string, any>;
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

export interface LandscapeResource {
  id: string;
  name: string;
  resource_type: string;
  coverage_state: 'uncovered' | 'partial' | 'covered' | 'stale' | 'excluded';
  last_extracted_at: string | null;
  items_extracted: number;
  metadata: Record<string, unknown>;
  last_error: string | null;
  last_error_at: string | null;
  recommended: boolean;
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

// =============================================================================
// ADR-138: Tasks (work definitions)
// =============================================================================

export type TaskStatus = "active" | "paused" | "completed" | "archived";

export interface Task {
  id: string;
  slug: string;
  title: string;
  status: TaskStatus;
  mode?: TaskMode;             // recurring | goal | reactive
  schedule?: string;           // cron or human-readable cadence
  next_run_at?: string;
  last_run_at?: string;
  created_at: string;
  updated_at: string;
  // Derived from TASK.md (populated by API)
  objective?: {
    deliverable?: string;
    audience?: string;
    purpose?: string;
    format?: string;
  };
  agent_slugs?: string[];      // assigned agents (from TASK.md ## Process)
  delivery?: string;           // delivery channel summary
  type_key?: string;           // task type key (e.g., "track-competitors", "competitive-brief")
  // ADR-166: 4-value enum (was task_class):
  // accumulates_context | produces_deliverable | external_action | system_maintenance
  output_kind?: string;
  context_reads?: string[];    // context domains this task reads from (parsed from TASK.md)
  context_writes?: string[];   // context domains this task writes to (parsed from TASK.md)
  // ADR-158: task-level source selection (parsed from TASK.md **Sources:** field)
  // e.g. { slack: ["C123", "C456"] } or { notion: ["page-id-1"] }
  sources?: Record<string, string[]>;
  essential?: boolean;         // ADR-161: anchor task (e.g., daily-update) — cannot be archived
}

// ADR-178 Phase 6: DELIVERABLE.md as structured quality contract
export interface DeliverableExpectedOutput {
  format?: string;         // e.g. "HTML report", "context files"
  surface?: string;        // surface_type from registry
  sections?: string[];     // declared section kinds
  word_count?: string;     // e.g. "800–1200 words"
  paths?: string;          // context-driven: file paths pattern
}

export interface DeliverableSpec {
  expected_output: DeliverableExpectedOutput | null;
  expected_assets: string[] | null;
  quality_criteria: string[] | null;
  audience: string | null;
  user_preferences: string | null;
  route: 'output-driven' | 'context-driven' | null;
}

// ADR-219 Commit 4: narrative filter-over-substrate response shapes.
// /work list view consumes these to render recent-activity headlines
// sourced from session_messages (the narrative) instead of from
// task.last_run_at timestamps. Tasks with zero narrative entries are
// simply absent from `tasks` — caller falls back gracefully.

export interface NarrativeMaterialEntry {
  summary: string;
  role: string;
  pulse: string;
  created_at: string;
  invocation_id?: string | null;
}

export interface NarrativeCounts {
  material: number;
  routine: number;
  housekeeping: number;
}

export interface NarrativeByTaskSlice {
  task_slug: string;
  last_material: NarrativeMaterialEntry | null;
  counts: NarrativeCounts;
  most_recent_at: string | null;
}

export interface NarrativeByTaskResponse {
  window_hours: number;
  tasks: NarrativeByTaskSlice[];
}

export interface TaskDetail extends Task {
  run_log?: string;            // memory/run_log.md content
  success_criteria?: string[];
  output_spec?: string[];
  // context_reads/context_writes inherited from Task
  // ADR-178 Phase 6: parsed DELIVERABLE.md quality contract
  deliverable_spec?: DeliverableSpec | null;
}

export interface TaskCreate {
  title: string;
  /** ADR-145/206: type_key drives default team + pipeline. Prefer over agent_slug. */
  type_key?: string;
  /** Fallback when no type_key is chosen — primary assigned agent. */
  agent_slug?: string;
  /** ADR-149: task management posture. Omit for default (run-now via chat-first per ADR-205). */
  mode?: "recurring" | "goal" | "reactive";
  /** Free-text context / intent (lands in objective.deliverable by convention). */
  focus?: string;
  objective?: {
    deliverable?: string;
    audience?: string;
    purpose?: string;
    format?: string;
  };
  /** ADR-205: omit for run-now; provide a cadence (daily/weekly/cron) for recurring. */
  schedule?: string;
  delivery?: string;
  /** ADR-158 Phase 2: initial source selection keyed by platform. */
  sources?: Record<string, string[]>;
}

// ADR-170: Section provenance from sys_manifest.json
export interface TaskSectionEntry {
  slug: string;
  title?: string;
  kind?: string;
  produced_at?: string;
  source_files: string[];
}

export interface TaskOutput {
  folder: string;
  date: string;
  status: string;
  content?: string;        // markdown text (API field name)
  html_content?: string;   // composed HTML
  md_content?: string;     // legacy alias for content
  manifest?: OutputManifest;
  // ADR-170: Compose substrate — section provenance
  sys_manifest?: Record<string, unknown>;
  sections?: TaskSectionEntry[];
}

// ADR-145: Task Type Registry
// Process step types (renamed from Pipeline — user-facing term is "process")
export interface ProcessStepSummary {
  agent_type: string;
  step: string;
}
/** @deprecated Use ProcessStepSummary */
export type PipelineStepSummary = ProcessStepSummary;

export interface TaskType {
  type_key: string;
  display_name: string;
  description: string;
  // ADR-166: category dropped. output_kind classifies what shape the task produces.
  output_kind: 'accumulates_context' | 'produces_deliverable' | 'external_action' | 'system_maintenance';
  default_schedule: string;
  // ADR-154 + ADR-206: registry-declared defaults exposed in GET /api/tasks/types response.
  default_mode?: 'recurring' | 'goal' | 'reactive';
  default_title?: string;
  output_format: string;
  export_options: string[];
  pipeline_summary: ProcessStepSummary[];
  context_sources: string[];
  requires_platform: string | null;
}

export interface TaskTypesResponse {
  types: TaskType[];
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

// ADR-119 Phase 4b: Output manifest (used by agent outputs)
export interface OutputManifest {
  folder: string;
  version: number;
  created_at: string;
  status: string;
  files: Array<{
    path: string;
    type: string;
    role: string;
    content_url?: string;
    size_bytes?: number;
  }>;
  sources: string[];
  delivery?: Record<string, unknown>;
}
