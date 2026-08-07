// The `open` result shape (server.py open_file → mcp_composition.compose_open).
// ADR-533 D4.
//
// NOTE ON SCOPE: this widget renders the file's IDENTITY (path, who holds the
// head, when, how many attributed revisions) — NOT its content. The content is
// what the host's own model reasons over and renders; duplicating it in an
// iframe would compete with the host at something the host does better. What a
// chat host CANNOT show is the attribution: that this exact version is someone's
// work, made at a time, with N revisions behind it. That is the widget's job.

export interface OpenRevision {
  revision_id?: string | null;
  authored_by?: string | null;
  created_at?: string | null;
  message?: string | null;
}

export interface OpenResult {
  found?: boolean;
  reference?: string;
  path?: string | null;
  content?: string | null;
  truncated?: boolean;
  authored_by?: string | null;
  last_updated?: string | null;
  history?: OpenRevision[];
  explanation?: string;
}

/** `found` is unique to `open` among the verbs that declare a schema. */
export function isOpenResult(v: Record<string, unknown>): boolean {
  return "found" in v && ("reference" in v || "path" in v);
}
