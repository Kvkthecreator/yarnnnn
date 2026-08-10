// The `history` result shape (compose_history, api/services/mcp_composition.py).
// Kept in lockstep with the backend; the widget renders this and nothing more
// (ADR-372 D3 — no synthesis).

export interface HistoryRevision {
  authored_by: string | null; // operator | reviewer:<id> | yarnnn:mcp:<client> | agent:<slug> | system:<actor>
  when: string | null; // ISO timestamp
  change: string | null; // the revision message
  revision_id: string | null;
  diff: string | null; // unified-diff text vs the predecessor; null for the oldest
  cited_source?: boolean; // true when this revision belongs to a cited source's chain
  source_path?: string; // the cited source's path (present when cited_source)
}

export interface HistoryResult {
  success?: boolean;
  found?: boolean;
  reference?: string;
  path?: string;
  history?: HistoryRevision[]; // newest first; cited sources' chains follow
  returned?: number;
  explanation?: string;
}

// Provenance buckets → a stable color class. Keep in sync with provClass below.
export type ProvBucket = "operator" | "reviewer" | "mcp" | "agent" | "system";

export function provBucket(authoredBy: string | null | undefined): ProvBucket {
  const a = (authoredBy || "").toLowerCase();
  if (a.startsWith("operator")) return "operator";
  if (a.startsWith("reviewer")) return "reviewer";
  if (a.includes("mcp")) return "mcp"; // yarnnn:mcp:<client>
  if (a.startsWith("agent")) return "agent";
  return "system";
}
