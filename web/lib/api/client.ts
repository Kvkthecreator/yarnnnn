/**
 * YARNNN API Client
 * ADR-005: Unified memory with embeddings
 */

import { createClient } from "@/lib/supabase/client";
import type {
  Project,
  ProjectCreate,
  ProjectWithCounts,
  Memory,
  MemoryCreate,
  MemoryUpdate,
  BulkImportRequest,
  BulkImportResponse,
  ContextBundle,
  Document,
  DocumentDetail,
  DocumentUploadResponse,
  DocumentDownloadResponse,
  DocumentListResponse,
  WorkTicket,
  WorkTicketCreate,
  WorkTicketDetail,
  WorkExecutionResponse,
  WorkListResponse,
  WorkUpdateRequest,
  WorkUpdateResponse,
  WorkDeleteResponse,
  DeleteResponse,
  OnboardingStateResponse,
  SubscriptionStatus,
  CheckoutResponse,
  PortalResponse,
  Deliverable,
  DeliverableCreate,
  DeliverableUpdate,
  DeliverableDetail,
  DeliverableVersion,
  VersionUpdate,
  DeliverableRunResponse,
  // ADR-031 Phase 6: Project Resources
  ProjectResource,
  ProjectResourceCreate,
  ResourceSuggestion,
  ContextSummaryItem,
} from "@/types";
import type {
  AdminOverviewStats,
  AdminMemoryStats,
  AdminDocumentStats,
  AdminChatStats,
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
  // Project endpoints
  projects: {
    list: () => request<Project[]>("/api/projects"),
    create: (data: ProjectCreate) =>
      request<Project>("/api/projects", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    get: (projectId: string) =>
      request<ProjectWithCounts>(`/api/projects/${projectId}`),

    // ADR-031 Phase 6: Project Resources
    resources: {
      // List resources linked to a project
      list: (projectId: string, platform?: string) => {
        const params = platform ? `?platform=${platform}` : "";
        return request<ProjectResource[]>(
          `/api/projects/${projectId}/resources${params}`
        );
      },

      // Add a resource to a project
      create: (projectId: string, data: ProjectResourceCreate) =>
        request<ProjectResource>(`/api/projects/${projectId}/resources`, {
          method: "POST",
          body: JSON.stringify(data),
        }),

      // Remove a resource from a project
      delete: (projectId: string, resourceId: string) =>
        request<{ status: string; message: string }>(
          `/api/projects/${projectId}/resources/${resourceId}`,
          { method: "DELETE" }
        ),

      // Auto-suggest resources for a project
      suggest: (projectId: string) =>
        request<ResourceSuggestion[]>(
          `/api/projects/${projectId}/resources/suggest`
        ),

      // Get cross-platform context summary
      contextSummary: (projectId: string, days?: number) => {
        const params = days ? `?days=${days}` : "";
        return request<ContextSummaryItem[]>(
          `/api/projects/${projectId}/context-summary${params}`
        );
      },
    },
  },

  // User memories (user-scoped, portable)
  userMemories: {
    list: () => request<Memory[]>("/api/context/user/memories"),
    create: (data: MemoryCreate) =>
      request<Memory>("/api/context/user/memories", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    importBulk: (data: BulkImportRequest) =>
      request<{ memories_extracted: number }>("/api/context/user/memories/import", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },

  // Project memories (project-scoped)
  projectMemories: {
    list: (projectId: string) =>
      request<Memory[]>(`/api/context/projects/${projectId}/memories`),
    create: (projectId: string, data: MemoryCreate) =>
      request<Memory>(`/api/context/projects/${projectId}/memories`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    importBulk: (projectId: string, data: BulkImportRequest) =>
      request<BulkImportResponse>(
        `/api/context/projects/${projectId}/memories/import`,
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      ),
  },

  // Memory management (works for both user and project memories)
  memories: {
    update: (memoryId: string, data: MemoryUpdate) =>
      request<Memory>(`/api/context/memories/${memoryId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (memoryId: string) =>
      request<DeleteResponse>(`/api/context/memories/${memoryId}`, {
        method: "DELETE",
      }),
  },

  // Context bundle (full context for a project)
  context: {
    getBundle: (projectId: string) =>
      request<ContextBundle>(`/api/context/projects/${projectId}/context`),
  },

  // Onboarding state
  onboarding: {
    getState: () =>
      request<OnboardingStateResponse>("/api/context/user/onboarding-state"),
  },

  // Document endpoints (ADR-008: Document Pipeline)
  documents: {
    // List user's documents (optionally filtered by project)
    list: (projectId?: string, status?: string) => {
      const params = new URLSearchParams();
      if (projectId) params.append("project_id", projectId);
      if (status) params.append("status", status);
      const query = params.toString();
      return request<DocumentListResponse>(
        `/api/documents${query ? `?${query}` : ""}`
      );
    },

    // Upload document (optionally scoped to project)
    upload: async (file: File, projectId?: string) => {
      const headers = await getAuthHeaders();
      delete (headers as Record<string, string>)["Content-Type"]; // Let browser set for FormData

      const formData = new FormData();
      formData.append("file", file);
      if (projectId) formData.append("project_id", projectId);

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

  // Work endpoints (ADR-009: Work and Agent Orchestration)
  work: {
    // List tickets for a project
    list: (projectId: string, status?: string) => {
      const params = status ? `?status=${status}` : "";
      return request<WorkTicket[]>(`/api/projects/${projectId}/work${params}`);
    },

    // Create and execute immediately (sync)
    create: (projectId: string, data: WorkTicketCreate) =>
      request<WorkExecutionResponse>(`/api/projects/${projectId}/work`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Create ticket for later execution (async)
    createAsync: (projectId: string, data: WorkTicketCreate) =>
      request<WorkTicket>(`/api/projects/${projectId}/work/async`, {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Get ticket with outputs
    get: (ticketId: string) =>
      request<WorkTicketDetail>(`/api/work/${ticketId}`),

    // Execute a pending ticket
    execute: (ticketId: string) =>
      request<WorkExecutionResponse>(`/api/work/${ticketId}/execute`, {
        method: "POST",
      }),

    // ADR-017: Unified Work Model endpoints
    // List all work (one-time and recurring) for current user
    listAll: (options?: {
      projectId?: string;
      activeOnly?: boolean;
      includeCompleted?: boolean;
      limit?: number;
    }) => {
      const params = new URLSearchParams();
      if (options?.projectId) params.append("project_id", options.projectId);
      if (options?.activeOnly) params.append("active_only", "true");
      if (options?.includeCompleted === false) params.append("include_completed", "false");
      if (options?.limit) params.append("limit", options.limit.toString());
      const query = params.toString();
      return request<WorkListResponse>(`/api/work${query ? `?${query}` : ""}`);
    },

    // Update work (pause/resume, change task, change frequency)
    update: (workId: string, data: WorkUpdateRequest) =>
      request<WorkUpdateResponse>(`/api/work/${workId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    // Delete work and all outputs
    delete: (workId: string) =>
      request<WorkDeleteResponse>(`/api/work/${workId}`, {
        method: "DELETE",
      }),
  },

  // Chat endpoints (streaming handled separately in useChat hook)
  chat: {
    send: (projectId: string, message: string) =>
      request<{ response: string }>(`/api/projects/${projectId}/chat`, {
        method: "POST",
        body: JSON.stringify({ message }),
      }),
    // Get global chat history (no project)
    globalHistory: (limit: number = 1) =>
      request<{
        sessions: Array<{
          id: string;
          created_at: string;
          messages: Array<{
            id: string;
            role: string;
            content: string;
            sequence_number: number;
            created_at: string;
          }>;
        }>;
      }>(`/api/chat/history?limit=${limit}`),
    // Get project chat history
    history: (projectId: string, limit: number = 1) =>
      request<{
        sessions: Array<{
          id: string;
          created_at: string;
          messages: Array<{
            id: string;
            role: string;
            content: string;
            sequence_number: number;
            created_at: string;
          }>;
        }>;
      }>(`/api/projects/${projectId}/chat/history?limit=${limit}`),
  },

  // Subscription endpoints (Lemon Squeezy)
  subscription: {
    getStatus: () => request<SubscriptionStatus>("/api/subscription/status"),

    createCheckout: (billingPeriod: "monthly" | "yearly" = "monthly") =>
      request<CheckoutResponse>("/api/subscription/checkout", {
        method: "POST",
        body: JSON.stringify({ billing_period: billingPeriod }),
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
  },

  // ADR-018: Deliverables endpoints
  deliverables: {
    // List user's deliverables
    list: (status?: string) => {
      const params = status ? `?status=${status}` : "";
      return request<Deliverable[]>(`/api/deliverables${params}`);
    },

    // Create a new deliverable
    create: (data: DeliverableCreate) =>
      request<Deliverable>("/api/deliverables", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    // Get deliverable with version history
    get: (deliverableId: string) =>
      request<DeliverableDetail>(`/api/deliverables/${deliverableId}`),

    // Update deliverable settings
    update: (deliverableId: string, data: DeliverableUpdate) =>
      request<Deliverable>(`/api/deliverables/${deliverableId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    // Archive deliverable
    delete: (deliverableId: string) =>
      request<{ success: boolean; message: string }>(
        `/api/deliverables/${deliverableId}`,
        { method: "DELETE" }
      ),

    // Trigger an ad-hoc run
    run: (deliverableId: string) =>
      request<DeliverableRunResponse>(`/api/deliverables/${deliverableId}/run`, {
        method: "POST",
      }),

    // List versions for a deliverable
    listVersions: (deliverableId: string, limit?: number) => {
      const params = limit ? `?limit=${limit}` : "";
      return request<DeliverableVersion[]>(
        `/api/deliverables/${deliverableId}/versions${params}`
      );
    },

    // Get a specific version
    getVersion: (deliverableId: string, versionId: string) =>
      request<DeliverableVersion>(
        `/api/deliverables/${deliverableId}/versions/${versionId}`
      ),

    // Update version (approve, reject, save edits)
    updateVersion: (
      deliverableId: string,
      versionId: string,
      data: VersionUpdate
    ) =>
      request<DeliverableVersion>(
        `/api/deliverables/${deliverableId}/versions/${versionId}`,
        {
          method: "PATCH",
          body: JSON.stringify(data),
        }
      ),
  },

  // Account management
  account: {
    // Notification preferences
    getNotificationPreferences: () =>
      request<{
        email_deliverable_ready: boolean;
        email_deliverable_failed: boolean;
        email_work_complete: boolean;
        email_weekly_digest: boolean;
      }>("/api/account/notification-preferences"),

    updateNotificationPreferences: (data: {
      email_deliverable_ready?: boolean;
      email_deliverable_failed?: boolean;
      email_work_complete?: boolean;
      email_weekly_digest?: boolean;
    }) =>
      request<{
        email_deliverable_ready: boolean;
        email_deliverable_failed: boolean;
        email_work_complete: boolean;
        email_weekly_digest: boolean;
      }>("/api/account/notification-preferences", {
        method: "PATCH",
        body: JSON.stringify(data),
      }),

    // Data & Privacy operations
    // Get stats for danger zone (counts of what will be affected)
    getDangerZoneStats: () =>
      request<{
        // Tier 1: Individual data types
        chat_sessions: number;
        memories: number;
        documents: number;
        work_tickets: number;
        // Content subtotals
        deliverables: number;
        deliverable_versions: number;
        work_outputs: number;
        // Integrations
        user_integrations: number;
        integration_import_jobs: number;
        export_logs: number;
        // Hierarchy
        projects: number;
        workspaces: number;
      }>("/api/account/danger-zone/stats"),

    // Tier 1: Selective Purge (individual data types)
    clearChatHistory: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/chat-history",
        { method: "DELETE" }
      ),

    clearMemories: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/memories",
        { method: "DELETE" }
      ),

    clearDocuments: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/documents",
        { method: "DELETE" }
      ),

    clearWork: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/work",
        { method: "DELETE" }
      ),

    // Tier 2: Category Reset (grouped deletions)
    clearContent: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/content",
        { method: "DELETE" }
      ),

    clearContext: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/context",
        { method: "DELETE" }
      ),

    clearIntegrations: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/integrations",
        { method: "DELETE" }
      ),

    // Legacy endpoint (backward compatibility)
    deleteAllDeliverables: () =>
      request<{ success: boolean; message: string; deleted: Record<string, number> }>(
        "/api/account/deliverables",
        { method: "DELETE" }
      ),

    // Tier 3: Full Actions (high impact)
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

  // ADR-025: Skills (slash commands)
  skills: {
    // List available skills for autocomplete/picker
    list: () =>
      request<{
        skills: Array<{
          name: string;
          description: string;
          command: string;
          tier: "core" | "beta";
          trigger_patterns: string[];
        }>;
        total: number;
      }>("/api/skills"),
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
    getAuthorizationUrl: (provider: string) =>
      request<{ authorization_url: string }>(
        `/api/integrations/${provider}/authorize`
      ),

    // Export to provider
    export: (
      provider: string,
      data: { deliverable_version_id: string; destination: Record<string, unknown> }
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
    getHistory: (deliverableId?: string) =>
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
        `/api/integrations/history${deliverableId ? `?deliverable_id=${deliverableId}` : ""}`
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
      provider: "slack" | "notion" | "gmail",
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
    getLandscape: (provider: "slack" | "notion" | "gmail", refresh?: boolean) =>
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

    // Update coverage state (mark as excluded or reset)
    updateCoverage: (
      provider: "slack" | "notion" | "gmail",
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
  },
};

export default api;
