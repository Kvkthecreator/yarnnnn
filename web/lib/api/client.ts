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
  WorkOutput,
  DeleteResponse,
  OnboardingStateResponse,
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

  // Work endpoints
  work: {
    listTickets: (projectId: string) =>
      request<WorkTicket[]>(`/api/work/projects/${projectId}/tickets`),
    createTicket: (projectId: string, data: WorkTicketCreate) =>
      request<WorkTicket>(`/api/work/projects/${projectId}/tickets`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    getTicket: (ticketId: string) =>
      request<WorkTicket & { outputs: WorkOutput[] }>(
        `/api/work/tickets/${ticketId}`
      ),
    execute: (ticketId: string) =>
      request<{ status: string }>(`/api/agents/tickets/${ticketId}/execute`, {
        method: "POST",
      }),
  },

  // Chat endpoints (streaming handled separately in useChat hook)
  chat: {
    send: (projectId: string, message: string) =>
      request<{ response: string }>(`/api/projects/${projectId}/chat`, {
        method: "POST",
        body: JSON.stringify({ message }),
      }),
    history: (projectId: string) =>
      request<Array<{ role: string; content: string }>>(
        `/api/projects/${projectId}/chat/history`
      ),
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
};

export default api;
