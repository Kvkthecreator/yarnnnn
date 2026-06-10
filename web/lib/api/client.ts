/**
 * YARNNN API Client
 * ADR-005: Unified memory with embeddings
 */

import { createClient } from "@/lib/supabase/client";
import type {
  Memory,
  MemoryCreate,
  MemoryUpdate,
  BulkImportRequest,
  WorkspaceUpload,
  WorkspaceUploadResponse,
  WorkspaceUploadListResponse,
  DocumentDownloadResponse,
  DeleteResponse,
  SubscriptionStatus,
  CheckoutResponse,
  PortalResponse,
  Agent,
  AgentCreate,
  AgentUpdate,
  AgentDetail,
  AgentRun,
  VersionUpdate,
  AgentRunResponse,
  // ADR-034: Context Domains
  ContextDomainSummary,
  ContextDomainDetail,
  ActiveDomainResponse,
  // ADR-119 Phase 4b: Output manifest (agent outputs)
  OutputManifest,
  // ADR-231: Recurrences (post-cutover; replaces ADR-138 Tasks naming)
  Recurrence,
  RecurrenceDetail,
  RecurrenceOutput,
  // ADR-231 D5 + ADR-235 D1.c: TaskCreate / TaskType / TaskTypesResponse
  // DELETED. Recurrence creation flows through ManageRecurrence(action='create');
  // the registry catalog is dissolved.
  ProcessStepsResponse,
  RunStatus,
  // ADR-152: Workspace Explorer
  WorkspaceTreeNode,
  WorkspaceFile,
  WorkspaceFileWithRevision,
  // ADR-219 Commit 4: narrative filter-over-substrate
  NarrativeByTaskResponse,
  // ADR-250: per-invocation execution log
  ExecutionEvent,
} from "@/types";
import type {
  AdminOverviewStats,
  AdminTokenUsage,
  AdminExecutionStats,
  AdminUserRow,
} from "@/types/admin";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class APIError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = "APIError";
  }
}

async function getAuthHeaders(): Promise<HeadersInit> {
  const supabase = createClient();

  // Try getSession first, fall back to refresh if needed
  let token: string | undefined;

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (session?.access_token) {
    token = session.access_token;
  } else {
    // Session might not be available, try to refresh
    const { data: refreshData } = await supabase.auth.refreshSession();
    token = refreshData.session?.access_token;
  }

  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  } else {
    console.warn("No auth token available for API request");
  }

  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz) (headers as Record<string, string>)["X-Timezone"] = tz;
  } catch {
    // Non-fatal — server falls back to UTC
  }

  return headers;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers = await getAuthHeaders();

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: "include",
    headers: {
      ...headers,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    throw new APIError(response.status, response.statusText, data);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

export const api = {
  // ADR-108: User context entries (user-scoped, stored in /system/notes.md)
  userMemories: {
    list: () => request<Array<{
      id: string;
      key: string;
      value: string;
      source: string;
      confidence: number;
      created_at: string;
      updated_at: string;
    }>>("/api/memory/user/memories"),
    create: (data: { content: string; entry_type?: string }) =>
      request<{
        id: string;
        key: string;
        value: string;
        source: string;
        confidence: number;
        created_at: string;
        updated_at: string;
      }>("/api/memory/user/memories", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    importBulk: (data: BulkImportRequest) =>
      request<{ memories_extracted: number }>("/api/memory/user/memories/import", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Memory/Entries management
  memories: {
    update: (memoryId: string, data: MemoryUpdate) =>
      request<Memory>(`/api/memory/memories/${memoryId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (memoryId: string) =>
      request<DeleteResponse>(`/api/memory/memories/${memoryId}`, {
        method: "DELETE",
      }),
  },

  // ADR-133: Profile — reads/writes /workspace/IDENTITY.md
  profile: {
    get: () =>
      request<{
        name?: string;
        role?: string;
        company?: string;
        timezone?: string;
        summary?: string;
      }>("/api/memory/profile"),
    update: (data: {
      name?: string;
      role?: string;
      company?: string;
      timezone?: string;
      summary?: string;
    }) =>
      request<{
        name?: string;
        role?: string;
        company?: string;
        timezone?: string;
        summary?: string;
      }>("/api/memory/profile", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
  },

  // (styles API deleted — ADR-133: preferences dissolved into BRAND.md)

  // ADR-244 (2026-05-01): api.onboarding deleted — `getState` migrated into
  // the existing api.workspace namespace below (workspace lifecycle is the
  // canonical name; the OnboardingModal lived for the duration of signup,
  // the surface lives forever). Singular implementation: one canonical
  // state read, one canonical namespace.

  // ADR-133: Brand — reads/writes /workspace/BRAND.md
  brand: {
    get: () =>
      request<{ content: string | null; exists: boolean }>(
        "/api/memory/user/brand"
      ),
    save: (content: string) =>
      request<{ exists: boolean }>(
        "/api/memory/user/brand",
        { method: "POST", body: JSON.stringify({ content }) },
      ),
  },

  // ADR-144: Identity (workspace IDENTITY.md — replaces profile fields)
  identity: {
    get: () =>
      request<{ content: string | null; exists: boolean }>(
        "/api/memory/user/identity"
      ),
    save: (content: string) =>
      request<{ exists: boolean }>(
        "/api/memory/user/identity",
        { method: "POST", body: JSON.stringify({ content }) },
      ),
  },

  // Document endpoints (ADR-249: persistent uploads → /workspace/uploads/*.md)
  documents: {
    // List workspace uploads
    list: () => request<WorkspaceUploadListResponse>("/api/documents"),

    // Persistent upload — returns workspace_path
    upload: async (file: File) => {
      const headers = await getAuthHeaders();
      delete (headers as Record<string, string>)["Content-Type"];
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
        method: "POST",
        credentials: "include",
        headers,
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new APIError(response.status, response.statusText, data);
      }
      return response.json() as Promise<WorkspaceUploadResponse>;
    },

    // Get signed download URL — documentPath is the workspace path e.g. /workspace/uploads/foo.md
    download: (documentPath: string) =>
      request<DocumentDownloadResponse>(`/api/documents${documentPath}/download`),

    // Delete an uploaded file (operator-facing 'Delete'). Trash-semantics,
    // not erasure: the backend archives via lifecycle (ADR-209 retention,
    // reversible) and scopes to operator-owned uploads/ (ADR-320 topology).
    delete: (documentPath: string) =>
      request<{ success: boolean; message: string; archived?: boolean }>(
        `/api/documents${documentPath}`,
        { method: "DELETE" }
      ),

    // ADR-127: Share file to global user_shared/ staging area
    shareFile: (filename: string, content: string) =>
      request<{ success: boolean; path: string; filename: string; message: string }>(
        "/api/share",
        { method: "POST", body: JSON.stringify({ filename, content }) }
      ),
  },

  // Chat endpoints (streaming handled separately in useChat hook)
  chat: {
    // Commit H (2026-05-11): cooperative cancellation of an in-flight
    // Reviewer Loop. Sets chat_sessions.cancellation_requested=true on
    // the operator's active workspace session; the Reviewer's tool-use
    // loop checks the flag at the top of every round and exits early
    // with stand_down on true.
    cancel: () =>
      request<{ ok: boolean; applied: boolean; session_id?: string; reason?: string }>(
        "/api/feed/cancel",
        { method: "POST" },
      ),

    // Ephemeral file attach — ADR-249. Returns {type, file_id?, filename, mime_type?}
    // or {type: "text_block", filename, content} for DOCX.
    attach: async (file: File): Promise<{
      type: "file_id" | "text_block";
      file_id?: string;
      filename: string;
      mime_type?: string;
      content?: string;
    }> => {
      const headers = await getAuthHeaders();
      delete (headers as Record<string, string>)["Content-Type"];
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch(`${API_BASE_URL}/api/feed/attach`, {
        method: "POST",
        credentials: "include",
        headers,
        body: formData,
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new APIError(response.status, response.statusText, data);
      }
      return response.json();
    },

    // Get global chat history
    globalHistory: (limit: number = 1, agentId?: string, taskSlug?: string) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (agentId) params.set('agent_id', agentId);
      if (taskSlug) params.set('task_slug', taskSlug);
      return request<{
        sessions: Array<{
          id: string;
          created_at: string;
          messages: Array<{
            id: string;
            role: string;
            content: string;
            sequence_number: number;
            created_at: string;
            metadata?: {
              tool_history?: Array<{
                type: string;
                name?: string;
                input_summary?: string;
                result_summary?: string;
                content?: string;
              }>;
              tools_used?: string[];
              // ADR-124: Author attribution for meeting room messages
              author_agent_id?: string;
              author_agent_slug?: string;
              author_role?: string;
              // ADR-179: System event cards
              system_card?: string;
              agents_created?: number;
              tasks_created?: string[];
              task_slug?: string;
              task_title?: string;
              output_path?: string;
              run_at?: string;
              // ADR-212: Reviewer verdict cards (role === 'reviewer')
              proposal_id?: string;
              verdict?: string;
              occupant?: string;
              action_type?: string;
              // ADR-219 Commit 2: narrative envelope stamped on every
              // session_messages row by services.narrative.write_narrative_entry.
              // Loader pulls these into TPMessage.narrative; renderer
              // dispatches on `weight` per ADR-219 D5.
              summary?: string;
              pulse?: 'periodic' | 'reactive' | 'addressed' | 'heartbeat';
              // ADR-277: housekeeping retired (no live emission path).
              // Pre-ADR-277 stored rows with weight='housekeeping' coerce
              // to 'routine' on read in ConversationPanel; surfacing the
              // legacy value in the wire type would re-leak it into the FE.
              weight?: 'material' | 'routine';
              invocation_id?: string;
              // ADR-219 Commit 3: narrative_digest rollup card
              rolled_up_count?: number;
              rolled_up_window_hours?: number;
              rolled_up_ids?: string[];
              counts?: { material?: number; routine?: number; housekeeping?: number };
            };
          }>;
        }>;
      }>(`/api/feed/history?${params.toString()}`);
    },

  },

  // Subscription endpoints (Lemon Squeezy)
  // ADR-172: Usage-first billing — Pro subscription for auto-refill
  subscription: {
    getStatus: () => request<SubscriptionStatus>("/api/subscription/status"),

    createCheckout: (billingPeriod: "monthly" | "yearly" = "monthly") =>
      request<CheckoutResponse>("/api/subscription/checkout", {
        method: "POST",
        body: JSON.stringify({ billing_period: billingPeriod, checkout_type: "subscription" }),
      }),

    getPortal: () => request<PortalResponse>("/api/subscription/portal"),
  },

  // Admin endpoints (requires admin access)
  admin: {
    stats: () => request<AdminOverviewStats>("/api/admin/stats"),
    tokenUsage: (days: number = 7) =>
      request<AdminTokenUsage>(`/api/admin/token-usage?days=${days}`),
    executionStats: () => request<AdminExecutionStats>("/api/admin/execution-stats"),
    users: () => request<AdminUserRow[]>("/api/admin/users"),
    exportUsers: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api/admin/export/users`, {
        credentials: "include",
        headers,
      });
      if (!response.ok) {
        throw new APIError(response.status, response.statusText);
      }
      const contentDisposition = response.headers.get("Content-Disposition");
      const filenameMatch = contentDisposition?.match(/filename=(.+)/);
      const filename = filenameMatch ? filenameMatch[1] : "yarnnn_users.xlsx";
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    exportReport: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api/admin/export/report`, {
        credentials: "include",
        headers,
      });
      if (!response.ok) {
        throw new APIError(response.status, response.statusText);
      }
      const contentDisposition = response.headers.get("Content-Disposition");
      const filenameMatch = contentDisposition?.match(/filename=(.+)/);
      const filename = filenameMatch ? filenameMatch[1] : "yarnnn_report.xlsx";
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
  },

  // ADR-018: Agents endpoints
  agents: {
    // List user's agents
    list: (status?: string) => {
      const params = status ? `?status=${status}` : "";
      return request<Agent[]>(`/api/agents${params}`);
    },

    // ADR-251 D5 (reframed 2026-05-08): Reviewer supervision surface —
    // recent runs (liveness), recent autonomous actions (history), and
    // upcoming scheduled fires. Reviewer-specific by intent.
    reviewerActivity: () =>
      request<{
        runs: Array<{
          slug: string;
          status: string;
          created_at: string;
          error_reason: string | null;
          duration_ms: number | null;
        }>;
        actions: Array<{
          id: string;
          // ADR-307: generic queue shape.
          primitive: string;
          family: "capital" | "substrate";
          decision_context: Record<string, unknown> | null;
          status: string;
          approved_at: string | null;
          executed_at: string | null;
          approved_by: string | null;
          source: string | null;
          created_at: string;
        }>;
        schedules: Array<{
          slug: string;
          display_name: string;
          schedule: string | null;
          paused: boolean;
          next_fires_at: string | null;
        }>;
        window_days: number;
      }>("/api/agents/reviewer/activity"),

    // 2026-05-14: Reviewer capability library — operator-facing view of
    // /workspace/operation/specs/. Each spec is a quality contract (schema, sections,
    // anti-patterns) the Reviewer reads when producing recurring outputs.
    // The capability-library analog of Claude Code's skills.md.
    reviewerCapabilities: () =>
      request<{
        specs: Array<{
          slug: string;
          path: string;
          title: string;
          description: string | null;
          sections: string[];
          used_by: string[];
          updated_at: string | null;
          size_bytes: number;
        }>;
      }>("/api/agents/reviewer/capabilities"),

    // Create a new agent
    create: (data: AgentCreate) =>
      request<Agent>("/api/agents", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Get agent with version history
    get: (agentId: string) =>
      request<AgentDetail>(`/api/agents/${agentId}`),

    // Update agent settings
    update: (agentId: string, data: AgentUpdate) =>
      request<Agent>(`/api/agents/${agentId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    // Archive agent
    delete: (agentId: string) =>
      request<{ success: boolean; message: string }>(
        `/api/agents/${agentId}`,
        { method: "DELETE" }
      ),

    // Trigger an ad-hoc run
    run: (agentId: string) =>
      request<AgentRunResponse>(`/api/agents/${agentId}/run`, {
        method: "POST",
      }),

    // List runs for an agent
    listRuns: (agentId: string, limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      return request<AgentRun[]>(
        `/api/agents/${agentId}/runs${params}`
      );
    },

    // Get a specific run
    getRun: (agentId: string, runId: string) =>
      request<AgentRun>(
        `/api/agents/${agentId}/runs/${runId}`
      ),

    // Update version (approve, reject, save edits)
    updateRun: (
      agentId: string,
      runId: string,
      data: VersionUpdate
    ) =>
      request<AgentRun>(
        `/api/agents/${agentId}/runs/${runId}`,
        {
          method: "PATCH",
          body: JSON.stringify(data),
        }
      ),

    // ADR-087 Phase 3: Scoped sessions
    listSessions: (agentId: string, limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      return request<Array<{ id: string; created_at: string; summary?: string; message_count: number }>>(
        `/api/agents/${agentId}/sessions${params}`
      );
    },

    // ADR-119 P4b: Output folder history
    getOutputs: (agentId: string, limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      return request<{ outputs: OutputManifest[]; total: number }>(
        `/api/agents/${agentId}/outputs${params}`
      );
    },
  },

  // ADR-225 + ADR-240: Programs — composition surfaces (ADR-225) +
  // activation lifecycle (ADR-240 FE consumption of ADR-226 backend).
  programs: {
    getSurfaces: () => request<{
      schema_version: 1;
      active_bundles: Array<{
        slug: string;
        title: string;
        tagline?: string;
        current_phase?: string | null;
        current_phase_label?: string | null;
        phases: Array<{ key: string; label: string; description?: string }>;
      }>;
      composition: {
        tabs: Record<string, unknown>;
        chat_chips: string[];
      };
    }>("/api/programs/surfaces"),

    // ADR-240 D1: list bundles the operator may activate at signup.
    listActivatable: () =>
      request<{
        schema_version: number;
        programs: Array<{
          slug: string;
          title: string;
          tagline: string | null;
          status: 'active' | 'deferred';
          deferred: boolean;
          oracle: Record<string, unknown>;
          current_phase: string | null;
        }>;
      }>("/api/programs/activatable"),

    // ADR-240 D1: fork the bundle's reference-workspace into the
    // operator's workspace via the standard authored-substrate path.
    activate: (programSlug: string) =>
      request<{
        schema_version: number;
        activated_program: string;
        files_written: string[];
        files_skipped: string[];
      }>("/api/programs/activate", {
        method: "POST",
        body: JSON.stringify({ program_slug: programSlug }),
      }),

    // ADR-244 D3: soft deactivation — drops the bundle marker on MANDATE.md
    // first heading; operator-authored content stays. Idempotent.
    deactivate: () =>
      request<{
        schema_version: number;
        deactivated: boolean;
        prior_program_slug: string | null;
        reason?: string;
      }>("/api/programs/deactivate", {
        method: "POST",
      }),

    // ADR-312 D9: alpha-trader program data (Home sections). Folded from
    // the legacy /api/cockpit/* namespace into program scope. Auth-scoped
    // only — endpoints derive user_id from session, no path param.
    // ADR-242 + ADR-243 Phase C (live brokerage) + ADR-273 D3 (substrate).
    alphaTrader: {
      moneyTruth: () =>
      request<{
        live: boolean;
        provider?: string;
        paper?: boolean;
        equity?: number;
        cash?: number;
        buying_power?: number;
        day_pnl?: number;
        day_pnl_pct?: number;
        positions_count?: number;
        as_of?: string;
        fallback_reason?: 'no_platform_connection' | 'alpaca_unreachable' | 'no_credentials';
      }>("/api/programs/alpha-trader/money-truth"),

    // ADR-243 Phase C: portfolio equity history for TraderPortfolio chart.
    portfolioHistory: (period = '1M', timeframe = '1D') =>
      request<{
        live: boolean;
        paper?: boolean;
        period?: string;
        timeframe?: string;
        data?: {
          timestamps: number[];
          equity: number[];
          profit_loss: number[];
          profit_loss_pct: number[];
          base_value: number;
        } | null;
        fallback_reason?: string;
      }>(`/api/programs/alpha-trader/portfolio-history?period=${period}&timeframe=${timeframe}`),

    // ADR-243 Phase C: open positions for TraderPositions.
    positions: () =>
      request<{
        live: boolean;
        paper?: boolean;
        positions: Array<{
          symbol: string;
          qty: string;
          side: string;
          market_value: string;
          cost_basis: string;
          avg_entry_price: string;
          current_price: string;
          unrealized_pl: string;
          unrealized_plpc: string;
          change_today: string;
        }>;
        fallback_reason?: string;
      }>("/api/programs/alpha-trader/positions"),

    // ADR-243 Phase C: recent orders for TraderOrders.
    recentOrders: (limit = 10) =>
      request<{
        live: boolean;
        paper?: boolean;
        orders: Array<{
          id: string;
          symbol: string;
          side: string;
          qty: string;
          filled_qty: string;
          type: string;
          time_in_force: string;
          limit_price?: string | null;
          filled_avg_price?: string | null;
          status: string;
          created_at: string;
          filled_at?: string | null;
        }>;
        fallback_reason?: string;
      }>(`/api/programs/alpha-trader/recent-orders?limit=${limit}`),

    // ADR-273 D3: substrate reads — accumulated trading intelligence.
    // Zero LLM, zero platform calls. Each route reads workspace_files
    // directly and parses YAML/markdown frontmatter.
    regime: () =>
      request<{
        live: boolean;
        as_of?: string;
        trend_regime?: 'uptrend' | 'downtrend' | 'chop' | string;
        vix_regime_active?: boolean;
        deactivation_streak_days?: number;
        vixy_close?: number;
        vixy_sma_20?: number;
        spy_close?: number;
        spy_sma_20?: number;
        spy_sma_50?: number;
        data_stale?: boolean;
        fallback_reason?: 'no_substrate' | 'parse_failed' | 'read_failed';
      }>("/api/programs/alpha-trader/regime"),

    indicators: (ticker: string) =>
      request<{
        live: boolean;
        ticker: string;
        as_of?: string;
        price?: number;
        sma_20?: number;
        sma_50?: number;
        sma_200?: number;
        rsi_14?: number;
        atr_14?: number;
        volume_20d_avg?: number;
        fallback_reason?: 'no_substrate' | 'parse_failed' | 'read_failed';
      }>(`/api/programs/alpha-trader/indicators?ticker=${encodeURIComponent(ticker)}`),

    signals: (limit = 10) =>
      request<{
        live: boolean;
        signals: Array<{
          slug: string;
          path: string;
          updated_at?: string;
          ticker?: string;
          direction?: 'long' | 'short' | string;
          expectancy?: number | string;
          status?: string;
          rationale?: string;
          reviewer_decision?: {
            verdict: 'approved' | 'rejected' | 'deferred' | null;
            excerpt: string;
          } | null;
        }>;
        fallback_reason?: 'no_substrate' | 'read_failed';
        evaluator_last_run_at?: string | null;
      }>(`/api/programs/alpha-trader/signals?limit=${limit}`),
    },
  },

  // ADR-327: budget is the KERNEL governance dial (supersedes the retired
  // pace dial). The operation's dollar spend envelope + window-to-date
  // utilization (summed from the execution_events cost ledger) + live queue
  // depth. Budget is the Trigger-dimension dial of the Budget+Autonomy+Identity
  // trifecta. /api/pace → /api/budget.
  budget: () =>
    request<{
      amount_usd: number;
      window: 'monthly' | 'weekly' | 'daily';
      window_spend_usd: number;
      remaining_usd: number;
      per_wake_ceiling_usd: number;
      queue_depth: number;
    }>('/api/budget'),

  // ADR-231: Recurrences endpoints (was `tasks`; renamed in Phase 3.8)
  recurrences: {
    list: (statusOrOpts?: string | { status?: string; include_system?: boolean }) => {
      let qs = "";
      if (typeof statusOrOpts === "string") {
        qs = statusOrOpts ? `?status=${statusOrOpts}` : "";
      } else if (statusOrOpts) {
        const parts: string[] = [];
        if (statusOrOpts.status) parts.push(`status=${encodeURIComponent(statusOrOpts.status)}`);
        if (statusOrOpts.include_system) parts.push(`include_system=true`);
        if (parts.length > 0) qs = `?${parts.join("&")}`;
      }
      return request<Recurrence[]>(`/api/recurrences${qs}`);
    },

    get: (slug: string) =>
      request<RecurrenceDetail>(`/api/recurrences/${slug}`),

    // ADR-215 Phase 4 + ADR-231 D5 + ADR-235 D1.c: frontend no longer POSTs
    // /api/recurrences for creation. Recurrence creation routes through YARNNN
    // via RecurrenceSetupModal → ManageRecurrence(action='create', shape=...,
    // slug=..., body={...}) per ADR-206 CRUD split (ManageTask deleted in
    // ADR-231 Phase 3.7; UpdateContext deleted in ADR-235).

    update: (slug: string, data: { status?: string; schedule?: string; sources?: Record<string, string[]> }) =>
      request<Recurrence>(`/api/recurrences/${slug}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    delete: (slug: string) =>
      request<{ success: boolean; message: string }>(
        `/api/recurrences/${slug}`,
        { method: "DELETE" }
      ),

    // Get latest output (rendered HTML)
    getLatestOutput: (slug: string) =>
      request<RecurrenceOutput>(`/api/recurrences/${slug}/outputs/latest`),

    // Get specific output by date folder
    getOutput: (slug: string, dateFolder: string) =>
      request<RecurrenceOutput>(`/api/recurrences/${slug}/outputs/${dateFolder}`),

    // List output history
    listOutputs: async (slug: string, limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      const data = await request<RecurrenceOutput[] | { outputs: RecurrenceOutput[]; total: number }>(
        `/api/recurrences/${slug}/outputs${params}`
      );
      // API returns plain array; normalize to { outputs, total }
      if (Array.isArray(data)) {
        return { outputs: data, total: data.length };
      }
      return data;
    },

    // Trigger immediate execution
    run: (slug: string) =>
      request<{ success: boolean; message: string }>(
        `/api/recurrences/${slug}/run`,
        { method: "POST" }
      ),

    // ADR-148: Export task output as PDF/XLSX/DOCX
    export: (slug: string, format: string, dateFolder?: string) => {
      const params = dateFolder ? `&date_folder=${dateFolder}` : "";
      return request<{ success: boolean; url: string; format: string; title: string }>(
        `/api/recurrences/${slug}/export?format=${format}${params}`
      );
    },

    // ADR-207 P4b (2026-04-22) + ADR-231 D5 + ADR-235 D1.c (2026-04-29):
    // `listTypes` + `getType` DELETED. The `/api/tasks/types` endpoints never
    // had an `/api/recurrences/types` equivalent — the registry was dissolved
    // before the URL rename. Recurrence creation happens via YARNNN
    // self-declaration through ManageRecurrence(action='create', shape=...,
    // slug=..., body={...}). Not a catalog pick.

    // ADR-145: Process step outputs for a given run
    getStepOutputs: (slug: string, dateFolder: string) =>
      request<ProcessStepsResponse>(
        `/api/recurrences/${slug}/outputs/${dateFolder}/steps`
      ),

    // Live execution progress
    getRunStatus: (slug: string) =>
      request<RunStatus>(`/api/recurrences/${slug}/status`),

    // ADR-158 Phase 2: Update task-level source selection in TASK.md.
    // sources: {platform: ids[]} e.g. { slack: ["C123", "C456"] }
    updateSources: (slug: string, sources: Record<string, string[]>) =>
      request<Recurrence>(`/api/recurrences/${slug}/sources`, {
        method: "PATCH",
        body: JSON.stringify({ sources }),
      }),
  },

  // ADR-219 Commit 4: narrative filter-over-substrate for /work list view.
  // Replaces the `task.last_run_at` timestamp on list rows with the
  // most-recent material-weight narrative entry's headline. Tasks with
  // no narrative entries yet are simply absent from the response — the
  // list view falls back to no headline (graceful empty state).
  narrative: {
    byTask: (windowHours?: number) => {
      const qs = windowHours ? `?window_hours=${windowHours}` : "";
      return request<NarrativeByTaskResponse>(`/api/narrative/by-task${qs}`);
    },
  },

  // Workspace Explorer (ADR-152) + Workspace Lifecycle (ADR-244)
  workspace: {
    // ADR-244: canonical workspace-state read. Replaces the legacy
    // memory-user-onboarding-state endpoint with extended shape
    // (substrate_status + capability_gaps + available_programs). Triggers
    // lazy roster scaffolding when no agents exist (idempotent first-login
    // side-effect preserved from the legacy endpoint).
    getState: () =>
      request<{
        has_agents: boolean;
        activation_state: 'none' | 'post_fork_pre_author' | 'operational';
        active_program_slug: string | null;
        available_programs: Array<{
          slug: string;
          title: string;
          tagline: string | null;
          status: 'active' | 'deferred';
          deferred: boolean;
          oracle: Record<string, unknown>;
          current_phase: string | null;
          // ADR-266 D5/D6: human label for the phase, derived from the
          // bundle MANIFEST's phases[].label. FE renders this — never the
          // bare enum slug.
          current_phase_label: string | null;
        }>;
        substrate_status: {
          mandate: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
          identity: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
          brand: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
          autonomy: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
          principles: { path: string; state: 'skeleton' | 'authored' | 'missing'; last_revised_at: string | null };
        };
        capability_gaps: Array<{
          capability: string;
          requires_platform: string;
          connected: boolean;
        }>;
      }>("/api/workspace/state"),

    // ADR-266 D8: bundled read for /workspace page mount.
    // Replaces 7 round-trips (state + 6 file reads) with 1. The four
    // concept cards still self-fetch as a fallback for /agents reuse —
    // when WorkspaceConfigSection passes data props, cards skip self-fetch.
    getSetupBundle: () =>
      request<{
        state: Awaited<ReturnType<typeof api.workspace.getState>>;
        mandate: WorkspaceFileWithRevision;
        autonomy_yaml: WorkspaceFileWithRevision;
        principles_prose: WorkspaceFileWithRevision;
        principles_yaml: WorkspaceFileWithRevision;
        identity: WorkspaceFileWithRevision;
        brand: WorkspaceFileWithRevision;
      }>("/api/workspace/setup-bundle"),

    // ADR-154: Structured navigation for Agent OS workfloor.
    // ADR-236 Item 6 (2026-04-29): `mode` and `essential` removed from
    // the contract — both were dropped from `tasks` by ADR-231
    // migration 164. The recurrence label (Recurring vs One-time) is
    // derived from `schedule` per ADR-163 / web/types/index.ts
    // recurrenceLabel().
    getNav: () =>
      request<{
        tasks: Array<{
          slug: string; title: string; status: string;
          schedule: string | null;
          next_run_at: string | null; last_run_at: string | null;
        }>;
        domains: Array<{
          key: string; display_name: string; entity_count: number;
          entity_type: string | null; path: string;
        }>;
        uploads: Array<{
          name: string; path: string; updated_at: string | null;
        }>;
        settings: Array<{
          name: string; filename: string; path: string; updated_at: string | null;
        }>;
        readiness: {
          identity: 'empty' | 'sparse' | 'rich';
          has_domains: boolean;
          has_tasks: boolean;
          phase: 'setup' | 'ready' | 'active';
        };
      }>(`/api/workspace/nav`),

    // ADR-154: Domain entity listing for domain browser view
    getDomainEntities: (domainKey: string) =>
      request<{
        domain_key: string; domain_path: string; display_name: string; entity_type: string | null;
        synthesis_files: Array<{
          name: string; filename: string; path: string; updated_at: string | null; preview: string | null;
        }>;
        entities: Array<{
          slug: string; name: string; last_updated: string | null;
          preview: string | null; files: Array<{ name: string; path: string; updated_at: string | null }>;
        }>;
        entity_count: number;
      }>(`/api/workspace/domain/${domainKey}`),

    // Legacy tree (still used by raw file viewer)
    getTree: (root: string = "/workspace") =>
      request<WorkspaceTreeNode[]>(`/api/workspace/tree?root=${encodeURIComponent(root)}`),

    getFile: (path: string) =>
      request<WorkspaceFile>(`/api/workspace/file?path=${encodeURIComponent(path)}`),

    // ADR-312 Home slot #5: recent delivered outputs across the whole
    // workspace (not per-recurrence). Kernel-universal — every workspace.
    recentArtifacts: (limit: number = 5) =>
      request<{
        artifacts: Array<{
          slug: string;
          date: string;
          path: string;
          summary: string | null;
          updated_at: string | null;
        }>;
      }>(`/api/workspace/recent-artifacts?limit=${limit}`),

    editFile: (path: string, content: string, summary?: string, message?: string) =>
      request<{ success: boolean; path: string; updated_at: string }>(
        `/api/workspace/file`,
        { method: "PATCH", body: JSON.stringify({ path, content, summary, message }) }
      ),

    // ADR-209 Phase 4 + ADR-329 (amended): the revision chain for a node.
    // Node Details (ADR-329) renders both scopes off this one route:
    //   - { path }        → FILE Details: exact-path chain (revert/diff).
    //   - { pathPrefix }   → FOLDER Details: recent revisions across the
    //                        subtree, each row carrying the file it changed
    //                        (revisions[].path populated). Read-only aggregate.
    // Exactly one of { path, pathPrefix } must be provided.
    listRevisions: (
      scope: { path: string; pathPrefix?: never } | { path?: never; pathPrefix: string },
      limit: number = 10,
    ) => {
      const q =
        scope.path !== undefined
          ? `path=${encodeURIComponent(scope.path)}`
          : `path_prefix=${encodeURIComponent(scope.pathPrefix)}`;
      return request<{
        path: string;
        count: number;
        revisions: Array<{
          id: string;
          authored_by: string;
          author_identity_uuid: string | null;
          message: string;
          created_at: string;
          parent_version_id: string | null;
          // Populated only in the folder (pathPrefix) case.
          path?: string | null;
        }>;
      }>(`/api/workspace/revisions?${q}&limit=${limit}`);
    },

    readRevision: (path: string, revisionId: string) =>
      request<{
        id: string;
        path: string;
        authored_by: string;
        author_identity_uuid: string | null;
        message: string;
        created_at: string;
        parent_version_id: string | null;
        blob_sha: string;
        content: string | null;
      }>(
        `/api/workspace/revisions/${encodeURIComponent(revisionId)}?path=${encodeURIComponent(path)}`
      ),

    diffRevisions: (path: string, fromRev: string, toRev: string) =>
      request<{
        path: string;
        from_revision: {
          id: string; authored_by: string; message: string; created_at: string;
          parent_version_id: string | null; author_identity_uuid: string | null;
        };
        to_revision: {
          id: string; authored_by: string; message: string; created_at: string;
          parent_version_id: string | null; author_identity_uuid: string | null;
        };
        diff: string;
        identical: boolean;
      }>(
        `/api/workspace/revisions/diff/two?path=${encodeURIComponent(path)}&from_rev=${encodeURIComponent(fromRev)}&to_rev=${encodeURIComponent(toRev)}`
      ),
  },

  // Account management
  account: {
    // Notification preferences
    getNotificationPreferences: () =>
      request<{
        email_agent_ready: boolean;
        email_agent_failed: boolean;
        email_suggestion_created: boolean; // ADR-060
      }>("/api/account/notification-preferences"),

    updateNotificationPreferences: (data: {
      email_agent_ready?: boolean;
      email_agent_failed?: boolean;
      email_suggestion_created?: boolean; // ADR-060
    }) =>
      request<{
        email_agent_ready: boolean;
        email_agent_failed: boolean;
        email_suggestion_created: boolean; // ADR-060
      }>("/api/account/notification-preferences", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    // Data & Privacy — ADR-122 Phase 5 + 2026-04-24 streamline (docs/features/data-privacy.md Phase 5)
    getDangerZoneStats: () =>
      request<{
        workspace_files: number;
        agents: number;
        tasks: number;
        chat_sessions: number;
        platform_connections: number;
        platform_context_files: number;
        agent_runs: number;
        // ADR-194 Reviewer queue — pending proposals surfaced for L2/L4 confirmation copy
        action_proposals: number;
      }>("/api/account/danger-zone/stats"),

    // L1: Clear work history (docs/features/data-privacy.md). Lightest
    // layer — wipes past run records + task output folders only. Tasks,
    // agents, identity, accumulated context, chat sessions all preserved.
    clearWorkHistory: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/work-history",
        { method: "DELETE" }
      ),

    clearWorkspace: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/workspace",
        { method: "DELETE" }
      ),

    clearIntegrations: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/integrations",
        { method: "DELETE" }
      ),

    resetAccount: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/reset",
        { method: "DELETE" }
      ),

    deactivateAccount: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/deactivate",
        { method: "DELETE" }
      ),
  },

  // ADR-025: Slash commands
  commands: {
    // List available slash commands for autocomplete/picker
    list: () =>
      request<{
        commands: Array<{
          name: string;
          description: string;
          command: string;
          tier: "core" | "beta";
          trigger_patterns: string[];
        }>;
        total: number;
      }>("/api/commands"),
  },

  // ADR-026: Integrations (Slack, Notion, etc.)
  integrations: {
    // List user's connected integrations
    list: () =>
      request<{
        integrations: Array<{
          id: string;
          provider: string;
          status: string;
          workspace_name: string | null;
          last_used_at: string | null;
          created_at: string;
        }>;
      }>("/api/integrations"),

    // Get specific integration
    get: (provider: string) =>
      request<{
        id: string;
        provider: string;
        status: string;
        workspace_name: string | null;
        last_used_at: string | null;
        created_at: string;
      }>(`/api/integrations/${provider}`),

    // Disconnect an integration
    disconnect: (provider: string) =>
      request<{ success: boolean; message: string }>(
        `/api/integrations/${provider}`,
        { method: "DELETE" }
      ),

    // Get authorization URL to initiate OAuth
    // Pass redirectTo to control where user lands after OAuth (e.g. "/system")
    getAuthorizationUrl: (provider: string, redirectTo?: string) =>
      request<{ authorization_url: string }>(
        `/api/integrations/${provider}/authorize${redirectTo ? `?redirect_to=${encodeURIComponent(redirectTo)}` : ''}`
      ),

    // Export to provider
    export: (
      provider: string,
      data: { agent_run_id: string; destination: Record<string, unknown> }
    ) =>
      request<{
        status: string;
        external_id: string | null;
        external_url: string | null;
        error_message: string | null;
      }>(`/api/integrations/${provider}/export`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Get export history
    getHistory: (agentId?: string) =>
      request<{
        exports: Array<{
          id: string;
          provider: string;
          status: string;
          external_url: string | null;
          created_at: string;
        }>;
        total: number;
      }>(
        `/api/integrations/history${agentId ? `?agent_id=${agentId}` : ""}`
      ),

    // ADR-027: Context Import
    // List available resources (channels/pages)
    listSlackChannels: () =>
      request<{
        channels: Array<{
          id: string;
          name: string;
          is_private: boolean;
          num_members: number;
          topic: string | null;
          purpose: string | null;
        }>;
      }>("/api/integrations/slack/channels"),

    listNotionPages: (query?: string) =>
      request<{
        pages: Array<{
          id: string;
          title: string;
          parent_type: string;
          last_edited: string | null;
          url: string | null;
        }>;
      }>(`/api/integrations/notion/pages${query ? `?query=${encodeURIComponent(query)}` : ""}`),

    // Import jobs DELETED (ADR-153/156: platform data flows through task execution)
    // startImport, getImportJob, listImportJobs removed

    // ADR-030: Landscape and Coverage
    // Get platform landscape with coverage state
    getLandscape: (provider: "slack" | "notion" | "github", refresh?: boolean) =>
      request<{
        provider: string;
        discovered_at: string | null;
        resources: Array<{
          id: string;
          name: string;
          resource_type: string;
          coverage_state: "uncovered" | "partial" | "covered" | "stale" | "excluded";
          last_extracted_at: string | null;
          items_extracted: number;
          metadata: Record<string, unknown>;
        }>;
        coverage_summary: {
          total_resources: number;
          covered_count: number;
          partial_count: number;
          stale_count: number;
          uncovered_count: number;
          excluded_count: number;
          coverage_percentage: number;
        };
      }>(`/api/integrations/${provider}/landscape${refresh ? "?refresh=true" : ""}`),

    // ADR-153: getPlatformContext DELETED — platform_content sunset

    // Update coverage state (mark as excluded or reset)
    updateCoverage: (
      provider: "slack" | "notion" | "github",
      resourceId: string,
      coverageState: "excluded" | "uncovered"
    ) =>
      request<{ success: boolean; resource_id: string; coverage_state: string }>(
        `/api/integrations/${provider}/coverage/${encodeURIComponent(resourceId)}`,
        {
          method: "PATCH",
          body: JSON.stringify({ coverage_state: coverageState }),
        }
      ),

    // ADR-033: Get integrations summary for Dashboard platform cards
    getSummary: () =>
      request<{
        platforms: Array<{
          provider: string;
          status: string;
          workspace_name: string | null;
          connected_at: string;
          resource_count: number;
          resource_type: string;
          agent_count: number;
          activity_7d: number;
        }>;
        total_agents: number;
      }>("/api/integrations/summary"),

    // ADR-171: token spend metering — tier limits and current usage
    getLimits: () =>
      request<{
        balance_usd: number;
        spend_usd: number;
        raw_balance_usd: number;
        is_subscriber: boolean;
        subscription_plan: string | null;
        next_refill: string | null;
      }>("/api/user/limits"),

    // Usage tab expansion — spend breakdown + trend + activity (ADR-172)
    getUsageDetail: () =>
      request<{
        by_work: Array<{ slug: string; runs: number; cost_usd: number; pct: number }>;
        trend: Array<{ date: string; cost_usd: number }>;
        activity: {
          runs: number;
          success_rate: number | null;
          avg_cost_usd: number;
          failed: number;
        };
      }>("/api/user/usage-detail"),

    // Get selected sources for a platform
    getSources: (provider: "slack" | "notion" | "github") =>
      request<{
        sources: Array<{
          id: string;
          type: string;
          name: string;
          last_sync_at: string | null;
          metadata?: {
            member_count?: number;
            message_count?: number;
          };
        }>;
        limit: number;
        can_add_more: boolean;
      }>(`/api/integrations/${provider}/sources`),

    // Update selected sources for a platform
    updateSources: (
      provider: "slack" | "notion" | "github",
      sourceIds: string[]
    ) =>
      request<{
        success: boolean;
        selected_sources: Array<{ id: string; name: string; type: string }>;
        message: string;
      }>(`/api/integrations/${provider}/sources`, {
        method: "PUT",
        body: JSON.stringify({ source_ids: sourceIds }),
      }),

    // Trigger on-demand sync for a platform
    triggerSync: (provider: "slack" | "notion" | "github") =>
      request<{
        success: boolean;
        message: string;
        sync_started_at?: string;
      }>(`/api/integrations/${provider}/sync`, {
        method: "POST",
      }),

    // ADR-049: Get sync status for a platform (freshness info)
    getSyncStatus: (provider: string) =>
      request<{
        platform: string;
        synced_resources: Array<{
          resource_id: string;
          resource_name: string | null;
          last_synced: string | null;
          freshness_status: "fresh" | "recent" | "stale" | "unknown";
          items_synced: number;
          last_error?: string | null;
          last_error_at?: string | null;
        }>;
        stale_count: number;
        error_count: number;
      }>(`/api/integrations/${provider}/sync-status`),

    // ADR-049: Trigger platform sync (alias for triggerSync with broader typing)
    syncPlatform: (provider: string) =>
      request<{
        success: boolean;
        message: string;
        sources_count?: number;
      }>(`/api/integrations/${provider}/sync`, {
        method: "POST",
      }),

    // ADR-050: Notion designated page (streamlined output pattern)
    getNotionDesignatedPage: () =>
      request<{
        success: boolean;
        designated_page_id: string | null;
        designated_page_name: string | null;
        message: string;
      }>("/api/integrations/notion/designated-page"),

    setNotionDesignatedPage: (pageId: string, pageName?: string) =>
      request<{
        success: boolean;
        designated_page_id: string | null;
        designated_page_name: string | null;
        message: string;
      }>("/api/integrations/notion/designated-page", {
        method: "PUT",
        body: JSON.stringify({ page_id: pageId, page_name: pageName }),
      }),

    clearNotionDesignatedPage: () =>
      request<{
        success: boolean;
        designated_page_id: null;
        designated_page_name: null;
        message: string;
      }>("/api/integrations/notion/designated-page", {
        method: "DELETE",
      }),

    // ADR-183: Commerce connection (API key auth, not OAuth)
    connectCommerce: (apiKey: string) =>
      request<{
        success: boolean;
        connection_id: string;
        platform: string;
        provider: string;
        status: string;
        store_name: string;
      }>("/api/integrations/commerce/connect", {
        method: "POST",
        body: JSON.stringify({ api_key: apiKey }),
      }),

    // ADR-187: Trading connection (API key + secret auth)
    connectTrading: (apiKey: string, apiSecret: string, paper: boolean = true, marketDataKey?: string) =>
      request<{
        success: boolean;
        connection_id: string;
        platform: string;
        provider: string;
        status: string;
        paper: boolean;
        account_number: string;
      }>("/api/integrations/trading/connect", {
        method: "POST",
        body: JSON.stringify({
          api_key: apiKey,
          api_secret: apiSecret,
          paper,
          market_data_key: marketDataKey,
        }),
      }),

  },

  // ADR-063: Activity Log (what YARNNN has done)
  activity: {
    // List recent activity from activity_log table
    list: (options?: {
      limit?: number;
      days?: number;
      eventType?: string;
    }) => {
      const params = new URLSearchParams();
      if (options?.limit) params.append("limit", options.limit.toString());
      if (options?.days) params.append("days", options.days.toString());
      if (options?.eventType) params.append("event_type", options.eventType);
      const query = params.toString();
      return request<{
        activities: Array<{
          id: string;
          event_type: string;
          event_ref: string | null;
          summary: string;
          metadata: Record<string, unknown> | null;
          created_at: string;
        }>;
        total: number;
      }>(`/api/memory/activity${query ? `?${query}` : ""}`);
    },
  },

  // ADR-034: Context Domains (Context v2)
  domains: {
    // List user's domains with summary stats
    list: () =>
      request<{
        domains: ContextDomainSummary[];
        total: number;
      }>("/api/domains"),

    // Get active domain for current context
    getActive: (agentId?: string) => {
      const params = agentId ? `?agent_id=${agentId}` : "";
      return request<ActiveDomainResponse>(`/api/domains/active${params}`);
    },

    // Get domain details
    get: (domainId: string) =>
      request<ContextDomainDetail>(`/api/domains/${domainId}`),

    // Rename a domain
    rename: (domainId: string, name: string) =>
      request<{ success: boolean; name: string }>(`/api/domains/${domainId}`, {
        method: "PATCH",
        body: JSON.stringify({ name }),
      }),

    // Manually trigger domain recomputation (admin/debug)
    recompute: () =>
      request<{ success: boolean; changes: Record<string, number> }>(
        "/api/domains/recompute",
        { method: "POST" }
      ),

    // Domain memories (Context v2 - replaces projectMemories)
    memories: {
      // List memories in a domain
      list: (domainId: string) =>
        request<Memory[]>(`/api/domains/${domainId}/memories`),

      // Create a memory in a domain
      create: (domainId: string, data: MemoryCreate) =>
        request<Memory>(`/api/domains/${domainId}/memories`, {
          method: "POST",
          body: JSON.stringify(data),
        }),
    },
  },

  // System/Operations status (ADR-141/153/156: streamlined)
  system: {
    getStatus: () =>
      request<{
        platform_sync: Array<{
          platform: string;
          connected: boolean;
          last_synced_at: string | null;
          next_sync_at: string | null;
          source_count: number;
          status: "healthy" | "stale" | "pending" | "disconnected" | "unknown";
          resources: Array<{
            resource_id: string;
            resource_name: string | null;
            last_synced_at: string | null;
            item_count: number;
            has_cursor: boolean;
            status: "fresh" | "recent" | "stale" | "never_synced" | "unknown";
          }>;
        }>;
        background_jobs: Array<{
          job_type: string;
          last_run_at: string | null;
          last_run_status: "success" | "failed" | "never_run" | "unknown";
          last_run_summary: string | null;
          items_processed: number;
          schedule_description: string | null;
        }>;
        tier: string;
        sync_frequency: string;
      }>("/api/system/status"),

    // Lightweight endpoint for polling sync completion during pipeline runs
    getSyncTimestamps: () =>
      request<{
        timestamps: Record<string, string>;
      }>("/api/system/sync-timestamps"),

    // Per-invocation execution log — powers /activity page (ADR-250 + ADR-265)
    executionEvents: (opts: { slug?: string; status?: string; mode?: string; limit?: number } = {}) => {
      const parts: string[] = [];
      if (opts.slug) parts.push(`slug=${encodeURIComponent(opts.slug)}`);
      if (opts.status) parts.push(`status=${encodeURIComponent(opts.status)}`);
      if (opts.mode) parts.push(`mode=${encodeURIComponent(opts.mode)}`);
      if (opts.limit) parts.push(`limit=${opts.limit}`);
      const qs = parts.length ? `?${parts.join("&")}` : "";
      return request<ExecutionEvent[]>(`/api/system/execution-events${qs}`);
    },
  },

  // ADR-193: Action proposals (approval loop)
  proposals: {
    /** List the user's proposals (default: pending only). */
    list: (status: string = "pending", limit: number = 50) =>
      request<{
        proposals: Array<{
          id: string;
          // ADR-307: generic gated-action queue shape.
          primitive: string;
          family: "capital" | "substrate";
          inputs: Record<string, unknown>;
          decision_context: Record<string, unknown> | null;
          status: string;
          task_slug: string | null;
          agent_slug: string | null;
          source: string | null;
          expires_at: string;
          created_at: string;
          approved_at: string | null;
          executed_at: string | null;
          execution_result: Record<string, unknown> | null;
          rejection_reason: string | null;
          approved_by: string | null;
        }>;
        /**
         * ADR-211 D7 prospective-attribution contract (Invariant I1):
         * the current occupant of the Reviewer seat. Frontend displays
         * this alongside pending proposals so the operator knows who
         * is set to render the verdict. Empty object for pre-Phase-4
         * workspaces (treat as "unknown — default human occupant").
         */
        current_occupant: {
          occupant: string;
          occupant_class: "human" | "ai" | "external" | "impersonated" | "";
          display_label: string;
        } | Record<string, never>;
      }>(`/api/proposals?status=${encodeURIComponent(status)}&limit=${limit}`),

    /**
     * Fetch a single proposal by id. Response is enveloped per ADR-211
     * D7 Invariant I1 + I2 — `current_occupant` sits alongside `proposal`
     * so the frontend can display seat attribution for both pending and
     * rendered verdicts (for rendered, use proposal.reviewer_identity;
     * for pending, use current_occupant).
     */
    get: (id: string) =>
      request<{
        proposal: {
          id: string;
          // ADR-307: generic gated-action queue shape.
          primitive: string;
          family: "capital" | "substrate";
          inputs: Record<string, unknown>;
          decision_context: Record<string, unknown> | null;
          status: string;
          expires_at: string;
          created_at: string;
          reviewer_identity?: string | null;
          reviewer_reasoning?: string | null;
        };
        current_occupant: {
          occupant: string;
          occupant_class: "human" | "ai" | "external" | "impersonated" | "";
          display_label: string;
        } | Record<string, never>;
      }>(`/api/proposals/${id}`),

    /** Approve + execute. Optional modified_inputs merged over proposal.inputs. */
    approve: (id: string, modified_inputs?: Record<string, unknown>) =>
      request<{
        success: boolean;
        proposal_id?: string;
        execution_result?: Record<string, unknown>;
        error?: string;
      }>(`/api/proposals/${id}/approve`, {
        method: "POST",
        body: JSON.stringify({ modified_inputs: modified_inputs ?? null }),
      }),

    /** Reject with optional reason. */
    reject: (id: string, reason?: string) =>
      request<{
        success: boolean;
        proposal_id?: string;
        status?: string;
      }>(`/api/proposals/${id}/reject`, {
        method: "POST",
        body: JSON.stringify({ reason: reason ?? null }),
      }),
  },

  // ADR-310 D4: MCP OAuth login handoff. The web /mcp/authorize page calls
  // this with the operator's JWT to bind the real user to the pending auth
  // code, then navigates the browser to the returned redirect_url (back to
  // the OAuth client — Claude.ai / ChatGPT / etc.).
  mcp: {
    completeAuthorize: (code: string) =>
      request<{ redirect_url: string }>(
        `/api/mcp/oauth-callback?code=${encodeURIComponent(code)}`
      ),
  },

};

export default api;
