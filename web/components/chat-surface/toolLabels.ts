/**
 * toolLabels — operator-facing spellings for lane tool verbs (2026-08-18;
 * re-cut 2026-08-25 for the stepped stream display).
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

/** A verb's two tenses, and whether it takes a subject in front of the place. */
type ToolLabel = {
  doing: string;
  did: string;
  /** Composed as `${withSubject} ${subject}` when the step carries a subject —
   *  "Reading" + "Documents/memo.md". Absent when naming a subject would read
   *  worse than the plain verb. */
  withSubject?: string;
};

const TOOL_LABELS: Record<string, ToolLabel> = {
  ReadFile: { doing: 'reading a file in your workspace', did: 'read a file', withSubject: 'reading' },
  WriteFile: { doing: 'writing a file in your workspace', did: 'wrote a file', withSubject: 'writing' },
  EditFile: { doing: 'revising a file in your workspace', did: 'revised a file', withSubject: 'revising' },
  // 2026-08-21 — the file-verb set is one set, whoever holds it. Named
  // explicitly rather than left to `humanize`: "deleting a file" is the one
  // verb a member most needs to read accurately in a streaming transcript.
  DeleteFile: { doing: 'deleting a file in your workspace', did: 'deleted a file', withSubject: 'deleting' },
  MoveFile: { doing: 'moving a file in your workspace', did: 'moved a file', withSubject: 'moving' },
  // 2026-08-21 — the FOLDER grain. Named "folder", never "files": a fan-out's
  // blast radius must read in the transcript as what it was. The count itself
  // rides in the verb's own result message ("19 moved to Trash · 2 stayed").
  DeleteFolder: { doing: 'deleting a folder in your workspace', did: 'deleted a folder', withSubject: 'deleting the folder' },
  MoveFolder: { doing: 'moving a folder in your workspace', did: 'moved a folder', withSubject: 'moving the folder' },
  // The inverse of the two deletes. "restoring" rather than "undeleting":
  // Trash is a place, and this is the Put Back beside it.
  Restore: { doing: 'restoring from Trash', did: 'restored from Trash', withSubject: 'restoring' },
  SearchFiles: { doing: 'searching your workspace', did: 'searched your workspace', withSubject: 'searching your workspace for' },
  ListFiles: { doing: 'listing files in your workspace', did: 'listed files', withSubject: 'listing' },
  QueryKnowledge: { doing: 'searching knowledge', did: 'searched knowledge', withSubject: 'searching knowledge for' },
  WebSearch: { doing: 'searching the web', did: 'searched the web', withSubject: 'searching the web for' },
  list_integrations: { doing: 'checking connections', did: 'checked connections' },
  GenerateImage: { doing: 'generating an image', did: 'generated an image' },

  // ADR-585 turn reach — the read-only platform surface a reach-bearing turn
  // holds. Un-named, these fell through `humanize` and printed
  // "platform slack get channel history" into a member's transcript: the exact
  // internal-vocabulary leak this file exists to prevent, reintroduced by a
  // roster the map had not caught up with. Named in the PLATFORM's own
  // vocabulary (channel, page, repo) because that is what the member sees on
  // the other side of the connection.
  platform_slack_list_channels: { doing: 'listing Slack channels', did: 'listed Slack channels' },
  platform_slack_get_channel_history: {
    doing: 'reading a Slack channel', did: 'read a Slack channel', withSubject: 'reading Slack',
  },
  platform_notion_search: {
    doing: 'searching Notion', did: 'searched Notion', withSubject: 'searching Notion for',
  },
  platform_notion_get_page: {
    doing: 'reading a Notion page', did: 'read a Notion page', withSubject: 'reading the Notion page',
  },
  platform_github_list_repos: { doing: 'listing GitHub repos', did: 'listed GitHub repos' },
  platform_github_get_issues: {
    doing: 'reading GitHub issues', did: 'read GitHub issues', withSubject: 'reading issues in',
  },
  platform_github_get_repo_metadata: {
    doing: 'reading a GitHub repo', did: 'read a GitHub repo', withSubject: 'reading',
  },
  platform_github_get_readme: {
    doing: 'reading a GitHub README', did: 'read a GitHub README', withSubject: 'reading the README of',
  },
  platform_github_get_releases: {
    doing: 'reading GitHub releases', did: 'read GitHub releases', withSubject: 'reading releases in',
  },
};

/** "WriteFile" → "write file", "list_integrations" → "list integrations". */
function humanize(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .toLowerCase();
}

/** Sentence case for a step row: only the first letter, so a path's own casing
 *  and a proper noun (Slack, Notion) both survive. */
function sentenceCase(s: string): string {
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

/** One streaming step's line: verb + subject when the server named one, the
 *  plain present-tense verb when it did not. */
export function toolStepLine(step: { name: string; subject?: string }): string {
  const label = TOOL_LABELS[step.name];
  if (step.subject && label?.withSubject) {
    return sentenceCase(`${label.withSubject} ${shortenSubject(step.subject)}`);
  }
  return sentenceCase(label?.doing ?? humanize(step.name));
}

/** Deduped, joined display line for a turn's tool calls. */
export function toolLabelLine(names: string[], form: 'doing' | 'did'): string {
  return Array.from(new Set(names))
    .map((n) => TOOL_LABELS[n]?.[form] ?? humanize(n))
    .join(' · ');
}
