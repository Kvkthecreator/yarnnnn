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
  WorkTicket,
  WorkTicketCreate,
  WorkOutput,
  DeleteResponse,
} from "@/types";

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

  // Document endpoints
  documents: {
    list: (projectId: string) =>
      request<Document[]>(`/api/context/projects/${projectId}/documents`),
    upload: async (projectId: string, file: File) => {
      const headers = await getAuthHeaders();
      delete (headers as Record<string, string>)["Content-Type"]; // Let browser set for FormData

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API_BASE_URL}/api/context/projects/${projectId}/documents`,
        {
          method: "POST",
          credentials: "include",
          headers,
          body: formData,
        }
      );

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new APIError(response.status, response.statusText, data);
      }

      return response.json();
    },
    get: (documentId: string) =>
      request<Document>(`/api/context/documents/${documentId}`),
    delete: (documentId: string) =>
      request<DeleteResponse>(`/api/context/documents/${documentId}`, {
        method: "DELETE",
      }),
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
};

export default api;
