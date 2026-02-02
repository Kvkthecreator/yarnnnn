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
export type DataSourceType = "url" | "document" | "description";

// ADR-019: Deliverable Types
export type DeliverableType =
  | "status_report"
  | "stakeholder_update"
  | "research_brief"
  | "meeting_summary"
  | "custom";

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

// Union type for type_config - use Record for flexibility with partial configs
export type TypeConfig =
  | StatusReportConfig
  | StakeholderUpdateConfig
  | ResearchBriefConfig
  | MeetingSummaryConfig
  | CustomConfig
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

export interface DataSource {
  type: DataSourceType;
  value: string;
  label?: string;
}

export interface Deliverable {
  id: string;
  title: string;
  deliverable_type: DeliverableType;
  type_config?: TypeConfig;
  project_id?: string;
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
  feedback_notes?: string;
  created_at: string;
  staged_at?: string;
  approved_at?: string;
}

export interface DeliverableDetail {
  deliverable: Deliverable;
  versions: DeliverableVersion[];
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
