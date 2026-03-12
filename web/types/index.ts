/**
 * YARNNN API Types
 * ADR-005: Unified memory with embeddings
 */

// Source types for memories
// ADR-038: Added user_stated for facts entered via UI/TP
export type SourceType = "manual" | "chat" | "document" | "import" | "bulk" | "user_stated" | "conversation" | "preference";

// Source reference for imported memories (platform provenance)
// ADR-046: Added calendar as a platform
export interface SourceRef {
  platform?: "slack" | "notion" | "gmail" | "calendar";
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

// Knowledge filesystem (ADR-107)
export type KnowledgeContentClass =
  | "digests"
  | "analyses"
  | "briefs"
  | "research"
  | "insights";

export interface KnowledgeFile {
  path: string;
  name: string;
  content_class: KnowledgeContentClass | string;
  summary?: string;
  metadata?: Record<string, unknown>;
  updated_at?: string;
}

export interface KnowledgeFilesResponse {
  files: KnowledgeFile[];
  total: number;
  content_class?: KnowledgeContentClass | null;
  limit: number;
}

export interface KnowledgeFileDetail {
  path: string;
  name: string;
  content_class: KnowledgeContentClass | string;
  content: string;
  summary?: string;
  metadata?: Record<string, unknown>;
  updated_at?: string;
}

export interface KnowledgeFileCreateInput {
  title: string;
  content: string;
  content_class: string;
}

export interface KnowledgeVersion {
  path: string;
  version: number;
  summary?: string;
  metadata?: Record<string, unknown>;
  updated_at?: string;
}

export interface KnowledgeVersionsResponse {
  canonical_path: string;
  versions: KnowledgeVersion[];
  total: number;
}

export interface KnowledgeSummaryResponse {
  total: number;
  classes: Array<{
    content_class: KnowledgeContentClass | string;
    count: number;
  }>;
}

// Onboarding State
export type OnboardingState = "cold_start" | "minimal_context" | "active";

export interface OnboardingStateResponse {
  state: OnboardingState;
  memory_count: number;
  document_count: number;
  has_recent_chat: boolean;
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
  plan: string | null;  // ADR-100: 'pro', 'pro_early_bird', 'pro_yearly'
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
// ADR-029 Phase 2: Added integration_import for Gmail/Slack/Notion data sources
export type DataSourceType = "url" | "document" | "description" | "integration_import";

// Integration import source provider
export type IntegrationProvider = "slack" | "notion" | "gmail" | "calendar";

// ADR-093: Agent Types (7 purpose-first types)
export type AgentType =
  | "digest"        // Regular synthesis of what's happening in a specific place
  | "brief"         // Situation-specific document before a key event
  | "status"        // Regular cross-platform summary for a person or audience
  | "watch"         // Standing-order intelligence on a domain
  | "deep_research" // Bounded investigation into something specific, then done
  | "coordinator"   // Meta-specialist that watches a domain and dispatches other work
  | "custom";       // User-defined intent

// ADR-093: All 7 types are stable — no deprecated tier
export type ActiveAgentType = AgentType;

// ADR-093: all stable
export type AgentTier = "stable";

// ADR-044: Type Classification (two-dimensional)
export type ContextBinding = "platform_bound" | "cross_platform" | "research" | "hybrid";
export type TemporalPattern = "reactive" | "scheduled" | "on_demand" | "emergent";

export interface TypeClassification {
  binding: ContextBinding;
  temporal_pattern: TemporalPattern;
  primary_platform?: "slack" | "gmail" | "notion" | "calendar";
}

// =============================================================================
// ADR-093: Type Configurations (7 purpose-first types)
// =============================================================================

// ADR-104: Only fields consumed by build_type_prompt() are defined here.
// Dead fields removed: DigestConfig.max_items, all BriefConfig, WatchConfig.threshold_notes,
// all DeepResearchConfig, CustomConfig.example_content.

export interface DigestConfig {
  focus?: string;
  reply_threshold?: number;
  reaction_threshold?: number;
}

// BriefConfig — no type_config fields consumed by build_type_prompt().
// Brief type uses schedule.timezone for date computation only.
export type BriefConfig = Record<string, unknown>;

export interface StatusConfig {
  subject?: string;
  audience?: "manager" | "stakeholders" | "team" | "executive";
  detail_level?: "brief" | "standard" | "detailed";
  tone?: "formal" | "conversational";
}

export interface WatchConfig {
  domain?: string;
  signals?: string[];
}

// DeepResearchConfig — no type_config fields consumed by build_type_prompt().
// Deep research uses schedule.timezone for date computation only.
export type DeepResearchConfig = Record<string, unknown>;

export interface CoordinatorConfig {
  domain?: string;
  dispatch_rules?: string[];
}

export interface CustomConfig {
  description?: string;
  structure_notes?: string;
}

// ADR-093: Union type for type_config (7 types + fallback)
export type TypeConfig =
  | DigestConfig
  | BriefConfig
  | StatusConfig
  | WatchConfig
  | DeepResearchConfig
  | CoordinatorConfig
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
// ADR-029: Gmail as full integration platform
export type DestinationPlatform = "slack" | "notion" | "gmail" | "calendar" | "email" | "download";
export type DeliveryStatus = "pending" | "delivering" | "delivered" | "failed";

// Gmail-specific format: send, draft, reply
export type GmailDeliveryFormat = "send" | "draft" | "reply";

export interface Destination {
  platform: DestinationPlatform;
  target?: string;  // Channel ID, page ID, recipient email, or null for download
  format?: string;  // message, thread, page, send, draft, reply, markdown, html
  options?: Record<string, unknown>;
}

// ADR-029: Gmail-specific destination options
export interface GmailDestinationOptions {
  cc?: string;
  subject?: string;
  thread_id?: string;  // For replies
}

// ADR-031: Platform-native agent variants
export type PlatformVariant = "slack_digest" | "email_summary" | "notion_page" | string;

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

// ADR-087/092/101: Agent memory structure
export interface AgentMemory {
  observations?: AgentObservation[];
  goal?: AgentGoal;
  review_log?: AgentReviewLogEntry[];
  created_agents?: Array<{
    date: string;
    title: string;
    agent_id?: string;
    dedup_key?: string;
  }>;
  last_generated_at?: string;
}

// ADR-087: Agent mode (ADR-092: extended with reactive, proactive, coordinator)
export type AgentMode = 'recurring' | 'goal' | 'reactive' | 'proactive' | 'coordinator';

// ADR-087: Scoped chat session
export interface AgentSession {
  id: string;
  created_at: string;
  summary?: string;
  message_count: number;
}

export interface Agent {
  id: string;
  title: string;
  agent_type: AgentType;
  type_config?: TypeConfig;
  // ADR-031: Platform-native variants
  platform_variant?: PlatformVariant;  // platform-native render variant (legacy field)
  // ADR-044: Type classification (binding + temporal pattern)
  type_classification?: TypeClassification;
  project_id?: string;
  project_name?: string;  // For UI display
  recipient_context?: RecipientContext;
  schedule: ScheduleConfig;
  sources: DataSource[];
  status: AgentStatus;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  next_run_at?: string;
  version_count?: number;
  latest_version_status?: VersionStatus;
  // ADR-028: Destination-first agents
  destination?: Destination;
  // ADR-068: Agent origin (ADR-092: coordinator_created added)
  origin?: 'user_configured' | 'coordinator_created';
  // ADR-087: Agent-scoped context
  agent_instructions?: string;
  agent_memory?: AgentMemory;
  mode?: AgentMode;
  // ADR-092: Proactive/coordinator review scheduling
  proactive_next_review_at?: string;
  // Quality metrics (ADR-018: feedback loop)
  quality_score?: number;  // Latest edit_distance_score (0=no edits, 1=full rewrite)
  quality_trend?: QualityTrend;  // "improving" | "stable" | "declining"
  avg_edit_distance?: number;  // Average over last 5 versions
  // Legacy: description still consumed by Research/Hybrid strategies
  description?: string;
}

export interface AgentCreate {
  title: string;
  agent_type?: AgentType;
  type_config?: TypeConfig;
  // ADR-031: Platform-native variants
  platform_variant?: PlatformVariant;
  // ADR-044: Type classification
  type_classification?: TypeClassification;
  project_id?: string;
  recipient_context?: RecipientContext;
  schedule: ScheduleConfig;
  sources?: DataSource[];
  // ADR-028: Destination-first agents
  destination?: Destination;
  // ADR-092: Mode taxonomy
  mode?: AgentMode;
  // Legacy: description still consumed by Research/Hybrid strategies
  description?: string;
}

export interface AgentUpdate {
  title?: string;
  agent_type?: AgentType;
  type_config?: TypeConfig;
  // ADR-031: Platform-native variants
  platform_variant?: PlatformVariant;
  recipient_context?: RecipientContext;
  schedule?: ScheduleConfig;
  sources?: DataSource[];
  status?: AgentStatus;
  // ADR-028: Destination-first agents
  destination?: Destination;
  // ADR-087: Agent-scoped context
  agent_instructions?: string;
  // ADR-092: Mode taxonomy + scheduling
  mode?: AgentMode;
  proactive_next_review_at?: string;
  trigger_config?: Record<string, unknown>;
  // Legacy: description still consumed by Research/Hybrid strategies
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

export interface AgentDetail {
  agent: Agent;
  versions: AgentRun[];
  feedback_summary?: FeedbackSummary;
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
// ADR-025: Skills (Slash Commands)
// =============================================================================

export type SkillTier = "core" | "beta";

export interface Skill {
  name: string;
  description: string;
  command: string;
  tier: SkillTier;
  trigger_patterns: string[];
}

export interface SkillListResponse {
  skills: Skill[];
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
  agent_type: string;
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

// ADR-072: Platform content with retention fields
export interface PlatformContentItem {
  id: string;
  content: string;
  content_type?: string | null;
  resource_id: string;
  resource_name?: string | null;
  source_timestamp?: string | null;
  fetched_at: string;
  retained: boolean;
  retained_reason?: string | null;  // ADR-072: why retained
  retained_at?: string | null;  // ADR-072: when marked retained
  expires_at?: string | null;  // ADR-072: for ephemeral content
  metadata: Record<string, unknown>;
}

export interface PlatformContentResponse {
  items: PlatformContentItem[];
  total_count: number;
  retained_count: number;  // ADR-072: accumulation visibility
  freshest_at?: string | null;
  platform: string;
}

// =============================================================================
// Context Pages: Shared Platform Types
// =============================================================================

export type PlatformProvider = 'slack' | 'gmail' | 'notion' | 'calendar';

export type ApiProvider = "slack" | "notion" | "gmail" | "calendar";

/** Map frontend platform names to backend provider names (identity after provider streamlining) */
export const BACKEND_PROVIDER_MAP: Record<PlatformProvider, string[]> = {
  slack: ['slack'],
  gmail: ['gmail'],
  notion: ['notion'],
  calendar: ['calendar'],
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

export type NumericLimitField = 'slack_channels' | 'gmail_labels' | 'notion_pages' | 'calendars' | 'total_platforms';

export interface TierLimits {
  tier: 'free' | 'pro';
  limits: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendars: number;
    total_platforms: number;
    sync_frequency: '1x_daily' | '2x_daily' | '4x_daily' | 'hourly';
    monthly_messages: number; // -1 for unlimited (ADR-100)
    active_agents: number;
  };
  usage: {
    slack_channels: number;
    gmail_labels: number;
    notion_pages: number;
    calendars: number;
    platforms_connected: number;
    monthly_messages_used: number; // ADR-100
    active_agents: number;
  };
  next_sync?: string | null;
}
