/**
 * toolLabels — operator-facing spellings for lane tool verbs (2026-08-18).
 *
 * The stream and the reply footer used to print raw primitive names
 * ("Designer · WriteFile · ReadFile…") — the same internal-vocabulary leak the
 * artifact card fixed for the artifact half (LanePanel header, 2026-07-09:
 * "a lane that wrote a report rendered as `gemini-2.5-pro · WriteFile…`").
 * Verbs are named here in the member's language instead, in the two tenses the
 * transcript actually uses: `doing` while the turn streams, `did` in the
 * settled footer.
 *
 * The roster mirrors `api/services/lane_runner.py::lane_tool_names()` — the
 * five file verbs + LANE_SURFACE_EXTRA. An unknown name (a future roster
 * addition) degrades to a humanized spelling rather than leaking camelCase, so
 * this map can lag the roster without re-shipping the defect.
 */

const TOOL_LABELS: Record<string, { doing: string; did: string }> = {
  ReadFile: { doing: 'reading a file', did: 'read a file' },
  WriteFile: { doing: 'writing a file', did: 'wrote a file' },
  EditFile: { doing: 'revising a file', did: 'revised a file' },
  SearchFiles: { doing: 'searching files', did: 'searched files' },
  ListFiles: { doing: 'listing files', did: 'listed files' },
  QueryKnowledge: { doing: 'searching knowledge', did: 'searched knowledge' },
  WebSearch: { doing: 'searching the web', did: 'searched the web' },
  list_integrations: { doing: 'checking connections', did: 'checked connections' },
  GenerateImage: { doing: 'generating an image', did: 'generated an image' },
};

/** "WriteFile" → "write file", "list_integrations" → "list integrations". */
function humanize(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .toLowerCase();
}

/** Deduped, joined display line for a turn's tool calls. */
export function toolLabelLine(names: string[], form: 'doing' | 'did'): string {
  return Array.from(new Set(names))
    .map((n) => TOOL_LABELS[n]?.[form] ?? humanize(n))
    .join(' · ');
}
