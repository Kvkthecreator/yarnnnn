// The `search` result shape (compose_search, api/services/mcp_composition.py).
// The widget renders this and nothing more (ADR-372 D3 — no synthesis).

export interface SearchMatch {
  path: string;
  reference: string; // yarnnn://workspace/… handle — open-able
  excerpt: string;
  last_updated: string | null;
  similarity?: number; // semantic path only; absent on BM25/list
}
// NOTE: search results carry NO `authored_by` — `compose_search` does not return
// it (the QueryKnowledge rows would each need a display-resolution pass). So the
// cards below show no attribution chip, deliberately: rendering a principal the
// server never sent would be synthesis (ADR-372 D3). If per-result attribution
// is wanted, it is a SERVER change first — the widget cannot invent it.

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
