'use client';

/**
 * LanePanel — one chat lane's conversation body (ADR-411, implements
 * ADR-408 D6).
 *
 * A lane is a conversation with one colleague: an isolated thread whose
 * agent works the SHARED workspace through the file-verb tool surface.
 * This panel is deliberately simpler than the steward's ConversationPanel:
 * non-streaming turns (POST → JSON reply), no command picker, no surface
 * override — a lane is a working thread, not the OS terminal.
 *
 * ADR-412 D2/D3 (2026-07-06): relocated from the chat-drawer chrome
 * (shell/chrome/) to the Chat surface body — the drawer purified to the
 * steward; member conversations live in their windowed workbench.
 * Mechanics unchanged.
 *
 * ADR-441 D2 (2026-07-11): THE lane-thread renderer — one per member
 * conversation, frame-agnostic, mounted N times (the /chat workbench, the
 * Studio's left pane) behind the named `LaneMountSlots` contract below.
 * Deliberately NOT merged with the steward's ConversationPanel: the split is
 * a wire-protocol split (ADR-441 D1), not a styling preference — the steward
 * streams and reaches the OS, a member conversation does neither.
 *
 * ⚠️ The "Altitude 1/2" ordinals this header carried were RETIRED by ADR-460
 * D1 (see ChatSurface.tsx's header, §6.10d). The wire-protocol split above is
 * the real, surviving fact; the ladder was never it.
 *
 * The contract rendered here: the transcript is private to the lane; the
 * work lands in files. When a turn used tools, the reply footer names them
 * so the member sees the lane touched the commons.
 *
 * 2026-07-09 — THE ARTIFACT CARD. Naming the verb was not enough: a lane that
 * wrote a report rendered as `gemini-2.5-pro · WriteFile…` and the member never
 * saw what it made. The stream now carries the PATH of every landed
 * WriteFile/EditFile (`lane_runner.artifact_path_from`), and each one mounts
 * `ArtifactCard` → `FileBody` — the same viewer the Files surface uses. The
 * card renders and opens; it never edits (ADR-236: chat is the mutation
 * surface). Assistant text renders as markdown, as it always should have.
 *
 * 2026-08-18 — SCROLL POLICY + THE SPEECH/ARTIFACT BALANCE. Scrolling is
 * `useStickToBottom` (shared with ConversationPanel — one policy, two
 * transcripts): follow the bottom only while the reader is AT the bottom;
 * a reader who scrolled up is never yanked back, and the way down is the
 * JumpToLatest chip. The local scrollIntoView-per-render effect this replaces
 * force-scrolled on every streaming delta AND on every 15s out-of-band poll.
 * Companion polish, same session: the artifact card holds its tile posture
 * mid-stream and unfolds on turn end (the words stay primary while they
 * arrive), the poll resync is an identity no-op when the transcript is
 * unchanged, and tool verbs render via `toolLabels` — never raw primitive
 * names (the `WriteFile…` footer defect, second half).
 */

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { COPY_FEEDBACK_MS } from '@/contexts/FeedbackContext';
import { useAutoResize, COMPOSER_MAX_PX } from '@/hooks/useAutoResize';
import { useStickToBottom, JumpToLatest } from '@/hooks/useStickToBottom';
import {
  ArrowUp,
  Check,
  Copy,
  FileText,
  FolderOpen,
  ImageIcon,
  Loader2,
  Paperclip,
  Pencil,
  RefreshCw,
  Sparkles,
  Square,
  Wrench,
  X,
} from 'lucide-react';
import { WorkspacePickerModal } from '@/components/workspace/WorkspacePicker';
import { api } from '@/lib/api/client';
import { useCurrentFocus, focusToWire } from '@/lib/shell/useSurfaceFocus';
import { formatDaySeparator, formatAbsolute } from '@/lib/formatting';
import { cn } from '@/lib/utils';
import { CONVERSATION_COLUMN_PX } from '@/components/chat-surface/conversationColumn';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { AgentFace } from '@/components/agents/AgentFace';
import { MentionMenu, type MentionCandidate } from './MentionMenu';
import { ArtifactCard } from './ArtifactCard';
import { toolLabelLine } from './toolLabels';
import { StreamSteps, type StreamStep } from './StreamSteps';

/** Render a member's text with recognized `@handles` marked (ADR-492 D3).
 *
 * A mention is ADDRESSING METADATA that happens to live in authored content —
 * the server deliberately leaves the `@name` in the message rather than
 * stripping it (`services/addressing.py`), so the transcript keeps exactly what
 * was typed. But rendering it as undifferentiated prose hid the fact that the
 * turn was ROUTED: "@lisa can you hear me" looked identical to a sentence about
 * someone called Lisa.
 *
 * Only handles that resolve are marked. An unknown one stays plain, which makes
 * a typo visible as a typo — the same reason the server refuses to fuzzy-match:
 * silently styling `@lisaa` as a live mention would claim a delivery that never
 * happened. The grammar mirrors the server's `_MENTION`.
 */
function renderWithMentions(text: string, known: Set<string>): ReactNode {
  if (!text || !known.size || !text.includes('@')) return text;
  const out: ReactNode[] = [];
  const re = /(^|\s)@([\w-]+)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (!known.has(m[2].toLowerCase())) continue;
    const at = m.index + m[1].length;
    if (at > last) out.push(text.slice(last, at));
    // A CHIP, not a highlight. The mention is a routing act, and the member
    // should be able to see at a glance which turns were addressed — a tinted
    // word reads as emphasis, a bordered token reads as a thing.
    out.push(
      <span
        key={`${at}-${m[2]}`}
        className="inline-flex items-center rounded-md bg-background/20 ring-1 ring-current/25 px-1.5 py-px mx-px text-[0.9em] font-medium align-baseline"
      >
        @{m[2]}
      </span>,
    );
    last = at + m[2].length + 1;
  }
  if (!out.length) return text;
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/** Day label for a message's separator (local date). '' when no timestamp. */
function dayKey(ts?: string): string {
  if (!ts) return '';
  const d = new Date(ts);
  return Number.isNaN(d.getTime()) ? '' : d.toDateString();
}

/** A file this turn wrote or revised — the pointer the lane contract promises. */
interface LaneArtifact {
  path: string;
  verb?: string;
}

/** ADR-579 D7 — what a gesture door clicked, carried typed beside the intent.
 *  The operator words (`label`, 1-indexed pages at render) are the ADR-511 D3
 *  vocabulary; `verb` names the door. Never authority — the server renders it
 *  into the frame and stamps it on the row; the binding still decides reach. */
export interface SeedTarget {
  verb: 'ask' | 'rewrite' | 'check';
  path: string | null;
  blockId: string | null;
  label: string | null;
  excerpt: string | null;
  pageIndex: number | null;
  /** ADR-609 D2 — the selection's EXTENT, for prose. `excerpt` is a clipped
   *  PREFIX (120 chars at capture, 80 at render) and always has been: it
   *  names the target so the colleague can say it back. It cannot say where
   *  the selection ENDS, which is what an edit needs. These are the source
   *  offsets the canvas already reports, carried instead of discarded, so an
   *  anchored edit acts on exactly what the member highlighted.
   *
   *  Half-open `[start, end)`. Null on every non-prose gesture — a Slides
   *  block has `blockId`, which is the same address in that medium's terms. */
  range: { start: number; end: number } | null;
}

/** Wire form (snake_case, the focus precedent) — what goes up on Send and
 *  what the ADR-605-shaped stamp stores on the row. */
function seedToWire(t: SeedTarget) {
  return {
    verb: t.verb,
    path: t.path,
    block_id: t.blockId,
    label: t.label,
    excerpt: t.excerpt,
    page_index: t.pageIndex,
    // ADR-609 D2 — the extent rides beside the prefix, never inside it.
    range: t.range ? { start: t.range.start, end: t.range.end } : null,
  };
}

/** Read the stamp back off a persisted row's metadata. Best-effort: a row
 *  written before D7 (or a malformed stamp) renders as a plain turn. */
function seedFromMeta(raw: unknown): SeedTarget | undefined {
  if (!raw || typeof raw !== 'object') return undefined;
  const s = raw as Record<string, unknown>;
  const verb = s.verb;
  if (verb !== 'ask' && verb !== 'rewrite' && verb !== 'check') return undefined;
  return {
    verb,
    path: typeof s.path === 'string' ? s.path : null,
    blockId: typeof s.block_id === 'string' ? s.block_id : null,
    label: typeof s.label === 'string' ? s.label : null,
    excerpt: typeof s.excerpt === 'string' ? s.excerpt : null,
    pageIndex: typeof s.page_index === 'number' ? s.page_index : null,
    range: readRange(s.range),
  };
}

/** A persisted range stamp, or null. Best-effort like the rest of the stamp:
 *  a pre-609 row simply has no range and renders as a plain gesture. */
function readRange(raw: unknown): { start: number; end: number } | null {
  if (!raw || typeof raw !== 'object') return null;
  const r = raw as Record<string, unknown>;
  return typeof r.start === 'number' && typeof r.end === 'number'
    ? { start: r.start, end: r.end }
    : null;
}

/** The chip's noun for a seed target — shared by the composer chip and the
 *  transcript chip so a gesture reads identically before and after Send. */
function seedTargetNoun(t: SeedTarget): string {
  if (t.label === 'selection') return 'the selection';
  if (t.pageIndex != null && !t.blockId) return `${t.label || 'slide'} ${t.pageIndex + 1}`;
  return `the ${t.label || 'block'} block`;
}

interface LaneMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  tools_called?: string[];
  /** The stepped thread this turn drew while it worked — one entry per tool
   *  round, in order, each with the subject the server named (`tool_step`).
   *  Streaming-only: it is NOT persisted, so a reloaded transcript shows the
   *  settled `tools_called` footer instead. That asymmetry is deliberate —
   *  the steps are progress, and progress is over once the turn is. */
  steps?: StreamStep[];
  /** Persisted on the assistant row's metadata, so a reloaded lane keeps its cards. */
  artifacts?: LaneArtifact[];
  /** Phase-A attachments: what this user turn carried (metadata, chips). */
  attachments?: Array<{ path: string; kind: 'image' | 'file'; name?: string }>;
  /** ADR-579 D7 — the gesture this user turn carried (stamped metadata). */
  seed?: SeedTarget;
  /** Direct conversations (2+ humans, no agent): WHO wrote this user row.
   *  Absent on solo-lane rows — every user row there is the viewer's own. */
  authorPrincipalId?: string;
  /** WHICH Agent authored this assistant row (ADR-495 D3 addressing).
   *
   *  A turn is authored BY A PRINCIPAL — that is the whole model, and the
   *  species of the principal is not what decides how it renders. Before this
   *  field the transcript could only express "mine vs. the machine's": every
   *  reply, from every Agent, rendered as one anonymous grey column. With two
   *  Agents in a cast that is not a cosmetic gap — Lisa's answer and Thinker's
   *  answer were indistinguishable on reload.
   *
   *  Absent on rows written before addressing shipped, and on direct
   *  (agent-less) conversations — both fall back to the unattributed render,
   *  so no backfill is needed. */
  agentSlug?: string;
}

/** A composer attachment mid-flight: uploading → uploaded (path set) | failed. */
interface PendingAttachment {
  key: string;
  name: string;
  kind: 'image' | 'file';
  path?: string;
  uploading: boolean;
  error?: boolean;
}

/** Metadata `artifacts` is a bare path list on the wire; the verb rides the
 *  live stream only. Normalize both shapes to one. */
function toArtifacts(raw: unknown): LaneArtifact[] | undefined {
  if (!Array.isArray(raw) || raw.length === 0) return undefined;
  const out: LaneArtifact[] = [];
  for (const item of raw) {
    if (typeof item === 'string') out.push({ path: item });
    else if (item && typeof item === 'object' && typeof (item as LaneArtifact).path === 'string') {
      out.push(item as LaneArtifact);
    }
  }
  return out.length ? out : undefined;
}

/**
 * The lane mount-slots contract (ADR-441 D2) — how an embedding surface
 * configures THE lane-thread renderer. One renderer, N mounts (the /chat
 * workbench, the Studio's left pane); the mount owns its frame and declares
 * slots — it never reaches into the thread's messages or transport. A new
 * mount need is a new named slot here, never a surface-specific branch
 * inside LanePanel.
 */
export interface LaneMountSlots {
  /** Fires when a write LANDS mid-turn (and again from the terminal list), so
   *  the mount can refresh its view of a file this lane just authored — the
   *  Studio canvas reload (ADR-440). */
  onArtifactWrite?: (path: string) => void;
  /** Replace the default (lane-contract) empty state — teach the mount's act
   *  in the mount's own words. Absent → the /chat default renders (ADR-440). */
  emptyState?: ReactNode;
  /** Starter prompts, rendered as clickable chips while the transcript is
   *  empty; clicking one fills the composer (ADR-440). */
  suggestions?: string[];
  /** Composer seed: when `nonce` changes, `text` is set into (or appended to)
   *  the composer. Drives pointing + the insert menu (ADR-440 v1.1).
   *
   *  ADR-579 D7 — the TARGET rides typed, never flattened into the prose.
   *  A gesture door (Rewrite… / Check this… / Ask about this…) passes what
   *  was clicked as `target`; the pane holds it as a chip beside the
   *  composer (named, dismissible, metered marker visible), the intent text
   *  stays editable, and NOTHING fires until Send — at which point the
   *  target goes up the wire as `seed` and is stamped on the message row
   *  (the ADR-605 mentions-stamp shape). Text-only seeds (`target` absent)
   *  behave exactly as before. */
  composerSeed?: { text: string; nonce: number; target?: SeedTarget } | null;
  /** ADR-612 D4 — a turn carrying THIS mount's gesture started or ended.
   *
   *  The mount cannot infer this from the click: clicking a gesture door only
   *  SEEDS the composer (ADR-579 D7 — nothing fires until Send, and the member
   *  may edit the intent, or dismiss the chip, or never send at all). A door
   *  that says "working" at click time is claiming a turn that does not exist.
   *
   *  Fires `true` when a seeded turn actually goes up, and `false` when it
   *  settles — however it settles, including an error or a stop. */
  onSeededTurn?: (running: boolean) => void;
  /** How this mount renders an assistant turn's artifact writes (ADR-443):
   *   - `'card'` (default): the full ArtifactCard preview — the mount has no
   *     other view of the artifact (/chat).
   *   - `'link'`: a compact "wrote {file} →" citation line — the mount
   *     references the artifact but doesn't render it inline.
   *   - `'none'`: suppress entirely — the mount fully OWNS the artifact view,
   *     so an inline render would be a duplicate (Studio: the canvas IS the
   *     artifact view; the transcript stays pure conversation).
   *  The card-vs-suppress decision is a MOUNT concern (declared here), never a
   *  branch inside the renderer (ADR-441 D2). */
  artifactWrite?: 'card' | 'link' | 'none';
}

interface LanePanelProps extends LaneMountSlots {
  laneId: string;
  laneName: string;
  /** The ENGINE's label ("Claude Sonnet"). Used where the fact is genuinely
   *  about the engine — chiefly the vision refusal, which is a capability of
   *  the model and not of the colleague wearing it. */
  modelLabel: string;
  /** ADR-562 D5 — WHO is working, for the member to read: the resident's name
   *  ("Designer") when the lane carries one, else the engine label.
   *
   *  A SEPARATE prop rather than a re-pointed `modelLabel`, because the two
   *  facts diverge: "Designer is working…" is right, but "Designer cannot see
   *  images" is wrong — vision is the ENGINE's limit, and collapsing them
   *  would make a colleague answer for a model's capability. Defaults to
   *  `modelLabel`, so a caller that has no colleague reads exactly as before. */
  speakerLabel?: string;
  /** This conversation can receive turns the viewer did not cause — so they
   *  arrive out-of-band (they don't ride the viewer's stream) and the
   *  transcript must refresh on an interval.
   *
   *  RENAMED TWICE, and the history is the point. It was `isDirect`, which
   *  bundled "other humans are here" with "no Agent is here"; the 2026-07-30
   *  audit split those and renamed it `hasOtherHumans`, fixing a group-with-an-
   *  Agent that polled never. That rename fixed one half and froze the other:
   *  a SOLO-human conversation with two Agents also polls never, so an Agent
   *  turn triggered from another tab never arrives (2026-08-14).
   *
   *  The honest predicate is neither species — it is "is there any other
   *  principal in this cast?" */
  canReceiveOutOfBandTurns?: boolean;
  /** The viewer's principal id — the own-vs-other test for user rows. */
  viewerId?: string | null;
  /** principal_id → display label (email) for foreign user-row authorship. */
  principalLabels?: Record<string, string>;
  /** Everyone addressable in this conversation, viewer excluded — the '@'
   *  menu's roster (ADR-492 D3/ADR-605: agents route a turn, people route
   *  attention; `inCast: false` rows are add-doors). Empty (the default)
   *  simply means no menu opens. */
  mentionCandidates?: MentionCandidate[];
  /** G4 — picking a not-in-cast member from the '@' menu: the host opens
   *  the add-participant drill-in. */
  onMentionOutsider?: (c: MentionCandidate) => void;
  /** G4 — handles that should MARK in the transcript beyond the menu's
   *  roster: the VIEWER's own (candidates exclude the viewer, so without
   *  this the one chip that means "this is about me" is the one that never
   *  marked). */
  extraKnownHandles?: string[];
  /** Reports WHO an unaddressed message would go to (the ADR-492 D3 continuity
   *  rung), so the mount can mark it on the roster. Null when the cast has
   *  fewer than two Agents — then there is nothing it could have been instead.
   *  Derived here because the transcript lives here; a second derivation in the
   *  parent would be free to disagree with this one. */
  onDefaultResponderChange?: (slug: string | null) => void;
  /** agent slug → the face that answers under it (ADR-495 D3).
   *
   *  A turn is authored BY A PRINCIPAL, and the transcript resolves any
   *  principal — human or Agent — to a name and a face through this map and
   *  `principalLabels`. Passing a LOOKUP rather than a single `speakerLabel`
   *  string is the whole correction: identity is a fact about a MESSAGE, not
   *  about the lane, and a lane-level string cannot express two Agents. */
  agentFaces?: Record<string, { name: string; avatarUrl?: string }>;
  /** Phase-A hygiene: the turn auto-named a default-named lane (server truth
   *  rides the done frame) — the mount updates its list/header. */
  onLaneRenamed?: (name: string) => void;
  /** Phase-A attachments: may this lane's model receive images? (LANE_MODELS
   *  vision flag — the server guards regardless; this gates the affordance.) */
  visionCapable?: boolean;
  /**
   * ADR-514 D2.3 — workspace paths arriving by `reference` delivery ("Open
   * With → Chat"). They bind as composer chips exactly like the picker's own
   * output. Plural by nature: a reference is the one delivery a multi-selection
   * (or a folder) can have.
   */
  citePaths?: string[];
  /** Called once the cited paths have been bound, so the surface can clear the
   *  deep-link param (an open act, not durable window state). */
  onCiteConsumed?: () => void;
}

export function LanePanel({
  laneId,
  laneName,
  modelLabel,
  speakerLabel,
  canReceiveOutOfBandTurns = false,
  viewerId = null,
  principalLabels,
  agentFaces,
  mentionCandidates = [],
  onMentionOutsider,
  extraKnownHandles = [],
  onDefaultResponderChange,
  onArtifactWrite,
  onSeededTurn,
  emptyState,
  suggestions,
  composerSeed,
  artifactWrite = 'card',
  onLaneRenamed,
  visionCapable = true,
  citePaths,
  onCiteConsumed,
}: LanePanelProps) {
  // ADR-562 D5 — who the member reads as working. Falls back to the engine
  // label, so a mount with no colleague renders byte-identically to pre-562.
  const speaker = speakerLabel || modelLabel;
  const [messages, setMessages] = useState<LaneMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Phase-A turn controls: the in-flight stream's abort handle (stop), the
  // user message being edited (edit-and-resend), copy feedback.
  const abortRef = useRef<AbortController | null>(null);
  // ADR-522 D2 — what the member is looking at, from the shell. Held by ref so
  // the send callback stays stable: focus updates on every click and scroll
  // settle, and listing it as a dep would rebuild the turn machinery each time.
  const currentFocus = useCurrentFocus();
  const focusRef = useRef(currentFocus);
  focusRef.current = currentFocus;
  const [editing, setEditing] = useState<{ id: string; original: string } | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  // Phase-A attachments: composer chips (upload → send as turn refs).
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  // Attach-from-workspace (ADR-512 D6): a BIND — the chip carries an EXISTING
  // artifact's path (no upload, no copy); the turn references the one
  // attributed file, exactly like a lane-produced ArtifactCard in reverse.
  const [workspacePickOpen, setWorkspacePickOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  // THE scroll policy (2026-08-18, see header) — shared with ConversationPanel.
  const { containerRef, contentRef, pinned, scrollToBottom } = useStickToBottom();
  // The composer grows with what you're writing, then holds and scrolls — the
  // CLI gesture. `rows={1}` alone pins it at one line forever (a CSS max-h is
  // only a ceiling; nothing pushes the box up to it), so the height is written
  // from scrollHeight. Shared with the shell drawer's composer — one rule.
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useAutoResize(textareaRef, input);

  /** Bind an EXISTING workspace artifact as a chip (ADR-512 D6 — no upload,
   *  no copy; the reference is the attachment). */
  const attachWorkspaceFile = useCallback(
    (path: string) => {
      setWorkspacePickOpen(false);
      const name = path.split('/').filter(Boolean).pop() || path;
      const isImage = /\.(png|jpe?g|webp|gif)$/i.test(name);
      if (isImage && !visionCapable) {
        setError(`${modelLabel} cannot see images — attach documents instead.`);
        return;
      }
      setAttachments((prev) =>
        prev.some((a) => a.path === path)
          ? prev
          : [
              ...prev,
              {
                key: `ref-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
                name,
                kind: isImage ? 'image' : 'file',
                uploading: false,
                path,
              },
            ],
      );
    },
    [visionCapable, modelLabel],
  );

  // ADR-514 D2.3 — arrival by `reference` DELIVERY. "Open With → Chat" from the
  // Finder navigates here with the cited paths; opening a file with Chat means
  // the file arrives as CITED MATERIAL, not as chat's subject. It lands as the
  // same bind the composer's own picker produces (no upload, no copy) — which
  // is why reference delivery needed no new receiving contract.
  //
  // Consumed ONCE per set of paths: the ref guard keeps a re-render (or the
  // param lingering in the URL) from re-attaching what the operator removed.
  const citedOnce = useRef<string | null>(null);
  useEffect(() => {
    if (!citePaths?.length) return;
    // '\n', never '\0'. This joined on a literal NUL byte, which made `file`
    // classify this 47KB component as BINARY — so plain `grep` silently SKIPPED
    // the whole file. An audit for on-screen copy that lives right here (the
    // empty state) returned nothing four times before the cause was found.
    // Python gates use read_text() and were unaffected, so nothing was red;
    // the cost was purely that the file was invisible to shell tooling.
    const key = citePaths.join('\n');
    if (citedOnce.current === key) return;
    citedOnce.current = key;
    citePaths.forEach(attachWorkspaceFile);
    onCiteConsumed?.();
  }, [citePaths, attachWorkspaceFile, onCiteConsumed]);

  /** Upload files into the raw lane (ADR-395) and track them as chips. */
  const addFiles = useCallback(
    (files: File[]) => {
      for (const file of files) {
        const kind: 'image' | 'file' = file.type.startsWith('image/') ? 'image' : 'file';
        if (kind === 'image' && !visionCapable) {
          setError(`${modelLabel} cannot see images — attach documents instead.`);
          continue;
        }
        const key = `att-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        setAttachments((prev) => [
          ...prev,
          { key, name: file.name, kind, uploading: true },
        ]);
        api.documents
          .upload(file)
          .then((res) => {
            const item = res.results?.[0];
            setAttachments((prev) =>
              prev.map((a) =>
                a.key === key
                  ? item?.success && item.workspace_path
                    ? { ...a, uploading: false, path: item.workspace_path }
                    : { ...a, uploading: false, error: true }
                  : a,
              ),
            );
          })
          .catch(() =>
            setAttachments((prev) =>
              prev.map((a) => (a.key === key ? { ...a, uploading: false, error: true } : a)),
            ),
          );
      }
    },
    [modelLabel, visionCapable],
  );

  const mapMessages = (
    rows: Array<{
      id: string;
      role: 'user' | 'assistant';
      content: string;
      created_at: string;
      metadata: Record<string, unknown>;
    }>,
  ): LaneMessage[] =>
    rows.map((m) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      created_at: m.created_at,
      tools_called: (m.metadata?.tools_called as string[]) ?? undefined,
      artifacts: toArtifacts(m.metadata?.artifacts),
      attachments:
        (m.metadata?.attachments as LaneMessage['attachments']) ?? undefined,
      seed: seedFromMeta(m.metadata?.seed),
      authorPrincipalId:
        typeof m.metadata?.author_principal_id === 'string'
          ? (m.metadata.author_principal_id as string)
          : undefined,
      // The API has written this since addressing shipped; nothing read it,
      // so a reloaded multi-agent transcript rendered every reply anonymously.
      agentSlug:
        typeof m.metadata?.agent_slug === 'string'
          ? (m.metadata.agent_slug as string)
          : undefined,
    }));

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMessages([]);
    setError(null);
    api.lanes
      .messages(laneId)
      .then((res) => {
        if (cancelled) return;
        setMessages(mapMessages(res.messages));
      })
      .catch(() => !cancelled && setError('Could not load this lane.'))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [laneId]);

  /** Silent transcript resync — swaps optimistic local ids for DB ids (edit/
   *  regenerate need them) and picks up a server-persisted partial after a
   *  stop. The mount stays put (`key={laneId}` remounts on lane switch).
   *
   *  IDENTITY NO-OP when nothing changed (2026-08-18). The 15s out-of-band
   *  poll calls this on lanes that are usually quiet; unconditionally adopting
   *  the fetched array gave every row a new identity, which remounted every
   *  ArtifactCard (refetch + spinner flash) and re-fired anything keyed on the
   *  array. Same content → keep the same objects. */
  const resyncMessages = useCallback(async () => {
    try {
      const res = await api.lanes.messages(laneId);
      const next = mapMessages(res.messages);
      setMessages((prev) =>
        prev.length === next.length &&
        prev.every(
          (m, i) =>
            m.id === next[i].id &&
            m.content === next[i].content &&
            (m.artifacts?.length ?? 0) === (next[i].artifacts?.length ?? 0) &&
            (m.tools_called?.length ?? 0) === (next[i].tools_called?.length ?? 0),
        )
          ? prev
          : next,
      );
    } catch {
      /* non-fatal — the optimistic view stands */
    }
  }, [laneId]);

  // Turns that don't ride the viewer's stream arrive out-of-band, so refresh
  // on a slow interval while mounted. Paused mid-send so a resync never
  // clobbers the optimistic rows. (Realtime is the deferred RLS work —
  // session subscriptions are creator-scoped today.)
  //
  // THE GATE IS "CAN A TURN ARRIVE THAT I DIDN'T CAUSE?", and the answer is
  // yes for ANY other principal — not only humans. Under the previous
  // `hasOtherHumans` gate a solo-human conversation with two Agents polled
  // NEVER: an Agent reply triggered by anyone else (or by an addressed turn
  // from another tab) simply never arrived until the lane was remounted. The
  // 2026-07-30 audit fixed the mirror-image bug (a group WITH an Agent got no
  // polling) and left this half standing, because at the time only one Agent
  // could ever answer and only a human could ever be the other party.
  useEffect(() => {
    if (!canReceiveOutOfBandTurns || sending) return;
    const t = setInterval(() => void resyncMessages(), 15_000);
    return () => clearInterval(t);
  }, [canReceiveOutOfBandTurns, sending, resyncMessages]);

  // ── THE '@' GESTURE (ADR-492 D3) ──────────────────────────────────────
  // The run being typed after an '@', or null. Mirrors the CARET, not just the
  // text: a mention is only live while the caret sits inside its run, so
  // clicking away closes the menu without any extra bookkeeping.
  //
  // The grammar matches the server's (`services/addressing.py::_MENTION`) —
  // `[\w-]+` after a start-of-string-or-whitespace boundary. Keeping the two in
  // agreement is what stops the menu offering a completion the router would not
  // honour; an email address is not a mention on either side.
  const readMentionRun = useCallback((el: HTMLTextAreaElement | null) => {
    if (!el || el.selectionStart !== el.selectionEnd) return null;
    const caret = el.selectionStart;
    const upto = el.value.slice(0, caret);
    const m = /(?:^|\s)@([\w-]*)$/.exec(upto);
    if (!m) return null;
    return { query: m[1], start: caret - m[1].length - 1 };
  }, []);
  // Every spelling that resolves to someone here — slug AND display name, the
  // two the server matches on. Used to mark mentions in the transcript, so an
  // unrecognized handle stays visibly plain.
  const knownHandles = useMemo(() => {
    const s = new Set<string>();
    for (const c of mentionCandidates) {
      // ADR-605 — people mark too: a human mention now routes to their
      // attention surface, so the chip claims a delivery that happens.
      // Outsider rows are excluded: their mention routes nowhere, and a
      // chip on one would claim a delivery that never happened.
      if (c.inCast === false) continue;
      s.add(c.handle.toLowerCase());
      s.add(c.name.replace(/\s+/g, '').toLowerCase());
    }
    // G4 — the viewer's own handles: mentions OF the reader are the chips
    // that matter most, and the roster above deliberately excludes them.
    for (const h of extraKnownHandles) {
      if (h) s.add(h.toLowerCase());
    }
    return s;
  }, [mentionCandidates, extraKnownHandles]);
  // ── WHO ANSWERS NEXT (the floor) ──────────────────────────────────────
  // With several Agents present and no mention, the server continues with
  // whoever spoke last (`select_responder`'s `last_responder` rung). That rule
  // is defensible; SHIPPING IT INVISIBLY WAS NOT. The member had no way to see
  // who held the floor, no way to hand it back, and the rule lived only in a
  // Python docstring — the "remembered state, no clearing path" smell.
  //
  // Derived, never stored (2026-08-14, deliberately): the conversation's
  // default-recipient model is still being found, so this reads the state the
  // transcript already carries rather than committing a schema to a rule that
  // may change. `agentSlug` is on every assistant row, so the floor-holder is
  // just the last one to speak.
  const floorHolder = useMemo(() => {
    if (mentionCandidates.filter((c) => c.kind === 'agent').length < 2) return null;
    for (let i = messages.length - 1; i >= 0; i--) {
      const s = messages[i].agentSlug;
      if (s) return s;
    }
    return null;
  }, [messages, mentionCandidates]);
  const floorName = floorHolder
    ? agentFaces?.[floorHolder]?.name || floorHolder
    : null;
  // Reported UP rather than re-derived by the parent: the transcript lives
  // here, and two derivations of "who answers next" would be free to disagree.
  useEffect(() => {
    onDefaultResponderChange?.(floorHolder);
  }, [floorHolder, onDefaultResponderChange]);

  const [mention, setMention] = useState<{ query: string; start: number } | null>(null);
  const [mentionHighlight, setMentionHighlight] = useState(0);
  const mentionItemsRef = useRef<MentionCandidate[]>([]);
  const syncMention = useCallback(() => {
    setMention((prev) => {
      const next = readMentionRun(textareaRef.current);
      if (prev?.query === next?.query && prev?.start === next?.start) return prev;
      return next;
    });
  }, [readMentionRun]);
  useEffect(() => {
    if (!mention) setMentionHighlight(0);
  }, [mention?.start, mention]);

  /** Complete the run to a real handle. Writes `@handle ` and puts the caret
   *  after it, so the member keeps typing their sentence uninterrupted. */
  const pickMention = useCallback(
    (c: MentionCandidate) => {
      const el = textareaRef.current;
      if (!el || !mention) return;
      const before = input.slice(0, mention.start);
      const after = input.slice(el.selectionStart);
      const next = `${before}@${c.handle} ${after}`;
      setInput(next);
      setMention(null);
      requestAnimationFrame(() => {
        const pos = before.length + c.handle.length + 2;
        el.focus();
        el.setSelectionRange(pos, pos);
      });
    },
    [input, mention],
  );

  // ADR-579 D7 — the held gesture target: what the door clicked, waiting
  // beside the composer as a typed chip until Send (or ✕). This is the place
  // a typed turn lives between mount-slot arrival and send — the seam the
  // prefill-only mechanism never had.
  const [pendingSeed, setPendingSeed] = useState<SeedTarget | null>(null);

  // ADR-440 v1.1 — composer seeding (pointing + insert menu). Appends when
  // the member already typed something; replaces when the composer is empty.
  // ADR-579 D7: a target-carrying seed also arms the chip; a text-only seed
  // clears it (a fresh gesture replaces the last, and a plain seed is not a
  // gesture).
  useEffect(() => {
    if (!composerSeed?.text) return;
    setInput((cur) => (cur.trim() ? `${cur.replace(/\s*$/, ' ')}${composerSeed.text}` : composerSeed.text));
    setPendingSeed(composerSeed.target ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [composerSeed?.nonce]);

  /** The one streaming-turn runner — send, edit-and-resend, and regenerate
   *  share it (Phase-A turn controls). Optimistic transcript surgery up
   *  front, the shared handler set during, a silent resync after. */
  const runStream = useCallback(
    async (
      kind: 'send' | 'regenerate',
      opts: {
        content?: string;
        replaceFromMessageId?: string;
        attachments?: Array<{ path: string; kind: 'image' | 'file'; name?: string }>;
        /** ADR-579 D7 — the gesture target riding this send. */
        seed?: SeedTarget;
      } = {},
    ) => {
      if (sending) return;
      setError(null);
      setSending(true);
      const controller = new AbortController();
      abortRef.current = controller;

      const replyId = `local-r-${Date.now()}`;
      if (kind === 'send') {
        const userId = `local-${Date.now()}`;
        // Optimistic: (on edit) truncate from the edited row, then the user
        // row + an empty assistant row the stream fills in place.
        setMessages((prev) => {
          let base = prev;
          if (opts.replaceFromMessageId) {
            const idx = base.findIndex((m) => m.id === opts.replaceFromMessageId);
            if (idx >= 0) base = base.slice(0, idx);
          }
          return [
            ...base,
            {
              id: userId,
              role: 'user',
              content: opts.content ?? '',
              attachments: opts.attachments,
              seed: opts.seed,
            },
            { id: replyId, role: 'assistant', content: '' },
          ];
        });
      } else {
        // Regenerate: drop the tail after the last user row, add the placeholder.
        setMessages((prev) => {
          let lastUser = -1;
          for (let i = prev.length - 1; i >= 0; i--) {
            if (prev[i].role === 'user') {
              lastUser = i;
              break;
            }
          }
          if (lastUser < 0) return prev;
          return [...prev.slice(0, lastUser + 1), { id: replyId, role: 'assistant', content: '' }];
        });
      }
      // The member's own act always reveals itself — sending re-pins the view
      // (the one growth that overrides a scrolled-up reading position).
      scrollToBottom();

      const appendDelta = (text: string) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === replyId ? { ...m, content: m.content + text } : m)),
        );

      let sawDelta = false;
      const dropEmptyPlaceholder = () =>
        setMessages((prev) =>
          prev.filter((m) => !(m.id === replyId && !m.content && !m.artifacts?.length)),
        );
      // WHO, before WHAT — the frame arrives ahead of the first delta, so the
      // spinner names the colleague answering instead of the lane's engine.
      const stampSpeaker = (agentSlug: string) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === replyId ? { ...m, agentSlug } : m)),
        );
      const handlers = {
        onDelta: (text: string) => {
          sawDelta = true;
          appendDelta(text);
        },
        onSpeaker: ({ agent_slug }: { agent_slug: string }) => stampSpeaker(agent_slug),
        onTool: (step: { name: string; subject?: string }) =>
          setMessages((prev) =>
            prev.map((m) =>
              m.id === replyId
                ? {
                    ...m,
                    tools_called: [...(m.tools_called ?? []), step.name],
                    steps: [...(m.steps ?? []), step],
                  }
                : m,
            ),
          ),
        // A write landed. Show the file as soon as it exists — mid-turn, before
        // the model has finished narrating it.
        onArtifact: ({ path, verb }: { path: string; verb: string }) => {
          onArtifactWrite?.(path);
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== replyId) return m;
              const existing = m.artifacts ?? [];
              if (existing.some((a) => a.path === path)) return m;
              return { ...m, artifacts: [...existing, { path, verb }] };
            }),
          );
        },
        onDone: ({
          tools_called,
          artifacts,
          agent_slug,
          lane_name,
          direct,
        }: {
          rounds: number;
          tools_called: string[];
          artifacts: string[];
          agent_slug?: string;
          lane_name?: string;
          direct?: boolean;
        }) => {
          // Phase-A hygiene: the server auto-named this lane on first turn.
          if (lane_name) onLaneRenamed?.(lane_name);
          // Belt-and-braces for a turn that emitted no delta (tool-only), or a
          // reader that joined after the speaker frame went by.
          if (agent_slug) stampSpeaker(agent_slug);
          // A direct-conversation turn is a broadcast — there is no reply, so
          // the placeholder goes away rather than becoming "[no reply]".
          if (direct) {
            dropEmptyPlaceholder();
            return;
          }
          if (tools_called?.length) {
            setMessages((prev) =>
              prev.map((m) => (m.id === replyId ? { ...m, tools_called } : m)),
            );
          }
          // The terminal list is authoritative (it survives a dropped frame).
          // Union by path, keeping the streamed entries first — they carry the
          // verb, which the terminal list does not.
          const finalArtifacts = toArtifacts(artifacts);
          finalArtifacts?.forEach((a) => onArtifactWrite?.(a.path));
          if (finalArtifacts) {
            setMessages((prev) =>
              prev.map((m) => {
                if (m.id !== replyId) return m;
                const seen = m.artifacts ?? [];
                const merged = [
                  ...seen,
                  ...finalArtifacts.filter((a) => !seen.some((s) => s.path === a.path)),
                ];
                return { ...m, artifacts: merged };
              }),
            );
          }
          // A turn that streamed no text shows a marker — UNLESS it produced an
          // artifact, in which case the card is the reply and a "[no reply]"
          // bubble above it would be a lie.
          if (!sawDelta && !finalArtifacts) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === replyId && !m.content ? { ...m, content: '[no reply]' } : m,
              ),
            );
          }
        },
        onError: (message: string) => {
          setError(message || 'The lane turn failed — try again.');
          // Papercut fix: preserve the user's text so it isn't lost.
          if (kind === 'send' && opts.content) setInput((cur) => cur || opts.content!);
          dropEmptyPlaceholder();
        },
      };

      try {
        if (kind === 'send') {
          await api.lanes.sendStream(laneId, opts.content ?? '', handlers, {
            signal: controller.signal,
            replaceFromMessageId: opts.replaceFromMessageId,
            attachments: opts.attachments,
            seed: opts.seed ? seedToWire(opts.seed) : undefined,
            // ADR-522 D2: what the member is looking at, read at SEND time —
            // focus is volatile (it changes between turns and within one), so
            // the reading that matters is the one at the moment they ask.
            //
            // Read from the shell, NOT declared as a mount slot: focus is
            // window-manager state (the foregrounded app's declaration), so a
            // slot would make every mount re-plumb the same value. The ADR-441
            // D2 rule is about the mount's FRAME, and this isn't one.
            focus: focusRef.current ? focusToWire(focusRef.current) : undefined,
          });
        } else {
          await api.lanes.regenerateStream(laneId, handlers, {
            signal: controller.signal,
          });
        }
      } catch {
        setError('The lane turn failed — try again.');
        if (kind === 'send' && opts.content) setInput((cur) => cur || opts.content!);
        dropEmptyPlaceholder();
      } finally {
        const stopped = controller.signal.aborted;
        abortRef.current = null;
        setSending(false);
        // ADR-612 D4 — the seeded turn has settled, however it settled.
        if (opts.seed) onSeededTurn?.(false);
        if (stopped) {
          // Stopped: drop a text-less placeholder, then resync once the server
          // has persisted the partial (it does so on disconnect — give it a beat).
          dropEmptyPlaceholder();
          setTimeout(() => void resyncMessages(), 600);
        } else {
          void resyncMessages();
        }
      }
    },
    [laneId, sending, onArtifactWrite, onSeededTurn, onLaneRenamed, resyncMessages, scrollToBottom],
  );

  const send = useCallback(async () => {
    const content = input.trim();
    if (!content || sending) return;
    // Attachments still uploading hold the send (a ref without a path would
    // silently drop); failed ones are skipped.
    if (attachments.some((a) => a.uploading)) return;
    const ready = attachments
      .filter((a) => a.path && !a.error)
      .map((a) => ({ path: a.path!, kind: a.kind, name: a.name }));
    setInput('');
    setAttachments([]);
    const replaceFromMessageId = editing?.id;
    setEditing(null);
    // ADR-579 D7 — the held gesture fires WITH the send, then clears; a
    // gesture is one turn's target, never a sticky mode.
    const seed = pendingSeed ?? undefined;
    setPendingSeed(null);
    if (seed) onSeededTurn?.(true);
    await runStream('send', {
      content,
      replaceFromMessageId,
      attachments: ready.length ? ready : undefined,
      seed,
    });
  }, [input, sending, editing, attachments, runStream, pendingSeed, onSeededTurn]);

  /** Phase-A turn controls: stop — abort the stream; the server persists the
   *  partial reply (any writes that landed stand — the no-rewind rule). */
  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const startEdit = useCallback((m: LaneMessage) => {
    setEditing({ id: m.id, original: m.content });
    setInput(m.content);
  }, []);

  const cancelEdit = useCallback(() => {
    setEditing(null);
    setInput('');
  }, []);

  const copyMessage = useCallback((m: LaneMessage) => {
    void navigator.clipboard?.writeText(m.content).then(() => {
      setCopiedId(m.id);
      setTimeout(() => setCopiedId((cur) => (cur === m.id ? null : cur)), COPY_FEEDBACK_MS);
    });
  }, []);

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      {/* ADR-507: the "Keep this" (settle) act is DELETED. The pipeline it was
          the middle of (think → settle → make) is retired for think ⇄ make, and
          a member who wants a conversation kept now simply asks — the lane's
          WriteFile + the conventions' placement/citation/format teaching absorb
          it, with no dedicated button, route or metered verb. */}
      {/* `relative` wrapper: the scroll container inside, the JumpToLatest
          chip floating over its bottom edge. The content wrapper is the
          ResizeObserver target — transcript growth (deltas, cards finishing
          their load, diagrams rendering) is what the follow rule watches. */}
      <div className="relative flex-1 min-h-0">
        <div ref={containerRef} className="h-full overflow-y-auto px-3 py-3">
          <div
            ref={contentRef}
            className="mx-auto w-full space-y-3"
            style={{ maxWidth: CONVERSATION_COLUMN_PX }}
          >
        {loading && (
          <div className="text-xs text-muted-foreground py-6 text-center">
            Loading {laneName}…
          </div>
        )}
        {!loading && messages.length === 0 && (
          <div className="py-6 px-4 space-y-3">
            {emptyState ?? (
              <div className="text-xs text-muted-foreground text-center space-y-1">
                {/* The colleague names the conversation; the ATTRIBUTION line
                    below stays on the engine — "you via {model}" is the ledger
                    fact (ADR-460 D2: the face is an Agent, the fact is your
                    hands), and a name must never be shown where a receipt is
                    meant. */}
                <p className="font-medium text-foreground/80">{laneName} · {speaker}</p>
                <p>
                  This conversation is private to this lane. The work it produces
                  lands in the shared workspace files, attributed to you via{' '}
                  {modelLabel}.
                </p>
              </div>
            )}
            {suggestions && suggestions.length > 0 && (
              <div className="flex flex-col items-stretch gap-1.5">
                {suggestions.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => setInput(s)}
                    className="rounded-lg border border-border px-3 py-2 text-left text-xs text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        {messages.map((m, i) => {
          // Session legibility: a day-separator when the calendar day changes
          // (ADR-412 D2). Reloaded lanes read across sessions, not as one blob.
          const prevDay = i > 0 ? dayKey(messages[i - 1].created_at) : '';
          const thisDay = dayKey(m.created_at);
          const showDay = thisDay !== '' && thisDay !== prevDay;
          const isLast = i === messages.length - 1;
          // ── AUTHORSHIP ────────────────────────────────────────────────
          // ONE model for every turn: a message is authored by a PRINCIPAL,
          // and the principal's species is not what decides how it renders.
          //
          // THE DEFECT THIS REPLACES (operator-observed 2026-08-13). `foreign`
          // used to require `role === 'user'`, so a *human* could be someone
          // else but an *assistant* was always "the machine" — one anonymous
          // grey column. That was fine while exactly one Agent could reply;
          // with addressing (ADR-495 D3) Lisa's answer and Thinker's answer
          // rendered identically, and consecutive replies from DIFFERENT
          // Agents even grouped into one visual run (`authorPrincipalId` is
          // undefined on both, and `undefined !== undefined` is false).
          //
          // It was the same species law ADR-495 stripped out of the substrate,
          // still living in the renderer: `conversation_cast.py` is
          // species-blind; this was not.
          //
          // `authorKey` identifies the speaker for grouping; `attributed`
          // means "someone other than the viewer, who we can name".
          const isOwn = m.role === 'user' && (!m.authorPrincipalId || m.authorPrincipalId === viewerId);
          const authorKey = m.role === 'assistant'
            ? `agent:${m.agentSlug ?? ''}`
            : `human:${m.authorPrincipalId ?? 'self'}`;
          const agentFace = m.agentSlug ? agentFaces?.[m.agentSlug] : undefined;
          const authorLabel = m.role === 'assistant'
            ? agentFace?.name || m.agentSlug || null
            : isOwn
              ? null
              : principalLabels?.[m.authorPrincipalId!] ||
                'A member';
          // A row gets the gutter + name when we can say WHO spoke and it is
          // not the viewer. An unattributed assistant row (pre-addressing
          // history, or a direct conversation) keeps exactly its old look.
          const attributed = !isOwn && !!authorLabel;
          // Consecutive-run grouping (the conventional messaging shape): a run
          // of turns from the SAME author shows the face + name once, at the
          // top. Keyed on the AUTHOR now, not the role — so Lisa-then-Thinker
          // is two runs, as it reads to a human.
          const prev = i > 0 ? messages[i - 1] : null;
          const prevKey = prev
            ? prev.role === 'assistant'
              ? `agent:${prev.agentSlug ?? ''}`
              : `human:${prev.authorPrincipalId ?? 'self'}`
            : null;
          const startsRun = !prev || prevKey !== authorKey || showDay;
          return (
            <div key={m.id} className="group">
              {showDay && (
                <div className="flex items-center gap-2 my-3">
                  <div className="flex-1 h-px bg-border" />
                  <span
                    className="text-[10px] text-muted-foreground/70 tracking-wide"
                    title={formatAbsolute(m.created_at)}
                  >
                    {formatDaySeparator(m.created_at)}
                  </span>
                  <div className="flex-1 h-px bg-border" />
                </div>
              )}
              {/* The bubble is speech. An artifact is not speech — it renders
                  below, at row width, outside the bubble (ADR-236: render +
                  open, never edit). A tool-only turn shows only the card. */}
              {/* An attributed row's author name sits ABOVE the bubble,
                  indented past the avatar gutter, and only at the top of a run
                  — the conventional grouping. Its own row rather than a
                  wrapper, so the bubble's own layout below is untouched. */}
              {attributed && startsRun && (
                <span className="block pl-[1.875rem] pb-0.5 text-[10px] text-muted-foreground">
                  {authorLabel}
                </span>
              )}
              {/* THE STEPPED THREAD — above the bubble, and deliberately NOT
                  gated on `!m.content`. A tool called after the reply began
                  narrating used to be invisible until the turn settled; the
                  steps now stay put and keep accruing under the narration.
                  The last one spins while the turn runs (`sending` + this being
                  the trailing row); when it settles they all read as done. */}
              {m.role === 'assistant' && m.steps && m.steps.length > 0 && (
                <StreamSteps
                  steps={m.steps}
                  running={sending && i === messages.length - 1}
                  className={cn('mb-1', attributed && 'pl-[1.875rem]')}
                />
              )}
              {(m.content || m.role === 'user' || !m.artifacts?.length) && (
                <div
                  className={cn(
                    'flex',
                    isOwn ? 'justify-end' : 'justify-start',
                    // An attributed row gets an avatar GUTTER: the face on the
                    // left, the bubble beside it. Continuation rows keep the
                    // gutter width (an empty span) so their bubbles stay
                    // aligned under the first — the face appears once per run.
                    attributed && 'items-end gap-1.5',
                  )}
                >
                  {attributed && (
                    <span className="w-6 shrink-0">
                      {startsRun && (
                        <AgentFace
                          name={authorLabel || '?'}
                          avatarUrl={agentFace?.avatarUrl}
                          size="sm"
                        />
                      )}
                    </span>
                  )}
                  <div
                    title={m.created_at ? formatAbsolute(m.created_at) : undefined}
                    className={cn(
                      'max-w-[85%] rounded-lg px-3 py-2 text-sm break-words',
                      isOwn
                        ? 'bg-primary text-primary-foreground whitespace-pre-wrap'
                        : attributed && m.role === 'user'
                          ? 'bg-muted text-foreground whitespace-pre-wrap border border-border/60'
                          : 'bg-muted text-foreground',
                    )}
                  >
                    {/* Streaming: an empty assistant bubble shows a live indicator
                        until the first delta lands, then fills token-by-token. */}
                    {m.role === 'assistant' && !m.content ? (
                      <span className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        {/* Per-MESSAGE speaker (ADR-495 D3). The lane-level
                            `speaker` is the fallback for a lane that has no
                            cast; once the SSE speaker frame lands, the row
                            names the colleague actually answering rather than
                            the engine behind them. */}
                        {/* Verbs in the member's language (`toolLabels`) —
                            raw primitive names are internal vocabulary. */}
                        {/* The VERBS moved out to the stepped thread above,
                            which names each one with its subject and survives
                            the first token. This line is now only WHO — so the
                            two never restate each other, and a turn mid-tool
                            reads as "Lisa is working…" beneath a thread that
                            says exactly what she is doing. */}
                        {`${authorLabel || speaker} is working…`}
                      </span>
                    ) : m.role === 'assistant' ? (
                      // 2026-07-09: the lane's reply is markdown, like every
                      // other model reply in the product. It rendered as raw
                      // text for no reason other than that LanePanel was a
                      // reimplementation.
                      // ADR-570 D6 (ADR-398 D3 reaching this surface): a
                      // named workspace path in a reply is a link into Files
                      // — the first hop of the connector round-trip.
                      <div className="prose prose-sm max-w-none dark:prose-invert prose-p:my-1.5 prose-pre:my-2">
                        <MarkdownRenderer content={m.content} linkifySubstrate />
                      </div>
                    ) : (
                      renderWithMentions(m.content, knownHandles)
                    )}
                    {/* ADR-579 D7 — the typed turn in the transcript: the
                        gesture this send carried, read off the row's stamp,
                        so what-was-clicked stays legible after the fact. */}
                    {m.role === 'user' && m.seed && (
                      <div className="mt-1.5 pt-1.5 border-t border-primary-foreground/20">
                        <span className="inline-flex items-center gap-1 rounded bg-primary-foreground/15 px-1.5 py-0.5 text-[10px]">
                          <Sparkles className="w-3 h-3" />
                          <span className="capitalize">{m.seed.verb}</span>
                          <span>·</span>
                          <span className="truncate max-w-[200px]">{seedTargetNoun(m.seed)}</span>
                        </span>
                      </div>
                    )}
                    {/* Phase-A attachments: what this user turn carried. */}
                    {m.role === 'user' && m.attachments && m.attachments.length > 0 && (
                      <div className="mt-1.5 pt-1.5 border-t border-primary-foreground/20 flex flex-wrap gap-1">
                        {m.attachments.map((a) => (
                          <span
                            key={a.path}
                            className="inline-flex items-center gap-1 rounded bg-primary-foreground/15 px-1.5 py-0.5 text-[10px]"
                          >
                            {a.kind === 'image' ? (
                              <ImageIcon className="w-3 h-3" />
                            ) : (
                              <FileText className="w-3 h-3" />
                            )}
                            <span className="truncate max-w-[140px]">
                              {a.name || a.path.split('/').pop()}
                            </span>
                          </span>
                        ))}
                      </div>
                    )}
                    {m.content && m.tools_called && m.tools_called.length > 0 && (
                      <div className="mt-1.5 pt-1.5 border-t border-border/40 flex items-center gap-1 text-[10px] text-muted-foreground">
                        <Wrench className="w-3 h-3" />
                        {toolLabelLine(m.tools_called, 'did')}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Phase-A turn controls: hover actions under the bubble — copy
                  everywhere; edit-and-resend on persisted user rows; regenerate
                  on the trailing assistant row. Hidden mid-stream. */}
              {!sending && m.content && (
                <div
                  className={cn(
                    'flex gap-0.5 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity',
                    isOwn ? 'justify-end' : 'justify-start',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => copyMessage(m)}
                    className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                    aria-label="Copy message"
                    title="Copy"
                  >
                    {copiedId === m.id ? (
                      <Check className="w-3 h-3" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                  {isOwn && !m.id.startsWith('local-') && (
                    <button
                      type="button"
                      onClick={() => startEdit(m)}
                      className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                      aria-label="Edit and resend"
                      title="Edit & resend"
                    >
                      <Pencil className="w-3 h-3" />
                    </button>
                  )}
                  {m.role === 'assistant' && isLast && (
                    <button
                      type="button"
                      onClick={() => void runStream('regenerate')}
                      className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                      aria-label="Regenerate reply"
                      title="Regenerate"
                    >
                      <RefreshCw className="w-3 h-3" />
                    </button>
                  )}
                </div>
              )}

              {/* ADR-443: how artifact writes render is a MOUNT concern the
                  mount declares via the `artifactWrite` slot. 'card' (default,
                  /chat) = full preview; 'link' = a compact citation line; 'none'
                  (Studio) = suppressed, because the mount already owns the view
                  (the canvas), so a transcript render would duplicate it. */}
              {m.role === 'assistant' && m.artifacts?.length && artifactWrite !== 'none' ? (
                <div className="mt-2 space-y-2">
                  {m.artifacts.map((a) =>
                    artifactWrite === 'link' ? (
                      <div
                        key={a.path}
                        className="flex items-center gap-1.5 text-xs text-muted-foreground"
                      >
                        <FileText className="h-3.5 w-3.5 shrink-0" />
                        <span className="text-foreground/80">{a.verb}</span>
                        <span className="truncate font-medium">{a.path.split('/').pop() || a.path}</span>
                      </div>
                    ) : (
                      <ArtifactCard
                        key={a.path}
                        path={a.path}
                        verb={a.verb}
                        attribution={`you via ${modelLabel}`}
                        // Tile posture while the turn still streams (this row
                        // is the in-flight reply): the write is visible the
                        // moment it lands, but the full render waits for the
                        // words — mid-turn, the message stays primary.
                        streaming={sending && isLast}
                      />
                    ),
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
        {error && (
          <div className="text-xs text-destructive text-center">{error}</div>
        )}
          </div>
        </div>
        {!pinned && <JumpToLatest onClick={() => scrollToBottom('smooth')} />}
      </div>

      {/* The composer FLOATS: a card sitting over the transcript rather than a
          bar welded to the pane's bottom edge.

          The full-width rule it used to carry drew a hard line across the
          surface and made the input read as a separate region — the shape a
          form has, not the shape a conversation has. Lifting it into a card
          says the same thing the transcript says: this is one column of work,
          and the thing you type into belongs to it. It is also what every
          current chat client converged on, for the same reason.

          The card is a flex SIBLING of the transcript, not an overlay — it
          reduces the scroll area rather than covering it, so the last message
          is never hidden underneath and no bottom-padding compensation is
          needed. `bg-background` is still explicit so the card reads as a
          raised surface against the pane rather than as a hole in it.

          On a phone it must clear the home indicator / gesture bar, or the send
          button sits under it. `env(safe-area-inset-bottom)` is the one honest
          signal for that — a fixed px guess is wrong on every other device. */}
      <div
        className="shrink-0 px-3 pt-1"
        style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
      >
        {/* The composer rides the SAME centred column as the transcript. A
            full-width input under a centred conversation reads as two different
            documents, and the reply lands somewhere the eye was not. */}
        <div
          className="mx-auto w-full rounded-2xl border border-border bg-background px-2 py-1.5 shadow-sm transition-shadow focus-within:shadow-md"
          style={{ maxWidth: CONVERSATION_COLUMN_PX }}
        >
        {/* Phase-A edit-and-resend: the banner names the mode; Esc cancels.
            Sending replaces the tail from the edited message (transcript
            only — the ledger keeps what already landed). */}
        {editing && (
          <div className="flex items-center justify-between px-2 pb-1.5 text-[11px] text-muted-foreground">
            <span className="flex items-center gap-1">
              <Pencil className="w-3 h-3" />
              Editing — sending replaces this message and everything after it
            </span>
            <button
              type="button"
              onClick={cancelEdit}
              className="px-1.5 py-0.5 rounded hover:bg-muted hover:text-foreground transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
        {/* ADR-579 D7 — the held gesture: target named, metered marker
            visible, dismissible; the intent below stays editable and nothing
            fires until Send. The `AI` pill is StudioBlockMenu's D4 badge
            riding into the turn it will spend. */}
        {pendingSeed && (
          <div className="flex flex-wrap gap-1 px-1 pb-1.5">
            <span className="inline-flex items-center gap-1 rounded border border-amber-300/60 bg-amber-50 px-1.5 py-0.5 text-[11px] text-amber-900 dark:border-amber-700/60 dark:bg-amber-950/30 dark:text-amber-200">
              <Sparkles className="w-3 h-3" />
              <span className="capitalize">{pendingSeed.verb}</span>
              <span>·</span>
              <span className="truncate max-w-[180px]">
                {seedTargetNoun(pendingSeed)}
                {pendingSeed.excerpt ? ` — “${pendingSeed.excerpt.slice(0, 40)}${pendingSeed.excerpt.length > 40 ? '…' : ''}”` : ''}
              </span>
              <span className="ml-0.5 inline-flex items-center gap-0.5 rounded bg-amber-200/70 px-1 text-[9px] font-semibold tracking-wide text-amber-900 dark:bg-amber-800/60 dark:text-amber-100">
                AI
              </span>
              <button
                type="button"
                onClick={() => setPendingSeed(null)}
                className="p-0.5 rounded hover:bg-amber-100 dark:hover:bg-amber-900/40"
                aria-label="Drop the gesture target"
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          </div>
        )}
        {/* Phase-A attachments: composer chips (uploading → ready | failed). */}
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-1 px-1 pb-1.5">
            {attachments.map((a) => (
              <span
                key={a.key}
                className={cn(
                  'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px]',
                  a.error
                    ? 'border-destructive/50 text-destructive'
                    : 'border-border text-muted-foreground',
                )}
              >
                {a.uploading ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : a.kind === 'image' ? (
                  <ImageIcon className="w-3 h-3" />
                ) : (
                  <FileText className="w-3 h-3" />
                )}
                <span className="truncate max-w-[140px]">{a.name}</span>
                {a.error && <span>failed</span>}
                <button
                  type="button"
                  onClick={() =>
                    setAttachments((prev) => prev.filter((p) => p.key !== a.key))
                  }
                  className="p-0.5 rounded hover:text-foreground"
                  aria-label={`Remove ${a.name}`}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        )}
        {/* `relative` anchors the '@' menu, which mounts bottom-full — above
            the composer, the way the command picker does. */}
        <div className="relative flex items-end gap-2">
          {mention && mentionCandidates.length > 0 && (
            <MentionMenu
              candidates={mentionCandidates}
              filter={mention.query}
              highlight={mentionHighlight}
              onHighlight={setMentionHighlight}
              onPick={pickMention}
              onPickOutsider={
                onMentionOutsider
                  ? (c) => {
                      setMention(null);
                      onMentionOutsider(c);
                    }
                  : undefined
              }
              onClose={() => setMention(null)}
              onItemsChange={(items) => {
                mentionItemsRef.current = items;
              }}
            />
          )}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={
              visionCapable
                ? 'image/png,image/jpeg,image/webp,image/gif,.pdf,.docx,.txt,.md'
                : '.pdf,.docx,.txt,.md'
            }
            className="hidden"
            onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              if (files.length) addFiles(files);
              e.target.value = '';
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={sending}
            className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-40 shrink-0 transition-colors"
            aria-label="Attach a file"
            title="Attach (upload)"
          >
            <Paperclip className="w-4 h-4" />
          </button>
          {/* Attach-from-workspace (ADR-512 D6): a BIND, not a copy — the chip
              references the existing artifact by path (the ADR-448 grammar);
              nothing forks, the conversation points at the one attributed
              file. Inside the commons this needs no grant change; the
              cross-boundary grant interstitial arrives with viewer-scoped
              casts (named deferred). */}
          <button
            type="button"
            onClick={() => setWorkspacePickOpen(true)}
            disabled={sending}
            className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-40 shrink-0 transition-colors"
            aria-label="Attach a workspace file"
            title="Attach from workspace"
          >
            <FolderOpen className="w-4 h-4" />
          </button>
          <WorkspacePickerModal
            open={workspacePickOpen}
            mode="file"
            title="Attach from workspace"
            subtitle="Reference an existing file — nothing is copied"
            confirmLabel="Attach"
            emptyMessage="Nothing in the workspace yet."
            selectable={() => true}
            onClose={() => setWorkspacePickOpen(false)}
            onConfirm={attachWorkspaceFile}
          />
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              // After the value lands, so the caret read is the post-edit one.
              requestAnimationFrame(syncMention);
            }}
            onSelect={syncMention}
            onBlur={() => setMention(null)}
            onKeyDown={(e) => {
              // The MENU owns these keys while it is open — the textarea keeps
              // focus (the caret must not leave the run), so the host arbitrates
              // rather than the palette. Same inversion as StudioSlashPalette.
              const items = mentionItemsRef.current;
              if (mention && items.length > 0) {
                if (e.key === 'ArrowDown') {
                  e.preventDefault();
                  setMentionHighlight((h) => Math.min(h + 1, items.length - 1));
                  return;
                }
                if (e.key === 'ArrowUp') {
                  e.preventDefault();
                  setMentionHighlight((h) => Math.max(h - 1, 0));
                  return;
                }
                if (e.key === 'Enter' || e.key === 'Tab') {
                  e.preventDefault();
                  pickMention(items[Math.min(mentionHighlight, items.length - 1)]);
                  return;
                }
                if (e.key === 'Escape') {
                  e.preventDefault();
                  setMention(null);
                  return;
                }
              }
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
              if (e.key === 'Escape' && editing) {
                e.preventDefault();
                cancelEdit();
              }
            }}
            onPaste={(e) => {
              // Pasted images (screenshots) become attachments.
              const files = Array.from(e.clipboardData?.files ?? []).filter((f) =>
                f.type.startsWith('image/'),
              );
              if (files.length) {
                e.preventDefault();
                addFiles(files);
              }
            }}
            // WHO ANSWERS, said once, where a chat surface already says it.
            //
            // The first attempt at this was a persistent chip above the
            // composer ("Thinker answers next ✕ · @ someone to redirect") — a
            // standing instructional banner for a fact that is only ever
            // interesting in passing. The rule should be QUIET: a conventional
            // chat names the recipient in the placeholder and says nothing more.
            // Two Agents make the room's name ambiguous, so name the one who
            // will actually answer; below that, the SPEAKER's name is right.
            //
            // NEVER `laneName`. A lane is named for its SUBJECT, and on every
            // bound app that subject is a FILE — so the composer read
            // "Message Learn: embed-application-2026-08-10.md…", addressing a
            // document as if it could reply. `speakerLabel` is the prop that
            // already answers "who is working, for the member to read"
            // (ADR-562 D5) and every caller passes it: the app's name for its
            // resident ("Designer", "Writer"), else the colleague's own name,
            // else the engine label. The fallback is GENERIC rather than a
            // guessed name — "Write a message…" is true of every surface,
            // where a wrong name is true of none.
            placeholder={
              editing
                ? 'Edit your message…'
                : floorName
                  ? `Message ${floorName}…`
                  : speakerLabel
                    ? `Message ${speakerLabel}…`
                    : 'Write a message…'
            }
            rows={1}
            style={{ maxHeight: COMPOSER_MAX_PX }}
            // No border, no ring, no ground of its own: the CARD is the box.
            // Two nested boxes is what made the old bar read as a form control
            // dropped into a surface rather than as the surface's own input.
            className="min-h-[36px] flex-1 resize-none overflow-y-auto bg-transparent px-2 py-1.5 text-sm focus:outline-none"
          />
          {sending ? (
            <button
              onClick={stop}
              className="p-2 rounded-md border border-border text-foreground hover:bg-muted shrink-0 transition-colors"
              aria-label="Stop generating"
              title="Stop"
            >
              <Square className="w-4 h-4" />
            </button>
          ) : (
            <button
              onClick={() => void send()}
              disabled={!input.trim() || attachments.some((a) => a.uploading)}
              className="p-2 rounded-md bg-primary text-primary-foreground disabled:opacity-40 shrink-0"
              aria-label="Send"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          )}
        </div>
        </div>
      </div>
    </div>
  );
}
