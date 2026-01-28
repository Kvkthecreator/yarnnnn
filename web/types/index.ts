/**
 * YARNNN API Types
 * Matches backend Pydantic models
 */

// Workspace
export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceCreate {
  name: string;
}

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
  block_count: number;
  ticket_count: number;
}

// Block
export interface Block {
  id: string;
  content: string;
  block_type: "text" | "structured" | "extracted";
  metadata?: Record<string, unknown>;
  project_id: string;
  created_at: string;
  updated_at: string;
}

export interface BlockCreate {
  content: string;
  block_type?: "text" | "structured" | "extracted";
  metadata?: Record<string, unknown>;
}

// Document
export interface Document {
  id: string;
  filename: string;
  file_url: string;
  file_type?: string;
  file_size?: number;
  project_id: string;
  created_at: string;
}

// Context Bundle (for agent execution)
export interface ContextBundle {
  project_id: string;
  blocks: Block[];
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

// Work Output
export interface WorkOutput {
  id: string;
  title: string;
  output_type: "text" | "file";
  content?: string;
  file_url?: string;
  file_format?: string;
  ticket_id: string;
  created_at: string;
}

// Agent Session
export interface AgentSession {
  id: string;
  agent_type: string;
  messages: Array<{ role: string; content: string }>;
  metadata?: Record<string, unknown>;
  ticket_id?: string;
  project_id: string;
  created_at: string;
  completed_at?: string;
}

// API Response types
export interface DeleteResponse {
  deleted: boolean;
  id: string;
}
