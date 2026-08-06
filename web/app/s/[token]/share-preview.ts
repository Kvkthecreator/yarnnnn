/**
 * The public share projection, fetched SERVER-SIDE — ADR-529 D3.
 *
 * The page that consumes this used to fetch in a `useEffect`, which meant every
 * reader that does not execute JavaScript (an LLM fetcher, a Slack/Notion
 * unfurler, any crawler) received `Loading…` and nothing else. Measured live
 * 2026-08-06: `GET /api/s/{token}` returned 200 with the full artifact while
 * the HTML carried a blank shell — and an LLM handed the link inferred a
 * PERMISSIONS REFUSAL from it. The link was public; it was simply unreadable.
 *
 * Shared by the page body and `generateMetadata` so one request shape serves
 * both; Next dedupes the two calls within a render pass.
 */

export type WalkEntry = {
  authored_by: string | null;
  when: string | null;
  change: string | null;
};

export type SharePreview = {
  workspace_name: string | null;
  artifact_path: string | null;
  label: string | null;
  role: string;
  status: string;
  artifact_name?: string | null;
  artifact_kind?: string | null;
  artifact_content?: string | null;
  truncated?: boolean;
  walk?: WalkEntry[];
  /** ADR-530 — the file's model-consumable projection (DP34). The browser
   *  renders `artifact_content` (html goes in the locked iframe); everything
   *  that is not a browser reads THIS. */
  artifact_text?: string | null;
  /** The honest marker when a format has no registered strategy yet — DP34's
   *  anti-silent-drop clause. Never accompanied by raw bytes. */
  artifact_note?: string | null;
};

/** What the server learned about the link — including the honest dark states. */
export type PreviewResult =
  | { kind: "ok"; preview: SharePreview }
  /** 404 (never existed) or 410 (revoked/expired) — ADR-513 D4: dark means dark. */
  | { kind: "gone"; message: string }
  /** The API was unreachable. Distinct from `gone`: the link may be perfectly good. */
  | { kind: "error" };

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** The artifact's display name — the API's name, the label, or the path leaf. */
export function artifactName(p: SharePreview): string | null {
  if (p.artifact_name) return p.artifact_name;
  if (p.label) return p.label;
  if (!p.artifact_path) return null;
  const seg = p.artifact_path.split("/").filter(Boolean).pop();
  return seg || p.artifact_path;
}

export async function fetchSharePreview(token: string): Promise<PreviewResult> {
  if (!token) return { kind: "gone", message: "This share link doesn't exist or has been revoked." };
  try {
    // `no-store`: a capability link must never be cached by an intermediary —
    // revocation has to be the end of it (ADR-513 D4). The same reason the API
    // sets Cache-Control: no-store on every exit, including the errors.
    const res = await fetch(`${API_BASE_URL}/api/s/${encodeURIComponent(token)}`, {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    if (res.status === 404 || res.status === 410) {
      return { kind: "gone", message: "This share link doesn't exist or has been revoked." };
    }
    if (!res.ok) return { kind: "error" };
    return { kind: "ok", preview: (await res.json()) as SharePreview };
  } catch {
    return { kind: "error" };
  }
}
