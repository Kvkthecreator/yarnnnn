/**
 * YARNNN API Types
 * ADR-005: Unified memory with embeddings
 */

// Project
export interface Project {
  id: string;
  name: string;
  description?: string;
  workspace_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectWithCounts extends Project {
  memory_count: number;
  ticket_count: number;
}

// Source types for memories
export type SourceType = "manual" | "chat" | "document" | "import" | "bulk";

// Memory (ADR-005: unified model)
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
  project_id?: string; // null = user-scoped
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MemoryCreate {
  content: string;
  tags?: string[];
  importance?: number;
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

// Context Bundle (for viewing full context)
export interface ContextBundle {
  project_id: string;
  user_memories: Memory[];
  project_memories: Memory[];
  documents: Document[];
}

// Work Ticket
export interface WorkTicket {
  id: string;
  task: string;
  agent_type: "research" | "content" | "reporting";
  status: "pending" | "running" | "completed" | "failed";
  parameters?: Record<string, unknown>;
  error_message?: string;
  project_id: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

// ADR-017: Unified Work Model - includes recurring work fields
export interface Work {
  id: string;
  task: string;
  agent_type: "research" | "content" | "reporting";
  project_name: string;
  is_ambient: boolean;
  is_recurring: boolean;
  created_at: string;
  // For recurring work
  frequency: string; // "once", "daily at 9am", etc.
  is_active?: boolean;
  next_run?: string;
  // For one-time work
  status?: "pending" | "running" | "completed" | "failed";
}

export interface WorkListResponse {
  success: boolean;
  work: Work[];
  count: number;
  message: string;
}

export interface WorkUpdateRequest {
  is_active?: boolean;
  task?: string;
  frequency?: string;
}

export interface WorkUpdateResponse {
  success: boolean;
  work: {
    id: string;
    task: string;
    is_recurring: boolean;
    is_active?: boolean;
    frequency: string;
    next_run?: string;
  };
  message: string;
}

export interface WorkDeleteResponse {
  success: boolean;
  message: string;
}

export interface WorkTicketCreate {
  task: string;
  agent_type: "research" | "content" | "reporting";
  parameters?: Record<string, unknown>;
}

// Work Output (ADR-009: structured outputs from agents)
export interface WorkOutput {
  id: string;
  title: string;
  output_type: "finding" | "recommendation" | "insight" | "draft" | "report";
  content?: string; // JSON string containing body
  file_url?: string;
  file_format?: string;
  status: string;
  ticket_id?: string;
  created_at: string;
}

// Work execution response (sync endpoint)
export interface WorkExecutionResponse {
  success: boolean;
  ticket_id: string;
  status: string;
  outputs: WorkOutput[];
  output_count: number;
  execution_time_ms?: number;
  error?: string;
}

// Work ticket with outputs (detail view)
export interface WorkTicketDetail {
  ticket: WorkTicket & { project_name?: string };
  outputs: WorkOutput[];
  output_count: number;
}

// Agent Session
export interface AgentSession {
  id: string;
  agent_type: string;
  messages: Array<{ role: string; content: string }>;
  metadata?: Record<string, unknown>;
  ticket_id?: string;
  project_id?: string;
  created_at: string;
  completed_at?: string;
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

// Subscription (Lemon Squeezy)
export type SubscriptionTier = "free" | "pro";

export interface SubscriptionStatus {
  status: SubscriptionTier;
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
// ADR-018: Recurring Deliverables
// ADR-019: Deliverable Types System
// =============================================================================

export type DeliverableStatus = "active" | "paused" | "archived";
export type VersionStatus = "generating" | "staged" | "reviewing" | "approved" | "rejected";
export type ScheduleFrequency = "daily" | "weekly" | "biweekly" | "monthly" | "custom";
// ADR-029 Phase 2: Added integration_import for Gmail/Slack/Notion data sources
export type DataSourceType = "url" | "document" | "description" | "integration_import";

// Integration import source provider
export type IntegrationProvider = "slack" | "notion" | "gmail";

// Integration import filter configuration
export interface IntegrationImportFilters {
  from?: string;           // Email sender filter
  subject_contains?: string; // Subject line filter
  after?: string;          // Time filter: "7d", "30d", or ISO date
  channel_id?: string;     // Slack channel filter
  page_id?: string;        // Notion page filter
}

// ADR-019: Deliverable Types
// ADR-029 Phase 3: Added email-specific deliverable types
export type DeliverableType =
  // Tier 1 - Stable
  | "status_report"
  | "stakeholder_update"
  | "research_brief"
  | "meeting_summary"
  | "custom"
  // Beta Tier
  | "client_proposal"
  | "performance_self_assessment"
  | "newsletter_section"
  | "changelog"
  | "one_on_one_prep"
  | "board_update"
  // ADR-029 Phase 3: Email-specific types
  | "inbox_summary"
  | "reply_draft"
  | "follow_up_tracker"
  | "thread_summary";

export type DeliverableTier = "stable" | "beta" | "experimental";

// Type-specific section configurations
export interface StatusReportSections {
  summary: boolean;
  accomplishments: boolean;
  blockers: boolean;
  next_steps: boolean;
  metrics: boolean;
}

export interface StakeholderUpdateSections {
  executive_summary: boolean;
  highlights: boolean;
  challenges: boolean;
  metrics: boolean;
  outlook: boolean;
}

export interface ResearchBriefSections {
  key_takeaways: boolean;
  findings: boolean;
  implications: boolean;
  recommendations: boolean;
}

export interface MeetingSummarySections {
  context: boolean;
  discussion: boolean;
  decisions: boolean;
  action_items: boolean;
  followups: boolean;
}

// Type-specific configurations
export interface StatusReportConfig {
  subject: string;
  audience: "manager" | "stakeholders" | "team" | "executive";
  sections: StatusReportSections;
  detail_level: "brief" | "standard" | "detailed";
  tone: "formal" | "conversational";
}

export interface StakeholderUpdateConfig {
  audience_type: "investor" | "board" | "client" | "executive";
  company_or_project: string;
  relationship_context?: string;
  sections: StakeholderUpdateSections;
  formality: "formal" | "professional" | "conversational";
  sensitivity: "public" | "confidential";
}

export interface ResearchBriefConfig {
  focus_area: "competitive" | "market" | "technology" | "industry";
  subjects: string[];
  purpose?: string;
  sections: ResearchBriefSections;
  depth: "scan" | "analysis" | "deep_dive";
}

export interface MeetingSummaryConfig {
  meeting_name: string;
  meeting_type: "team_sync" | "one_on_one" | "standup" | "review" | "planning";
  participants: string[];
  sections: MeetingSummarySections;
  format: "narrative" | "bullet_points" | "structured";
}

export interface CustomConfig {
  description: string;
  structure_notes?: string;
  example_content?: string;
}

// =============================================================================
// Beta Tier Type Configurations
// =============================================================================

export interface ClientProposalSections {
  executive_summary: boolean;
  needs_understanding: boolean;
  approach: boolean;
  deliverables: boolean;
  timeline: boolean;
  investment: boolean;
  social_proof: boolean;
}

export interface ClientProposalConfig {
  client_name: string;
  project_type: "new_engagement" | "expansion" | "renewal";
  service_category: string;
  sections: ClientProposalSections;
  tone: "formal" | "consultative" | "friendly";
  include_pricing: boolean;
}

export interface PerformanceSelfAssessmentSections {
  summary: boolean;
  accomplishments: boolean;
  goals_progress: boolean;
  challenges: boolean;
  development: boolean;
  next_period_goals: boolean;
}

export interface PerformanceSelfAssessmentConfig {
  review_period: "quarterly" | "semi_annual" | "annual";
  role_level: "ic" | "senior_ic" | "lead" | "manager" | "director";
  sections: PerformanceSelfAssessmentSections;
  tone: "humble" | "confident" | "balanced";
  quantify_impact: boolean;
}

export interface NewsletterSectionSections {
  hook: boolean;
  main_content: boolean;
  highlights: boolean;
  cta: boolean;
}

export interface NewsletterSectionConfig {
  newsletter_name: string;
  section_type: "intro" | "main_story" | "roundup" | "outro";
  audience: "customers" | "team" | "investors" | "community";
  sections: NewsletterSectionSections;
  voice: "brand" | "personal" | "editorial";
  length: "short" | "medium" | "long";
}

export interface ChangelogSections {
  highlights: boolean;
  new_features: boolean;
  improvements: boolean;
  bug_fixes: boolean;
  breaking_changes: boolean;
  whats_next: boolean;
}

export interface ChangelogConfig {
  product_name: string;
  release_type: "major" | "minor" | "patch" | "weekly";
  audience: "developers" | "end_users" | "mixed";
  sections: ChangelogSections;
  format: "technical" | "user_friendly" | "marketing";
  include_links: boolean;
}

export interface OneOnOnePrepSections {
  context: boolean;
  topics: boolean;
  recognition: boolean;
  concerns: boolean;
  career: boolean;
  previous_actions: boolean;
}

export interface OneOnOnePrepConfig {
  report_name: string;
  meeting_cadence: "weekly" | "biweekly" | "monthly";
  relationship: "direct_report" | "skip_level" | "mentee";
  sections: OneOnOnePrepSections;
  focus_areas: ("performance" | "growth" | "wellbeing" | "blockers")[];
}

export interface BoardUpdateSections {
  executive_summary: boolean;
  metrics: boolean;
  strategic_progress: boolean;
  challenges: boolean;
  financials: boolean;
  asks: boolean;
  outlook: boolean;
}

export interface BoardUpdateConfig {
  company_name: string;
  stage: "pre_seed" | "seed" | "series_a" | "series_b_plus" | "growth";
  update_type: "quarterly" | "monthly" | "special";
  sections: BoardUpdateSections;
  tone: "optimistic" | "balanced" | "candid";
  include_comparisons: boolean;
}

// =============================================================================
// ADR-029 Phase 3: Email-Specific Deliverable Types
// =============================================================================

export interface InboxSummarySections {
  overview: boolean;
  urgent: boolean;
  action_required: boolean;
  fyi_items: boolean;
  threads_to_close: boolean;
}

export interface InboxSummaryConfig {
  summary_period: "daily" | "weekly";
  inbox_scope: "all" | "unread" | "flagged";
  sections: InboxSummarySections;
  prioritization: "by_sender" | "by_urgency" | "chronological";
  include_thread_context: boolean;
}

export interface ReplyDraftSections {
  acknowledgment: boolean;
  response_body: boolean;
  next_steps: boolean;
  closing: boolean;
}

export interface ReplyDraftConfig {
  thread_id: string;
  tone: "formal" | "professional" | "friendly" | "brief";
  sections: ReplyDraftSections;
  include_original_quotes: boolean;
  suggested_actions?: string[];  // User hints for what to include
}

export interface FollowUpTrackerSections {
  overdue: boolean;
  due_soon: boolean;
  waiting_on_others: boolean;
  commitments_made: boolean;
}

export interface FollowUpTrackerConfig {
  tracking_period: "7d" | "14d" | "30d";
  sections: FollowUpTrackerSections;
  include_thread_links: boolean;
  prioritize_by: "age" | "sender_importance" | "subject";
}

export interface ThreadSummarySections {
  participants: boolean;
  timeline: boolean;
  key_points: boolean;
  decisions: boolean;
  open_questions: boolean;
}

export interface ThreadSummaryConfig {
  thread_id: string;
  sections: ThreadSummarySections;
  detail_level: "brief" | "detailed";
  highlight_action_items: boolean;
}

// Union type for type_config - use Record for flexibility with partial configs
export type TypeConfig =
  // Tier 1 - Stable
  | StatusReportConfig
  | StakeholderUpdateConfig
  | ResearchBriefConfig
  | MeetingSummaryConfig
  | CustomConfig
  // Beta Tier
  | ClientProposalConfig
  | PerformanceSelfAssessmentConfig
  | NewsletterSectionConfig
  | ChangelogConfig
  | OneOnOnePrepConfig
  | BoardUpdateConfig
  // ADR-029 Phase 3: Email-specific
  | InboxSummaryConfig
  | ReplyDraftConfig
  | FollowUpTrackerConfig
  | ThreadSummaryConfig
  | Record<string, unknown>;

export interface RecipientContext {
  name?: string;
  role?: string;
  priorities?: string[];
  notes?: string;
}

export interface TemplateStructure {
  sections?: string[];
  typical_length?: string;
  tone?: string;
  format_notes?: string;
}

export interface ScheduleConfig {
  frequency: ScheduleFrequency;
  day?: string;
  time?: string;
  timezone?: string;
  cron?: string;
}

// ADR-030: Scope configuration for integration sources
export type ScopeMode = "delta" | "fixed_window";

export interface IntegrationSourceScope {
  mode: ScopeMode;
  fallback_days?: number;  // If no last_run_at, go back this many days
  recency_days?: number;   // For fixed_window mode
  max_items?: number;      // Safety limit
  include_threads?: boolean;  // Slack
  include_sent?: boolean;     // Gmail
  max_depth?: number;         // Notion
}

export interface DataSource {
  type: DataSourceType;
  value: string;
  label?: string;
  // ADR-029 Phase 2: Integration import configuration
  provider?: IntegrationProvider;  // Required when type = "integration_import"
  source?: string;                 // "inbox", "thread:<id>", "query:<query>", channel ID, page ID
  filters?: IntegrationImportFilters;
  // ADR-030: Scope configuration for delta extraction
  scope?: IntegrationSourceScope;
}

// Quality trend for feedback loop tracking (ADR-018)
export type QualityTrend = "improving" | "stable" | "declining";

// ADR-028: Destination-first deliverables
// ADR-029: Gmail as full integration platform
export type DestinationPlatform = "slack" | "notion" | "gmail" | "email" | "download";
export type GovernanceLevel = "manual" | "semi_auto" | "full_auto";
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

export interface Deliverable {
  id: string;
  title: string;
  deliverable_type: DeliverableType;
  type_config?: TypeConfig;
  project_id?: string;
  project_name?: string;  // For UI display
  recipient_context?: RecipientContext;
  schedule: ScheduleConfig;
  sources: DataSource[];
  status: DeliverableStatus;
  created_at: string;
  updated_at: string;
  last_run_at?: string;
  next_run_at?: string;
  version_count?: number;
  latest_version_status?: VersionStatus;
  // ADR-028: Destination-first deliverables
  destination?: Destination;
  governance: GovernanceLevel;
  // Quality metrics (ADR-018: feedback loop)
  quality_score?: number;  // Latest edit_distance_score (0=no edits, 1=full rewrite)
  quality_trend?: QualityTrend;  // "improving" | "stable" | "declining"
  avg_edit_distance?: number;  // Average over last 5 versions
  // Legacy fields (for backwards compatibility)
  description?: string;
  template_structure?: TemplateStructure;
}

export interface DeliverableCreate {
  title: string;
  deliverable_type?: DeliverableType;
  type_config?: TypeConfig;
  project_id?: string;
  recipient_context?: RecipientContext;
  schedule: ScheduleConfig;
  sources?: DataSource[];
  // ADR-028: Destination-first deliverables
  destination?: Destination;
  governance?: GovernanceLevel;
  // Legacy fields
  description?: string;
  template_structure?: TemplateStructure;
}

export interface DeliverableUpdate {
  title?: string;
  deliverable_type?: DeliverableType;
  type_config?: TypeConfig;
  recipient_context?: RecipientContext;
  schedule?: ScheduleConfig;
  sources?: DataSource[];
  status?: DeliverableStatus;
  // ADR-028: Destination-first deliverables
  destination?: Destination;
  governance?: GovernanceLevel;
  // Legacy fields
  description?: string;
  template_structure?: TemplateStructure;
}

export interface DeliverableVersion {
  id: string;
  deliverable_id: string;
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
}

// ADR-018: Feedback summary for learned preferences
export interface FeedbackSummary {
  has_feedback: boolean;
  total_versions: number;
  approved_versions: number;
  avg_quality?: number;  // Percentage (0-100)
  learned_preferences: string[];  // Human-readable preferences
}

export interface DeliverableDetail {
  deliverable: Deliverable;
  versions: DeliverableVersion[];
  feedback_summary?: FeedbackSummary;
}

export interface VersionUpdate {
  status?: "reviewing" | "approved" | "rejected";
  final_content?: string;
  feedback_notes?: string;
}

export interface DeliverableRunResponse {
  success: boolean;
  version_id?: string;
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
