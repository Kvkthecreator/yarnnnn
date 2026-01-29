/**
 * YARNNN API Client
 * Typed fetch wrapper with Supabase auth
 */

import { createClient } from "@/lib/supabase/client";
import type {
  Project,
  ProjectCreate,
  ProjectWithCounts,
  Block,
  BlockCreate,
  BulkImportRequest,
  BulkImportResponse,
  ContextBundle,
  WorkTicket,
  WorkTicketCreate,
  WorkOutput,
  DeleteResponse,
  UserContext,
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
  // Project endpoints (workspace is auto-managed)
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

  // Context endpoints (blocks)
  context: {
    listBlocks: (projectId: string) =>
      request<Block[]>(`/api/context/projects/${projectId}/blocks`),
    createBlock: (projectId: string, data: BlockCreate) =>
      request<Block>(`/api/context/projects/${projectId}/blocks`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
    importBulk: (projectId: string, data: BulkImportRequest) =>
      request<BulkImportResponse>(
        `/api/context/projects/${projectId}/blocks/import`,
        {
          method: "POST",
          body: JSON.stringify(data),
        }
      ),
    deleteBlock: (blockId: string) =>
      request<DeleteResponse>(`/api/context/blocks/${blockId}`, {
        method: "DELETE",
      }),
    getBundle: (projectId: string) =>
      request<ContextBundle>(`/api/context/projects/${projectId}/context`),
  },

  // Work endpoints (TODO: implement when API routes ready)
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

  // User context endpoints (ADR-004 two-layer memory)
  userContext: {
    list: () => request<UserContext[]>("/api/context/user/context"),
    update: (itemId: string, data: { content?: string; importance?: number }) =>
      request<UserContext>(`/api/context/user/context/${itemId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    delete: (itemId: string) =>
      request<DeleteResponse>(`/api/context/user/context/${itemId}`, {
        method: "DELETE",
      }),
  },
};

export default api;
