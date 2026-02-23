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

// ADR-073: Sync Health (cross-user)
export interface AdminSyncHealth {
  total_sources: number;
  sources_fresh: number;
  sources_stale: number;
  sources_never_synced: number;
  sources_with_cursor: number;
  by_platform: Record<string, { total: number; fresh: number; stale: number }>;
  users_with_sync: number;
  last_sync_event_at: string | null;
}

// ADR-073: Pipeline Stats
export interface AdminPipelineStats {
  content_total: number;
  content_retained: number;
  content_ephemeral: number;
  content_by_platform: Record<string, number>;
  content_retained_by_reason: Record<string, number>;
  last_heartbeat_at: string | null;
  heartbeats_24h: number;
  deliverables_scheduled_24h: number;
  deliverables_executed_24h: number;
  signals_processed_24h: number;
  signals_processed_7d: number;
  triggers_executed_24h: number;
  triggers_skipped_24h: number;
  triggers_failed_24h: number;
}
