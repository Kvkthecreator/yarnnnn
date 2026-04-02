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
  caller: string; // "chat" | "task_pipeline" | "composer" | "other"
  model: string;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  cache_creation_tokens: number;
  api_calls: number;
  estimated_cost_usd: number;
}

export interface AdminTokenUsage {
  period_days: number;
  total_input_tokens: number;
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
}

export interface AdminExecutionStats {
  total_runs_24h: number;
  total_runs_7d: number;
  total_runs_30d: number;
  credits_used_this_month: number;
  credits_limit: number;
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
  credits_used: number;
  last_activity: string | null;
}
