/**
 * Admin Dashboard Types
 *
 * Matches backend models in api/routes/admin.py
 */

// GET /admin/stats
export interface AdminOverviewStats {
  total_users: number;
  total_agents: number;
  total_tasks: number;
  total_sessions: number;
  total_messages: number;
  users_7d: number;
  tasks_7d: number;
  sessions_7d: number;
}

// GET /admin/token-usage
export interface TokenUsageRow {
  date: string;
  caller: string; // "chat" | "task_pipeline" | "other"
  model: string;
  billed_input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  api_calls: number;
  estimated_cost_usd: number;
}

export interface AdminTokenUsage {
  period_days: number;
  total_billed_input_tokens: number;
  total_output_tokens: number;
  total_cache_read_tokens: number;
  total_cache_creation_tokens: number;
  total_api_calls: number;
  total_estimated_cost_usd: number;
  cache_hit_pct: number;
  by_day: TokenUsageRow[];
}

// GET /admin/execution-stats
export interface TaskExecutionRow {
  task_slug: string;
  agent_title: string;
  agent_role: string;
  runs_total: number;
  runs_7d: number;
  avg_input_tokens: number;
  avg_output_tokens: number;
  last_run_at: string | null;
  // ADR-250 Phase 4 — from execution_events
  cost_usd_total: number | null;
  failed_count: number;
  skipped_count: number;
}

export interface AdminExecutionStats {
  total_runs_24h: number;
  total_runs_7d: number;
  total_runs_30d: number;
  spend_usd_this_month: number;
  spend_usd_limit: number;
  daily_spend_today: number;
  daily_spend_ceiling: number;
  last_scheduler_heartbeat: string | null;
  heartbeats_24h: number;
  tasks: TaskExecutionRow[];
}

// GET /admin/users
export interface AdminUserRow {
  id: string;
  email: string;
  created_at: string;
  tier: string;
  agent_count: number;
  task_count: number;
  session_count: number;
  spend_usd: number;
  last_activity: string | null;
}
