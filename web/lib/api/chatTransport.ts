const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const CHAT_PROXY_PATH = "/api/chat-proxy";

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
  const directChatUrl = `${normalizedBase}/api/chat`;

  // Retry through same-origin Next route when direct cross-origin transport fails.
  if (isAbsoluteUrl(normalizedBase)) {
    return [directChatUrl, CHAT_PROXY_PATH];
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
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
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
