// The `recall` result shape (compose_recall, api/services/mcp_composition.py).
// The widget renders this and nothing more (ADR-372 D3 — no synthesis).

export interface RecallChunk {
  path: string;
  excerpt: string;
  last_updated: string | null;
  domain: string | null;
  source_tag: string | null; // provenance tag, e.g. mcp:Claude | reviewer:ai | operator
}

export interface RecallResult {
  success?: boolean;
  subject?: string;
  chunks?: RecallChunk[];
  total_matches?: number;
  returned?: number;
  explanation?: string;
}

// Recognize a recall result among arbitrary toolOutput (for the shared reader).
export function isRecallResult(v: Record<string, unknown>): boolean {
  return "chunks" in v || ("subject" in v && "returned" in v) || "explanation" in v;
}
