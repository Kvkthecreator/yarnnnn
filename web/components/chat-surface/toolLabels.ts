/**
 * toolLabels — operator-facing spellings for lane tool verbs (2026-08-18;
 * re-cut 2026-08-25 for the stepped stream display; moved into the catalogs
 * 2026-09-20, ADR-660).
 *
 * The stream and the reply footer used to print raw primitive names
 * ("Designer · WriteFile · ReadFile…") — the same internal-vocabulary leak the
 * artifact card fixed for the artifact half (LanePanel header, 2026-07-09:
 * "a lane that wrote a report rendered as `gemini-2.5-pro · WriteFile…`").
 * Verbs are named here in the member's language instead, in the two tenses the
 * transcript actually uses: `doing` while the turn streams, `did` in the
 * settled footer.
 *
 * ⭐ THE PLACE IS THE WORKSPACE, NEVER "YOUR COMPUTER". Where a verb needs to
 * name where it acts, it names the workspace — the shared, attributed commons
 * (ADR-373: the workspace is the binding unit and the outermost scope). A file
 * verb here does not touch the member's disk and must never read as if it did:
 * the whole claim of the product is that these acts land in a commons other
 * principals can see, with attribution. "on your computer" would be a
 * marketing-honesty defect in the transcript itself.
 *
 * ⭐ ADR-660 — this module is evaluated at import, before any member's language
 * is known, so it holds no words at all: it resolves a primitive name to a
 * catalog KEY plus its arguments, and the COMPONENT words it. Composing a
 * subject line by concatenation ("reading" + path) was also an English word
 * order; the catalog carries `withSubject` as a whole ICU message so Korean can
 * put the subject first (`{subject} 읽는 중`).
 *
 * The roster mirrors `api/services/lane_runner.py::lane_tool_names()` — the
 * file + folder verbs + LANE_SURFACE_EXTRA, plus the ADR-585 `turn_reach`
 * platform reads a reach-bearing turn holds. An unknown name (a future roster
 * addition) degrades to a humanized spelling rather than leaking camelCase, so
 * this map can lag the roster without re-shipping the defect.
 *
 * ⚠️ A SECOND, SEPARATE MAP EXISTS: `lib/utils.ts::TOOL_DISPLAY_NAMES` serves
 * the STEWARD rail's vocabulary (`InlineToolCall`), whose roster is the whole
 * primitives registry, not the lane surface. The two are deliberately not
 * merged here — ADR-441 D1's altitude seam is the reason the vocabularies are
 * disjoint — but they do disagree in spelling for shared names, which is worth
 * a pass of its own rather than a silent unification in a display change.
 */

/** The catalog namespace every key below lives under. */
export const TOOL_LABEL_NS = 'chat.tools';
/** ADR-662 D3 — what a desktop-app act changed; its own namespace, because
 *  `chat.tools` is the verb roster and a receipt is not a verb. */
export const RECEIPT_LABEL_NS = 'chat.receipts';

/**
 * Which verbs the catalog names, and which of them can take a subject. A name
 * absent from here has no catalog entry and degrades to `humanize`.
 *
 * `true` — the verb has a `withSubject` message (it reads well naming what it
 * acted on). `false` — naming a subject would read worse than the plain verb.
 */
const TOOL_VERBS: Record<string, boolean> = {
  ReadFile: true,
  WriteFile: true,
  EditFile: true,
  // 2026-08-21 — the file-verb set is one set, whoever holds it. Named
  // explicitly rather than left to `humanize`: "deleting a file" is the one
  // verb a member most needs to read accurately in a streaming transcript.
  DeleteFile: true,
  MoveFile: true,
  // 2026-08-21 — the FOLDER grain. Named "folder", never "files": a fan-out's
  // blast radius must read in the transcript as what it was. The count itself
  // rides in the verb's own result message ("19 moved to Trash · 2 stayed").
  DeleteFolder: true,
  MoveFolder: true,
  // The inverse of the two deletes. "restoring" rather than "undeleting":
  // Trash is a place, and this is the Put Back beside it.
  Restore: true,
  SearchFiles: true,
  ListFiles: true,
  QueryKnowledge: true,
  WebSearch: true,
  list_integrations: false,
  GenerateImage: false,

  // ADR-585 turn reach — the read-only platform surface a reach-bearing turn
  // holds. Un-named, these fell through `humanize` and printed
  // "platform slack get channel history" into a member's transcript: the exact
  // internal-vocabulary leak this file exists to prevent, reintroduced by a
  // roster the map had not caught up with. Named in the PLATFORM's own
  // vocabulary (channel, page, repo) because that is what the member sees on
  // the other side of the connection.
  platform_slack_list_channels: false,
  platform_slack_get_channel_history: true,
  platform_notion_search: true,
  platform_notion_get_page: true,
  platform_github_list_repos: false,
  platform_github_get_issues: true,
  platform_github_get_repo_metadata: true,
  platform_github_get_readme: true,
  platform_github_get_releases: true,

  // ADR-662 D14 — the desktop app's browser pane. Only BrowserOpen takes its
  // subject (the address); the others are worded from their RECEIPT once the
  // host has read the effect back (`toolStepRef`'s `record` arm), because
  // "pressing a button" says nothing and "Pressed “Sign in”" says what happened.
  BrowserOpen: true,
  BrowserRead: false,
  BrowserClick: false,
  BrowserFill: false,
  BrowserBack: false,
};

/** "WriteFile" → "write file", "list_integrations" → "list integrations". */
/** The acts the host reports (`src-tauri/src/hands/mod.rs`, `record.act`). */
const RECEIPT_ACTS = new Set(['opened', 'read', 'pressed', 'filled', 'back', 'failed', 'refused']);

function humanize(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .toLowerCase();
}

/** Sentence case for a step row: only the first letter, so a path's own casing
 *  and a proper noun (Slack, Notion) both survive. Korean has no letter case,
 *  so this is a no-op on a Hangul string by construction. */
export function sentenceCase(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** A workspace path renders WHOLE when it reasonably fits, and elides from the
 *  FRONT only when it does not — the tail is what identifies the file. The
 *  leading `/workspace` (and a bare `workspace/`) is dropped first: it is the
 *  root every path shares, so it costs width and carries no information.
 *
 *  ⚠️ Elide reluctantly. A first cut capped every path at its last two
 *  segments, which turned `reports/acme/summary.md` — a path that fits fine —
 *  into `…/acme/summary.md`, hiding the folder the member most needed to see.
 *  A query or prompt (no slash) is never touched: it is already the member's
 *  own words. */
function shortenSubject(subject: string): string {
  const path = subject.replace(/^\/?workspace\//, '');
  if (!path.includes('/')) return path;
  if (path.length <= 48) return path;
  const parts = path.split('/').filter(Boolean);
  return parts.length <= 2 ? path : `…/${parts.slice(-2).join('/')}`;
}

/** What a component needs to word one line: a catalog key relative to
 *  `TOOL_LABEL_NS` and its ICU arguments, or `fallback` when the verb has no
 *  catalog entry (an unknown name from a newer roster). */
export type ToolLabelRef =
  | { key: string; args?: Record<string, string>; fallback?: undefined; receipt?: boolean }
  | { key?: undefined; args?: undefined; fallback: string };

/** One streaming step's line: verb + subject when the server named one AND the
 *  verb reads well with one, the plain present-tense verb when it does not. */
export function toolStepRef(step: {
  name: string;
  subject?: string;
  record?: { act: string; subject: string; changed: boolean } | null;
}): ToolLabelRef {
  // ADR-662 D3 — an act the desktop app performed is worded from what it
  // CHANGED, read back by the host, in the member's language. A settled act
  // with no change says so: that is the receipt, not a failure to render one.
  if (step.record && RECEIPT_ACTS.has(step.record.act)) {
    const { act, subject, changed } = step.record;
    const unchanged = !changed && act !== 'read' && act !== 'opened';
    return {
      receipt: true,
      key: `${act}${unchanged ? 'Unchanged' : ''}`,
      args: { subject: subject.length > 60 ? `${subject.slice(0, 59)}…` : subject },
    };
  }
  const takesSubject = TOOL_VERBS[step.name];
  if (takesSubject === undefined) return { fallback: sentenceCase(humanize(step.name)) };
  if (step.subject && takesSubject) {
    return { key: `${step.name}.withSubject`, args: { subject: shortenSubject(step.subject) } };
  }
  return { key: `${step.name}.doing` };
}

/** The deduped set of refs for a turn's tool calls, in call order. The caller
 *  words each and joins them — joining worded strings is the component's job,
 *  so the separator is not baked into a key. */
export function toolLabelRefs(names: string[], form: 'doing' | 'did'): ToolLabelRef[] {
  return Array.from(new Set(names)).map((n) =>
    TOOL_VERBS[n] === undefined ? { fallback: humanize(n) } : { key: `${n}.${form}` },
  );
}
