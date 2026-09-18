/**
 * Operator console types (ADR-655).
 *
 * Matches backend models in api/routes/admin.py. Keyed on the WORKSPACE,
 * because the workspace is the substrate's binding unit (ADR-373/378).
 *
 * This file previously declared `total_agents`, `agent_count`, `task_count`
 * and a `tasks: TaskExecutionRow[]` breakdown — shapes the backend had already
 * deleted (they read the retired agent model's empty tables). The console's
 * types drifting behind its routes is how a pane renders a confident zero, so
 * every field below has a live writer verified against prod.
 */

// GET /admin/stats
export interface AdminOverviewStats {
  total_workspaces: number;
  total_grants: number;
  total_sessions: number;
  total_messages: number;
  workspaces_7d: number;
  sessions_7d: number;
  /**
   * The engagement funnel over LIVE workspaces (am.2). The first three bands are
   * disjoint and sum to the live workspace count; `ws_authored` is a deeper
   * stage of the same journey and deliberately overlaps `ws_sent_message`
   * (against prod: 11 authored vs 9 who sent a message).
   */
  ws_never_opened_lane: number;
  ws_lane_no_message: number;
  ws_sent_message: number;
  ws_authored: number;
}

/** One engine's share of the month's spend. Derived from what the ledger
 *  recorded — never a hardcoded roster of the engines we believe we run. */
export interface AdminEngineRow {
  model: string;
  runs: number;
  billed_usd: number;
}

// GET /admin/execution-stats
export interface AdminExecutionStats {
  spend_usd_this_month: number;
  daily_spend_today: number;
  daily_spend_ceiling: number;
  last_scheduler_heartbeat: string | null;
  heartbeats_24h: number;
  engines: AdminEngineRow[];
}

// GET /admin/workspaces
export interface AdminWorkspaceRow {
  id: string;
  name: string | null;
  owner_id: string;
  /**
   * A display NAME (metadata full_name, else the email's local part) resolved
   * from auth — not an address, and not a column. Null when it does not
   * resolve: the row then identifies itself by `name` + short id, never by the
   * string "unknown".
   */
  owner_label: string | null;
  created_at: string;
  tier: string;
  /**
   * The GRANTED total — every credit ever banked, never debited. Rendered as
   * "Granted", never as "Balance".
   */
  balance_usd: number;
  /**
   * What the member actually has left, from the `get_effective_balance` RPC —
   * the same figure their own billing pane shows. The console shipped
   * rendering `balance_usd` under a "Balance" header and so read $124.21 where
   * the member's menu said "Free · $17.84 left".
   */
  effective_balance_usd: number;
  grant_count: number;
  /** Lanes ever opened. Zero is the honest "never started". */
  lane_count: number;
  /** Messages ever sent, both roles. A lane with 0 messages is a real state. */
  message_count: number;
  /**
   * Files authored, EXCLUDING the mirrored kernel substrate under `system/`.
   * The raw count is furniture — every workspace carries 17-18 mirrored kernel
   * artifacts, so an untouched workspace and a working one both read ~17.
   */
  authored_file_count: number;
  events_7d: number;
  spend_7d: number;
  last_activity: string | null;
  /** ADR-429 §12.3a — when exempt, the workspace pays nothing. */
  billing_exempt: boolean;
}
