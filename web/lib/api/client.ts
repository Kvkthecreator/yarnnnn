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
  KnowledgeFile,
  KnowledgeFileDetail,
  KnowledgeFileCreateInput,
  KnowledgeFilesResponse,
  KnowledgeVersionsResponse,
  KnowledgeSummaryResponse,
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
  // ADR-119 Phase 4: Projects
  ProjectSummary,
  ProjectDetail,
  ProjectActivityItem,
  // ADR-119 Phase 4b: Outputs + Contributions
  OutputManifest,
  ProjectOutputDetail,
  ContributionFile,
} from "@/types";
import type {
  AdminOverviewStats,
  AdminMemoryStats,
  AdminDocumentStats,
  AdminChatStats,
  AdminUserRow,
  AdminSyncHealth,
  AdminPipelineStats,
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

  // ADR-108: Profile — reads/writes /memory/MEMORY.md
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

  // ADR-108: Styles — tone/verbosity per platform, stored in /memory/preferences.md
  styles: {
    list: () =>
      request<{
        styles: Array<{
          platform: string;
          tone?: string;
          verbosity?: string;
        }>;
      }>("/api/memory/styles"),
    get: (platform: string) =>
      request<{
        platform: string;
        tone?: string;
        verbosity?: string;
      }>(`/api/memory/styles/${platform}`),
    update: (platform: string, data: {
      tone?: string;
      verbosity?: string;
    }) =>
      request<{
        platform: string;
        tone?: string;
        verbosity?: string;
      }>(`/api/memory/styles/${platform}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (platform: string) =>
      request<{
        platform: string;
        tone?: string;
        verbosity?: string;
      }>(`/api/memory/styles/${platform}`, {
        method: "DELETE",
      }),
  },

  // Onboarding state
  onboarding: {
    getState: () =>
      request<OnboardingStateResponse>("/api/memory/user/onboarding-state"),
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
  },

  // Knowledge filesystem (ADR-107 Phase 3)
  knowledge: {
    summary: () =>
      request<KnowledgeSummaryResponse>("/api/knowledge/summary"),

    listFiles: (
      options?: {
        content_class?: "digests" | "analyses" | "briefs" | "research" | "insights";
        limit?: number;
      }
    ) => {
      const params = new URLSearchParams();
      if (options?.content_class) params.set("content_class", options.content_class);
      if (typeof options?.limit === "number") params.set("limit", String(options.limit));
      const query = params.toString();
      return request<KnowledgeFilesResponse>(
        `/api/knowledge/files${query ? `?${query}` : ""}`
      );
    },

    readFile: (path: string) =>
      request<KnowledgeFileDetail>(
        `/api/knowledge/files/read?path=${encodeURIComponent(path)}`
      ),

    createFile: (data: KnowledgeFileCreateInput) =>
      request<KnowledgeFile>(
        `/api/knowledge/files`,
        { method: "POST", body: JSON.stringify(data) }
      ),

    listVersions: (path: string) =>
      request<KnowledgeVersionsResponse>(
        `/api/knowledge/files/versions?path=${encodeURIComponent(path)}`
      ),
  },

  // Chat endpoints (streaming handled separately in useChat hook)
  chat: {
    // Get global chat history
    globalHistory: (limit: number = 1, agentId?: string, projectSlug?: string) => {
      const params = new URLSearchParams({ limit: String(limit) });
      if (agentId) params.set('agent_id', agentId);
      if (projectSlug) params.set('project_slug', projectSlug);
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
            };
          }>;
        }>;
      }>(`/api/chat/history?${params.toString()}`);
    },

    // List global (non-agent-scoped) TP sessions — lightweight metadata for dashboard panel
    listSessions: (limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      return request<Array<{ id: string; created_at: string; summary?: string; message_count: number }>>(
        `/api/chat/sessions${params}`
      );
    },
  },

  // Subscription endpoints (Lemon Squeezy)
  // ADR-100: 2-tier pricing (Free/Pro) with Early Bird option
  subscription: {
    getStatus: () => request<SubscriptionStatus>("/api/subscription/status"),

    createCheckout: (
      billingPeriod: "monthly" | "yearly" = "monthly",
      earlyBird: boolean = false
    ) =>
      request<CheckoutResponse>("/api/subscription/checkout", {
        method: "POST",
        body: JSON.stringify({ billing_period: billingPeriod, early_bird: earlyBird }),
      }),

    getPortal: () => request<PortalResponse>("/api/subscription/portal"),
  },

  // Admin endpoints (requires admin access)
  admin: {
    stats: () => request<AdminOverviewStats>("/api/admin/stats"),
    users: () => request<AdminUserRow[]>("/api/admin/users"),
    memoryStats: () => request<AdminMemoryStats>("/api/admin/memory-stats"),
    documentStats: () => request<AdminDocumentStats>("/api/admin/document-stats"),
    chatStats: () => request<AdminChatStats>("/api/admin/chat-stats"),
    exportUsers: async () => {
      const headers = await getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/api/admin/export/users`, {
        credentials: "include",
        headers,
      });

      if (!response.ok) {
        throw new APIError(response.status, response.statusText);
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get("Content-Disposition");
      const filenameMatch = contentDisposition?.match(/filename=(.+)/);
      const filename = filenameMatch ? filenameMatch[1] : "yarnnn_users.xlsx";

      // Create blob and trigger download
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
    // ADR-073: Pipeline observability
    syncHealth: () => request<AdminSyncHealth>("/api/admin/sync-health"),
    pipelineStats: () => request<AdminPipelineStats>("/api/admin/pipeline-stats"),
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

  // ADR-119 Phase 4: Projects
  projects: {
    list: () =>
      request<{ projects: ProjectSummary[]; count: number }>("/api/projects"),

    get: (slug: string) =>
      request<ProjectDetail>(`/api/projects/${slug}`),

    archive: (slug: string) =>
      request<{ project_slug: string; archived: boolean }>(
        `/api/projects/${slug}`,
        { method: "DELETE" }
      ),

    getActivity: (slug: string, limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      return request<{ activities: ProjectActivityItem[]; total: number }>(
        `/api/projects/${slug}/activity${params}`
      );
    },

    // ADR-119 P4b: Output + contribution endpoints
    getOutputs: (slug: string, limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      return request<{ outputs: OutputManifest[]; total: number }>(
        `/api/projects/${slug}/outputs${params}`
      );
    },

    getOutput: (slug: string, folder: string) =>
      request<ProjectOutputDetail>(`/api/projects/${slug}/outputs/${folder}`),

    getContributions: (slug: string, agentSlug: string) =>
      request<{ agent_slug: string; files: ContributionFile[] }>(
        `/api/projects/${slug}/contributions/${agentSlug}`
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
        projects: number;
        chat_sessions: number;
        platform_connections: number;
        platform_content: number;
      }>("/api/account/danger-zone/stats"),

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

    // Start import job
    startImport: (
      provider: "slack" | "notion" | "gmail" | "calendar",
      data: {
        resource_id: string;
        resource_name?: string;
        project_id?: string;
        instructions?: string;
        config?: {
          learn_style?: boolean;
          style_user_id?: string;
        };
        // ADR-030: Scope parameters
        scope?: {
          recency_days?: number;
          max_items?: number;
          include_sent?: boolean;
          include_threads?: boolean;
        };
      }
    ) =>
      request<{
        id: string;
        provider: string;
        resource_id: string;
        resource_name: string | null;
        status: string;
        progress: number;
        created_at: string;
      }>(`/api/integrations/${provider}/import`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Get import job status
    getImportJob: (jobId: string) =>
      request<{
        id: string;
        provider: string;
        resource_id: string;
        resource_name: string | null;
        status: string;
        progress: number;
        // ADR-030: Progress details for real-time tracking
        progress_details: {
          phase: "fetching" | "processing" | "storing";
          items_total: number;
          items_completed: number;
          current_resource: string | null;
          updated_at: string;
        } | null;
        result: {
          blocks_created: number;
          items_processed: number;
          items_filtered: number;
          summary: string;
          style_learned?: boolean;
          style_confidence?: string;
        } | null;
        error_message: string | null;
        created_at: string;
        started_at: string | null;
        completed_at: string | null;
      }>(`/api/integrations/import/${jobId}`),

    // List import jobs
    listImportJobs: (params?: { status?: string; provider?: string; limit?: number }) =>
      request<{
        jobs: Array<{
          id: string;
          provider: string;
          resource_id: string;
          resource_name: string | null;
          status: string;
          progress: number;
          result: Record<string, unknown> | null;
          error_message: string | null;
          created_at: string;
          completed_at: string | null;
        }>;
      }>(
        `/api/integrations/import${params ? `?${new URLSearchParams(
          Object.entries(params)
            .filter(([, v]) => v !== undefined)
            .map(([k, v]) => [k, String(v)])
        ).toString()}` : ""}`
      ),

    // ADR-030: Landscape and Coverage
    // Get platform landscape with coverage state
    getLandscape: (provider: "slack" | "notion" | "gmail" | "calendar", refresh?: boolean) =>
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

    // ADR-072: Get synced platform content from platform_content
    getPlatformContext: (
      provider: "slack" | "notion" | "gmail" | "calendar",
      options?: { limit?: number; resourceId?: string; offset?: number }
    ) =>
      request<{
        items: Array<{
          id: string;
          content: string;
          content_type: string | null;
          resource_id: string;
          resource_name: string | null;
          source_timestamp: string | null;
          fetched_at: string;  // ADR-072: platform_content uses fetched_at
          retained: boolean;  // ADR-072: retention flag
          retained_reason: string | null;  // ADR-072: why retained
          retained_at: string | null;  // ADR-072: when marked retained
          expires_at: string | null;  // ADR-072: for ephemeral content
          metadata: Record<string, unknown>;
        }>;
        total_count: number;
        retained_count: number;  // ADR-072: accumulation visibility
        freshest_at: string | null;
        platform: string;
      }>(
        `/api/integrations/${provider}/context${
          options
            ? `?${new URLSearchParams(
                Object.entries(options)
                  .filter(([, v]) => v !== undefined)
                  .map(([k, v]) => [k === "resourceId" ? "resource_id" : k, String(v)])
              ).toString()}`
            : ""
        }`
      ),

    // Update coverage state (mark as excluded or reset)
    updateCoverage: (
      provider: "slack" | "notion" | "gmail" | "calendar",
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

    // ADR-100: 2-tier monetization — Source Selection & Limits
    // Get user's tier limits, current usage, and next sync time
    getLimits: () =>
      request<{
        tier: "free" | "pro";
        limits: {
          slack_channels: number;
          gmail_labels: number;
          notion_pages: number;
          calendars: number;
          total_platforms: number;
          sync_frequency: "1x_daily" | "2x_daily" | "4x_daily" | "hourly";
          monthly_messages: number; // -1 for unlimited
          active_agents: number; // -1 for unlimited
        };
        usage: {
          slack_channels: number;
          gmail_labels: number;
          notion_pages: number;
          calendars: number;
          platforms_connected: number;
          monthly_messages_used: number;
          active_agents: number;
        };
        next_sync: string | null; // ISO timestamp
      }>("/api/user/limits"),

    // Get selected sources for a platform
    getSources: (provider: "slack" | "gmail" | "notion" | "calendar") =>
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
      provider: "slack" | "gmail" | "notion" | "calendar",
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
    triggerSync: (provider: "slack" | "gmail" | "notion") =>
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

    // ADR-050/051: Google designated settings (Calendar + Email)
    getGoogleDesignatedSettings: () =>
      request<{
        success: boolean;
        designated_calendar_id: string | null;
        designated_calendar_name: string | null;
        designated_email: string | null;
        message: string;
      }>("/api/integrations/google/designated-settings"),

    setGoogleDesignatedSettings: (options: {
      calendarId?: string;
      calendarName?: string;
      email?: string;
    }) =>
      request<{
        success: boolean;
        designated_calendar_id: string | null;
        designated_calendar_name: string | null;
        designated_email: string | null;
        message: string;
      }>("/api/integrations/google/designated-settings", {
        method: "PUT",
        body: JSON.stringify({
          designated_calendar_id: options.calendarId,
          designated_calendar_name: options.calendarName,
          designated_email: options.email,
        }),
      }),

    clearGoogleDesignatedSettings: () =>
      request<{
        success: boolean;
        designated_calendar_id: null;
        designated_calendar_name: null;
        designated_email: string | null; // Email preserved
        message: string;
      }>("/api/integrations/google/designated-settings", {
        method: "DELETE",
      }),

    // List Google Calendars for picker
    listGoogleCalendars: () =>
      request<{
        calendars: Array<{ id: string; summary: string; primary?: boolean }>;
      }>("/api/integrations/google/calendars"),

    // Get calendar events for visual calendar display
    getCalendarEvents: (options?: {
      calendarId?: string;
      timeMin?: string;  // RFC3339 format
      timeMax?: string;  // RFC3339 format
      maxResults?: number;
    }) => {
      const params = new URLSearchParams();
      if (options?.calendarId) params.append("calendar_id", options.calendarId);
      if (options?.timeMin) params.append("time_min", options.timeMin);
      if (options?.timeMax) params.append("time_max", options.timeMax);
      if (options?.maxResults) params.append("max_results", String(options.maxResults));
      const query = params.toString();
      return request<{
        events: Array<{
          id: string;
          title: string;
          start: string;
          end: string;
          attendees: Array<{ email: string; name?: string; self?: boolean }>;
          location?: string;
          description?: string;
          meeting_link?: string;
          recurring: boolean;
        }>;
        calendar_id: string;
      }>(`/api/integrations/google/events${query ? `?${query}` : ""}`);
    },
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

  // ADR-072/073: System/Operations status
  system: {
    // Get system operations status with per-resource detail
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
          content: {
            total_items: number;
            retained_items: number;
            ephemeral_items: number;
            freshest_at: string | null;
          } | null;
        }>;
        background_jobs: Array<{
          job_type: string;
          last_run_at: string | null;
          last_run_status: "success" | "failed" | "never_run" | "unknown";
          last_run_summary: string | null;
          items_processed: number;
          schedule_description: string | null;  // ADR-084
        }>;
        tier: string;
        sync_frequency: string;
        // ADR-084: Sync schedule observability
        sync_schedule: {
          timezone: string;
          sync_frequency_label: string;
          todays_windows: Array<{
            time: string;
            time_utc: string;
            status: "completed" | "failed" | "missed" | "upcoming" | "active";
          }>;
          next_sync_at: string | null;
        } | null;
      }>("/api/system/status"),

    // Lightweight endpoint for polling sync completion during pipeline runs
    getSyncTimestamps: () =>
      request<{
        timestamps: Record<string, string>;
      }>("/api/system/sync-timestamps"),
  },

  // Dashboard — ADR-122 Phase 5: project-first (no standalone agents)
  dashboard: {
    getSummary: () =>
      request<{
        projects: Array<{
          project_slug: string;
          title: string;
          type_key: string | null;
          purpose: string | null;
          updated_at: string | null;
          agents: Array<{
            id: string;
            title: string;
            status: string;
            origin: string;
            role: string;
            scope: string;
            sources: Array<{ provider?: string; resource_id?: string }>;
            last_run_at: string | null;
            next_run_at: string | null;
          }>;
        }>;
        connected_platforms: string[];
        attention: Array<{
          type: 'auto_paused' | 'failed';
          message: string;
          agent_id: string;
          project_slug?: string;
        }>;
      }>("/api/dashboard/summary"),
  },
};

export default api;
