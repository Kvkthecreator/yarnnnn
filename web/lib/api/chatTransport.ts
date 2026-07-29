import { getActiveWorkspaceId } from "./client";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const FEED_PROXY_PATH = "/api/feed-proxy";

function normalizeBaseUrl(url: string): string {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

function isAbsoluteUrl(url: string): boolean {
  return /^https?:\/\//i.test(url);
}

function isRetriableNetworkError(error: unknown): boolean {
  if (!(error instanceof Error)) return false;
  if (error.name === "AbortError") return false;

  const message = error.message.toLowerCase();
  return (
    error.name === "TypeError" ||
    message.includes("failed to fetch") ||
    message.includes("network") ||
    message.includes("load failed")
  );
}

function getChatUrlCandidates(): string[] {
  const normalizedBase = normalizeBaseUrl(API_BASE_URL);
  const directChatUrl = `${normalizedBase}/api/feed`;

  // Retry through same-origin Next route when direct cross-origin transport fails.
  if (isAbsoluteUrl(normalizedBase)) {
    return [directChatUrl, FEED_PROXY_PATH];
  }

  return [directChatUrl];
}

interface PostChatOptions {
  body: string;
  token?: string;
  signal?: AbortSignal;
}

export async function postChatWithFallback({
  body,
  token,
  signal,
}: PostChatOptions): Promise<Response> {
  const urls = getChatUrlCandidates();
  // X-Workspace-Id is NOT optional on a write path (ADR-373). This transport
  // hand-builds its headers instead of going through `getAuthHeaders()`, and
  // for that reason it silently omitted the binding — so a member acting in a
  // workspace they were GRANTED had their chat turns (and every file the turn
  // wrote, and every proposal it raised) land in their OWN workspace: the
  // server defaults to the owner workspace when the header is absent
  // (`services/supabase.py::get_user_client` — the fail-closed 403 only fires
  // when the header is PRESENT and invalid, so an omission is invisible).
  //
  // Worse than a plain mis-scope: chat HISTORY reads go through `request()`
  // and DO carry the header, so the member read one workspace's transcript
  // while writing into another's.
  //
  // Reuses the exported binding accessor rather than re-reading localStorage —
  // one source of truth for what "the acting workspace" is.
  const workspaceId = getActiveWorkspaceId();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(workspaceId ? { "X-Workspace-Id": workspaceId } : {}),
  };

  let lastError: unknown;

  for (let i = 0; i < urls.length; i += 1) {
    const url = urls[i];
    const isLastAttempt = i === urls.length - 1;

    try {
      return await fetch(url, {
        method: "POST",
        headers,
        body,
        credentials: "include",
        signal,
      });
    } catch (error) {
      lastError = error;
      if (isLastAttempt || !isRetriableNetworkError(error)) {
        throw error;
      }
      console.warn(
        `[chatTransport] direct chat request failed, retrying via proxy: ${url}`
      );
    }
  }

  throw lastError ?? new Error("Chat request failed");
}
