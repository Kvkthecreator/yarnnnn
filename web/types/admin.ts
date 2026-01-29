/**
 * Admin Dashboard Types
 */

// Overview statistics
export interface AdminOverviewStats {
  total_users: number;
  total_projects: number;
  total_memories: number;
  total_documents: number;
  total_sessions: number;
  // Growth metrics (7-day)
  users_7d: number;
  projects_7d: number;
  memories_7d: number;
}

// Memory system statistics
export interface AdminMemoryStats {
  by_source: {
    chat: number;
    document: number;
    manual: number;
    import: number;
  };
  by_scope: {
    user_scoped: number;
    project_scoped: number;
  };
  avg_importance: number;
  total_active: number;
  total_soft_deleted: number;
}

// Document pipeline statistics
export interface AdminDocumentStats {
  by_status: {
    pending: number;
    processing: number;
    completed: number;
    failed: number;
  };
  total_storage_bytes: number;
  total_chunks: number;
  avg_chunks_per_doc: number;
}

// Chat engagement statistics
export interface AdminChatStats {
  total_sessions: number;
  active_sessions: number;
  total_messages: number;
  avg_messages_per_session: number;
  sessions_today: number;
}

// User row in admin users table
export interface AdminUserRow {
  id: string;
  email: string;
  created_at: string;
  project_count: number;
  memory_count: number;
  session_count: number;
  last_activity: string | null;
}
