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
