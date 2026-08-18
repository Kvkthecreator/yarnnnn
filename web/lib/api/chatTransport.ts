import { getActiveWorkspaceId, healStaleWorkspacePin, isStaleWorkspacePin } from "./client";

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
      const response = await fetch(url, {
        method: "POST",
        headers,
        body,
        credentials: "include",
        signal,
      });

      // ADR-499's self-heal reaches this transport too (2026-08-18).
      //
      // This path sends `X-Workspace-Id` (see above) but returns a raw
      // `Response`, so it never consulted the heal that `request()` performs:
      // a stale pin surfaced as an ordinary chat error ("Chat request failed:
      // 403"), with no clear, no retry and no reload. The member stayed pinned
      // to an unreachable workspace — and chat is exactly where they would sit
      // and retry — while every `request()` caller around them healed.
      //
      // Observed as the sibling of the 2026-08-18 lockout: a workspace the
      // member had just created was momentarily unreachable, and this
      // transport was the one surface that could not recover from it.
      //
      // The predicate and the reload guard are SHARED with `request()`, so the
      // two can never disagree about what a stale pin looks like, and a heal
      // in either place still produces exactly one navigation.
      if (response.status === 403) {
        // Read from a CLONE: the body must stay unconsumed for the caller,
        // which parses its own error detail (and streams it on success).
        let detail: unknown;
        try {
          detail = (await response.clone().json())?.detail;
        } catch {
          // Not JSON — cannot be the stale-pin shape; fall through untouched.
        }
        if (isStaleWorkspacePin(response.status, detail)) {
          healStaleWorkspacePin();
        }
      }

      return response;
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
