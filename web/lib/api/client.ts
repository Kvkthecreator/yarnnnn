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
  Document,
  DocumentDetail,
  DocumentUploadResponse,
  DocumentDownloadResponse,
  DocumentListResponse,
  DeleteResponse,
  OnboardingStateResponse,
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
  // ADR-138: Tasks
  Task,
  TaskDetail,
  TaskCreate,
  TaskOutput,
  // ADR-145: Task type registry
  TaskType,
  TaskTypesResponse,
  ProcessStepsResponse,
  RunStatus,
  // ADR-152: Workspace Explorer
  WorkspaceTreeNode,
  WorkspaceFile,
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
  // ADR-108: User context entries (user-scoped, stored in /memory/notes.md)
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

  // ADR-144: onboarding.enrich deleted — context enrichment via UpdateContext primitive (ADR-146).
  // getState kept for roster scaffolding trigger on first login.
  onboarding: {
    getState: () =>
      request<{ has_agents: boolean }>("/api/memory/user/onboarding-state"),
  },

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

  // Document endpoints (ADR-008: Document Pipeline)
  documents: {
    // List user's documents
    list: (status?: string) => {
      const params = status ? `?status=${status}` : "";
      return request<DocumentListResponse>(`/api/documents${params}`);
    },

    // Upload document
    upload: async (file: File) => {
      const headers = await getAuthHeaders();
      delete (headers as Record<string, string>)["Content-Type"]; // Let browser set for FormData

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

      return response.json() as Promise<DocumentUploadResponse>;
    },

    // Get document details with stats
    get: (documentId: string) =>
      request<DocumentDetail>(`/api/documents/${documentId}`),

    // Get signed download URL
    download: (documentId: string) =>
      request<DocumentDownloadResponse>(`/api/documents/${documentId}/download`),

    // Delete document
    delete: (documentId: string) =>
      request<{ success: boolean; message: string }>(
        `/api/documents/${documentId}`,
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
            };
          }>;
        }>;
      }>(`/api/chat/history?${params.toString()}`);
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

  // ADR-138: Tasks endpoints
  tasks: {
    list: (status?: string) => {
      const params = status ? `?status=${status}` : "";
      return request<Task[]>(`/api/tasks${params}`);
    },

    get: (slug: string) =>
      request<TaskDetail>(`/api/tasks/${slug}`),

    create: (data: TaskCreate) =>
      request<Task>("/api/tasks", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (slug: string, data: Partial<TaskCreate> & { status?: string }) =>
      request<Task>(`/api/tasks/${slug}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    delete: (slug: string) =>
      request<{ success: boolean; message: string }>(
        `/api/tasks/${slug}`,
        { method: "DELETE" }
      ),

    // Get latest output (rendered HTML)
    getLatestOutput: (slug: string) =>
      request<TaskOutput>(`/api/tasks/${slug}/outputs/latest`),

    // Get specific output by date folder
    getOutput: (slug: string, dateFolder: string) =>
      request<TaskOutput>(`/api/tasks/${slug}/outputs/${dateFolder}`),

    // List output history
    listOutputs: async (slug: string, limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      const data = await request<TaskOutput[] | { outputs: TaskOutput[]; total: number }>(
        `/api/tasks/${slug}/outputs${params}`
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
        `/api/tasks/${slug}/run`,
        { method: "POST" }
      ),

    // ADR-148: Export task output as PDF/XLSX/DOCX
    export: (slug: string, format: string, dateFolder?: string) => {
      const params = dateFolder ? `&date_folder=${dateFolder}` : "";
      return request<{ success: boolean; url: string; format: string; title: string }>(
        `/api/tasks/${slug}/export?format=${format}${params}`
      );
    },

    // ADR-145 / ADR-166: Task type registry filtered by output_kind
    listTypes: (output_kind?: string) => {
      const params = output_kind ? `?output_kind=${output_kind}` : "";
      return request<TaskTypesResponse>(`/api/tasks/types${params}`);
    },

    getType: (typeKey: string) =>
      request<TaskType>(`/api/tasks/types/${typeKey}`),

    // ADR-145: Process step outputs for a given run
    getStepOutputs: (slug: string, dateFolder: string) =>
      request<ProcessStepsResponse>(
        `/api/tasks/${slug}/outputs/${dateFolder}/steps`
      ),

    // Live execution progress
    getRunStatus: (slug: string) =>
      request<RunStatus>(`/api/tasks/${slug}/status`),

    // ADR-158 Phase 2: Update task-level source selection in TASK.md.
    // sources: {platform: ids[]} e.g. { slack: ["C123", "C456"] }
    updateSources: (slug: string, sources: Record<string, string[]>) =>
      request<Task>(`/api/tasks/${slug}/sources`, {
        method: "PATCH",
        body: JSON.stringify({ sources }),
      }),
  },

  // Workspace Explorer (ADR-152)
  workspace: {
    // ADR-154: Structured navigation for Agent OS workfloor
    getNav: () =>
      request<{
        tasks: Array<{
          slug: string; title: string; status: string;
          mode: string | null; schedule: string | null;
          next_run_at: string | null; last_run_at: string | null;
          essential?: boolean;
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

    editFile: (path: string, content: string, summary?: string) =>
      request<{ success: boolean; path: string; updated_at: string }>(
        `/api/workspace/file`,
        { method: "PATCH", body: JSON.stringify({ path, content, summary }) }
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

    // Data & Privacy — ADR-122 Phase 5: workspace-aware purge
    getDangerZoneStats: () =>
      request<{
        workspace_files: number;
        agents: number;
        tasks: number;
        chat_sessions: number;
        platform_connections: number;
        platform_context_files: number;
        agent_runs: number;
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
        is_subscriber: boolean;
        subscription_plan: string | null;
        next_refill: string | null;
      }>("/api/user/limits"),

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
  },

};

export default api;
