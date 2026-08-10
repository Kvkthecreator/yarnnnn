// The `search` result shape (compose_search, api/services/mcp_composition.py).
// The widget renders this and nothing more (ADR-372 D3 — no synthesis).

export interface SearchMatch {
  path: string;
  reference: string; // yarnnn://workspace/… handle — open-able
  excerpt: string;
  last_updated: string | null;
  similarity?: number; // semantic path only; absent on BM25/list
}

export interface SearchResult {
  success?: boolean;
  query?: string;
  results?: SearchMatch[];
  total_matches?: number;
  returned?: number;
  confidence?: string; // high | ambiguous | weak | none — always present
  explanation?: string;
}

// Recognize a search result among arbitrary toolOutput (for the shared reader).
export function isSearchResult(v: Record<string, unknown>): boolean {
  return "results" in v || ("query" in v && "returned" in v) || "explanation" in v;
}
