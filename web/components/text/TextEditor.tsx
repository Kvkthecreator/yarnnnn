'use client';

/**
 * TextEditor — Text's open state (ADR-571, deepened to Docs parity by ADR-572).
 *
 * The Docs open-state shape, one medium down: a crumb row (app · document
 * name, click to rename) with the view controls and boundary acts (Read/Write ·
 * zoom · Share · Export) on the right, the canvas in the middle, and the
 * Properties|Chat rail carrying Editor's bound lane — the same two tabs, the
 * same never-unmount rule so a streaming turn survives a tab switch.
 *
 * ## ONE canvas (ADR-572 D8)
 *
 * `ProseCanvas` is CodeMirror-grade: always editable, always styled, no mode
 * toggle. The first cut split Read from Write, and the operator's correction —
 * *"do we need to split the modes? like docs app can we just have one mode"* —
 * was right: Docs has one canvas, and the split hid every formatting control
 * behind a mode the surface did not open in.
 *
 * ADR-456 D1 permits "textarea/CodeMirror-grade"; the split read that ceiling
 * as a floor. CodeMirror's document is a plain STRING and its styling is a
 * decoration layer recomputed each update — nothing enters the file, so the
 * `.md` stays byte-identical. See `ProseCanvas` for the full argument.
 *
 * ## File handling is Docs' (ADR-572 D10 — supersedes D5)
 *
 * D5 gave Text an explicit Save button on the premise that *"Docs autosaves
 * with no CAS, so a prose member needs to know which bytes are theirs."*
 * **That premise was false.** Docs' `writeAndAdvance` is a queued CAS commit
 * per operation — `writeArtifact(path, html, baseHead, message)` with a 409
 * handler that refetches the head and re-applies once. Docs has everything
 * the Save button was justified by and still has no button, no dirty flag and
 * no manual gesture.
 *
 * So Text was not more careful than Docs; it was less capable, and it handed
 * the member the difference as a chore. Saving is now automatic on idle-2s
 * and on blur/teardown, over the same CAS path, and the Save button is
 * DELETED rather than kept beside it.
 *
 * The ONE thing Text keeps is the **409 conflict banner**, and the asymmetry
 * that justifies it is real: Docs commits operations it can replay onto a
 * fresh head, while Text commits whole text, which cannot be re-applied
 * without inventing a merge. So a conflict asks the member instead of
 * resolving itself. That is the part of D5 that survives contact with Docs.
 *
 * The save path is ADR-570's, unchanged: `PATCH /workspace/file` (prose class
 * ∧ carve law ∧ principal gate), CAS-guarded on the head the document was
 * loaded with.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  FileText,
  Link2,
  Loader2,
  MoreHorizontal,
  PanelRight,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { PANE_HEADING, PANE_SECTION } from '@/lib/authoring/pane-spine';
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { useFileContextMenu } from '@/components/workspace/FileContextMenu';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { formatRelativeTime } from '@/lib/formatting';
import { LanePanel, type SeedTarget } from '@/components/chat-surface/LanePanel';
import { SelectionGesture } from '@/components/authoring/SelectionGesture';
import { ShareDialog } from '@/components/workspace/ShareDialog';
import { TextExport } from '@/components/text/TextExport';
import { ProseCanvas, type ProseCanvasHandle, type SlashRun } from '@/components/text/ProseCanvas';
import { MarkdownToolbar, type ToolbarAction } from '@/components/text/MarkdownToolbar';
import { FACE } from '@/components/text/readingFace';
import { SlashMenu, filterSlashItems, type SlashItem } from '@/components/text/SlashMenu';
import { StudioCitablePicker } from '@/components/authoring/StudioCitablePicker';
import { readConflict, type ConflictState } from '@/components/text/conflict';
import { useFileRevisionsRealtime } from '@/lib/realtime/use-file-revisions-realtime';
import { useDeclareFocus, type SurfaceFocus } from '@/lib/shell/useSurfaceFocus';
import { parseOutline, readingMinutes } from '@/components/text/outline';
import {
  insertCsvTable,
  insertFence,
  insertImage,
  insertLink,
  insertMermaid,
  insertRule,
  insertTable,
  offsetOfLine,
  toggleChecklist,
  toggleHeading,
  toggleList,
  toggleQuote,
  toggleWrap,
  type Edit,
} from '@/components/text/markdownEdits';
import { documentName, leafOf } from '@/components/text/TextSurface';
import { slotIsColumn, usePaneLadder, usePaneSlot } from '@/lib/shell/pane-layout';
import { useFeedback } from '@/contexts/FeedbackContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';

type LanesEnv = Awaited<ReturnType<typeof api.lanes.list>>;
type LaneRow = LanesEnv['lanes'][number];

const WORKSPACE_PREFIX = '/workspace/';
const relPath = (p: string) => (p.startsWith(WORKSPACE_PREFIX) ? p.slice(WORKSPACE_PREFIX.length) : p);

/** Docs' clamp (`StudioSurface`: 0.25–2), so the two apps zoom alike. */
const ZOOM_MIN = 0.25;
const ZOOM_MAX = 2;

/**
 * Idle before an edit commits — Docs' own `COMMIT_IDLE_MS` (`FlowEditor`),
 * matched deliberately so the two document apps batch revisions alike
 * (ADR-572 D10). A member moving between Docs and Text should not have to
 * learn two save models.
 */
const COMMIT_IDLE_MS = 2000;

const SUGGESTIONS = [
  'Tighten this — same meaning, fewer words',
  'What is unclear to someone reading this cold?',
  'Restructure so the main point lands first',
];


export function TextEditor({
  path,
  onClose,
  onSaved,
  onRenamed,
}: {
  path: string;
  onClose: () => void;
  onSaved?: () => void;
  onRenamed?: (nextPath: string) => void;
}) {
  const [setWorkbenchNode, wb] = usePaneLadder();
  const [reloadKey, setReloadKey] = useState(0);
  const { file, loading, notFound, error, headRevision, refreshRevision } = useFileLoad(path, {
    withRevision: true,
    reloadKey,
  });

  const [text, setText] = useState('');
  const [baseline, setBaseline] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ConflictState | null>(null);
  const baseHead = useRef<string | null>(null);
  const canvasRef = useRef<ProseCanvasHandle | null>(null);
  // ADR-612 D5 — the landing's three inputs, held as refs because the effect
  // that consumes them runs above their declarations and must not close over
  // a stale render's copy.
  /** ADR-612 D4 — the target a gesture ARMED, held until the member actually
   *  sends (or abandons it). Armed is not pending: a seeded composer is an
   *  intent being written, not a turn in flight. */
  const armedRewriteRef = useRef<{ start: number; end: number; excerpt: string } | null>(null);
  /** ADR-612 D5 — the span the LANDING will re-find, held separately from the
   *  spinner's state. The turn settles (`onSeededTurn(false)`) as soon as the
   *  stream closes, which is often BEFORE the refetch resolves — reading the
   *  spinner's state here meant the target was already gone and the landing
   *  silently never ran, leaving the member at the top of the document. */
  const landingTargetRef = useRef<{ start: number; end: number; excerpt: string } | null>(null);
  const preWriteRef = useRef<string | null>(null);
  const landOnRewriteRef = useRef<
    (before: string, after: string, span: { start: number; end: number }) => void
  >(() => {});

  // ── View state (ADR-572 D2) — zoom only; it never touches the file.
  const [zoom, setZoom] = useState(1);

  // Rail: Properties | Chat, the Docs grammar. The lane stays MOUNTED while
  // Properties is up (CSS-hidden) so a streaming turn survives the switch.
  const [rightTab, setRightTab] = useState<'properties' | 'chat'>('properties');
  const { sideIsOverlay, singlePane, fullLabels } = wb;
  // The side pane rides the ONE pane contract (`lib/shell/pane-layout.ts`) —
  // the same show/hide + width + persistence Studio and Chat use. Text composes
  // no rail: absence is a property of the medium (markdown has no navigator),
  // and a slot a surface does not compose is absent, never broken.
  const { userId } = useSurfacePreferences();
  const side = usePaneSlot('text', 'side', userId, wb, { defaultShown: true });
  const sideOpen = side.shown;
  // The single-pane rung shows ONE pane at a time with a bottom tab bar — the
  // Docs ladder's last rung. Without it the rail would be unreachable on a
  // phone (the ADR-519 lesson: never ship an inescapable state).
  const [activePane, setActivePane] = useState<'canvas' | 'chat'>('canvas');

  const [shareTarget, setShareTarget] = useState<{ path: string; name: string } | null>(null);

  useEffect(() => {
    if (!file) return;
    const content = file.content ?? '';
    setText(content);
    setBaseline(content);
    baseHead.current = file.head_version_id ?? null;
    setConflict(null);
    // ADR-612 D5 — a lane write just landed and the member asked for it on a
    // specific passage. Put them back on it, once, after the canvas has taken
    // the new document (a frame later — the effect runs before the value
    // reaches the view).
    const target = landingTargetRef.current;
    const before = preWriteRef.current;
    if (target && before !== null && before !== content) {
      landingTargetRef.current = null;
      preWriteRef.current = null;
      requestAnimationFrame(() => landOnRewriteRef.current(before, content, target));
    }
  }, [file]);

  const dirty = text !== baseline;

  // The live text, read by the debounced commit. A timer that closed over
  // `text` would write whatever the document said when the timer was SET —
  // the classic stale-closure autosave bug, which writes a revision one
  // keystroke behind and then reports success.
  const textRef = useRef(text);
  textRef.current = text;
  const baselineRef = useRef(baseline);
  baselineRef.current = baseline;

  // Revision ids this editor authored, so the realtime echo of our OWN save is
  // not reported back as a peer edit (ADR-575). Declared here, above `commit`,
  // because `commit` writes to it — a `const` used before its declaration line
  // is a temporal-dead-zone throw at runtime, which no build step catches.
  const ownRevisions = useRef<Set<string>>(new Set());
  /** A peer's revision landed while the member had unsaved text. */
  const [peerEdit, setPeerEdit] = useState<{ actor: string; at: string } | null>(null);

  /**
   * Commit the current text as one attributed CAS revision.
   *
   * Serialized through `writeTail` exactly as Docs serializes its queue
   * (`StudioSurface`): two commits must never race, because the second one's
   * CAS base is the head the first one acked. Reading `baseHead` INSIDE the
   * queued body rather than from a render closure is the same rule.
   */
  const writeTail = useRef<Promise<void>>(Promise.resolve());
  const savingRef = useRef(false);

  /**
   * The bytes the LAST queued commit sent, updated synchronously inside the
   * queue. `baselineRef` mirrors React state, which lags a tick — so two
   * triggers firing close together (the idle timer, then a blur flush) both
   * saw the OLD baseline and both wrote, minting a duplicate revision of
   * identical bytes. The revision log is the product; it must not carry
   * phantom entries because two timers agreed.
   */
  const inFlightBody = useRef<string | null>(null);

  const commit = useCallback(
    (expectedHead?: string | null): Promise<void> => {
      const run = async () => {
        const body = textRef.current;
        // Nothing new to say — never mint an empty revision (Docs' rule).
        // Checked against the queue's own record as well as React state,
        // because state has not necessarily re-rendered since the last commit.
        if (
          expectedHead === undefined &&
          (body === baselineRef.current || body === inFlightBody.current)
        ) {
          return;
        }
        inFlightBody.current = body;
        savingRef.current = true;
        setSaving(true);
        setSaveError(null);
        try {
          const res = await api.workspace.editFile(
            path,
            body,
            undefined,
            'Edited in Text',
            expectedHead === undefined ? baseHead.current : expectedHead,
          );
          const newHead = (res as { head_version_id?: string }).head_version_id ?? null;
          baseHead.current = newHead;
          // Remember our own revision ids so the realtime echo of THIS save is
          // not announced back to the member as somebody else's edit
          // (ADR-575).
          if (newHead) ownRevisions.current.add(newHead);
          setBaseline(body);
          setConflict(null);
          setPeerEdit(null);
          setSavedAt(Date.now());
          // A save changes the REVISION, not the member's text — so refresh
          // only the revision. `reloadKey` would re-run `getFile` and re-fire
          // the `setText(content)` effect, destroying a keystroke that landed
          // during the refetch (the D12 shape). This is the fix for Properties
          // reading "No revisions yet." on a file with four revisions.
          refreshRevision();
          onSaved?.();
        } catch (err) {
          if (err instanceof APIError && err.status === 409) {
            // The conflict banner STAYS (ADR-572 D10). Docs can auto-recompute
            // a 409 because it commits OPERATIONS it can replay on a fresh
            // head; Text commits whole text, which cannot be re-applied
            // without inventing a merge. So the member is told, and chooses.
            setConflict(readConflict(err.data));
          } else {
            setSaveError(err instanceof Error ? err.message : 'Save failed');
          }
        } finally {
          savingRef.current = false;
          setSaving(false);
        }
      };
      const next = writeTail.current.then(run, run);
      writeTail.current = next.catch(() => undefined);
      return next;
    },
    [path, onSaved, refreshRevision],
  );

  // ── Hearing about other principals' writes (ADR-575) ────────────────────
  //
  // The conflict banner used to be the FIRST notice that anyone else had
  // touched this document: whole-document CAS with no subscription means a
  // peer's write is discovered by colliding with it at save time. Measured on
  // production — `/workspace/seulki/babo-song-concept.md` had four revisions,
  // one authored by `yarnnn:mcp:claude.ai`, while the open editor showed
  // "No revisions yet." and an unexplained 409.
  //
  // Notion's members never see that screen, and the reason is not their block
  // model: rendering a record subscribes the client to it, and the server
  // pushes a version on commit. This is that. Whole-document CAS is unchanged
  // — the 409 still exists and still asks — but it becomes RARE and INFORMED
  // instead of routine and surprising.
  useFileRevisionsRealtime({
    path,
    isOwnWrite: (row) => ownRevisions.current.has(row.id),
    onForeignRevision: (row) => {
      // The head moved under us. Two different situations, and conflating them
      // is what made the old banner confusing:
      //
      //   - the member has NOT typed since their last save → nothing of theirs
      //     is at stake, so take their revision silently. The document is
      //     reloaded and LAST EDITED updates. No decision to make.
      //   - the member HAS unsaved text → do NOT touch the document (that
      //     would discard their typing). Tell them now, while they can still
      //     act, rather than at save time.
      refreshRevision();
      if (textRef.current === baselineRef.current) {
        setReloadKey((n) => n + 1);
      } else {
        setPeerEdit({ actor: row.authored_by, at: row.created_at });
      }
    },
  });

  // ── Autosave: idle-2s, flushed on blur and teardown (ADR-572 D10) ───────
  // Ported from Docs (`COMMIT_IDLE_MS = 2000` in `FlowEditor`), which is the
  // shape ADR-572 D5 originally diverged from on a premise that turned out to
  // be false: D5 said Docs "autosaves with no CAS", so Text needed a manual
  // Save. Docs autosaves WITH CAS — `writeArtifact(path, html, baseHead)`,
  // queued, with a 409 path. Text was therefore not more careful than Docs;
  // it was less capable, and it billed the member for the difference by
  // making them press a button. The Save button is DELETED, not kept beside
  // this — two save models in one surface is the dual-approach shape.
  const commitTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback(() => {
    if (commitTimer.current) {
      clearTimeout(commitTimer.current);
      commitTimer.current = null;
    }
    if (textRef.current === baselineRef.current) return;
    void commit();
  }, [commit]);

  useEffect(() => {
    if (!dirty || conflict) return; // a conflict waits for the member's choice
    if (commitTimer.current) clearTimeout(commitTimer.current);
    commitTimer.current = setTimeout(() => {
      commitTimer.current = null;
      if (!savingRef.current) void commit();
    }, COMMIT_IDLE_MS);
    return () => {
      if (commitTimer.current) clearTimeout(commitTimer.current);
      commitTimer.current = null;
    };
  }, [text, dirty, conflict, commit]);

  // Leaving the tab or the app must not drop the last two seconds of typing.
  useEffect(() => {
    const onHide = () => { if (document.visibilityState === 'hidden') flush(); };
    window.addEventListener('beforeunload', flush);
    document.addEventListener('visibilitychange', onHide);
    return () => {
      window.removeEventListener('beforeunload', flush);
      document.removeEventListener('visibilitychange', onHide);
      // Teardown (closing the document, following a rename) flushes too —
      // `commit` reads the text through a ref, so this is safe after unmount.
      flush();
    };
  }, [flush]);

  useEffect(() => {
    if (savedAt === null) return;
    const t = setTimeout(() => setSavedAt(null), 2200);
    return () => clearTimeout(t);
  }, [savedAt]);

  // ── Applying a source edit ──────────────────────────────────────────────
  // Every formatting/insert path funnels through here. The canvas owns the
  // caret, so the pure function's computed selection is handed straight to it
  // as one transaction — no rAF dance, and undo treats it as a single step.
  const applyEdit = useCallback((edit: Edit) => {
    canvasRef.current?.apply(edit.text, edit.selectionStart, edit.selectionEnd);
    setText(edit.text);
  }, []);

  // The canonical async-outcome reporter (ADR-400), aliased — this file's own
  // `runAction` below is the TOOLBAR dispatcher, an unrelated verb.
  const { runAction: reportAction } = useFeedback();

  const runAction = useCallback(
    (action: ToolbarAction) => {
      const sel = canvasRef.current?.selection();
      if (!sel) return;
      const [s, e] = sel;
      switch (action.kind) {
        case 'wrap': return applyEdit(toggleWrap(text, s, e, action.marker));
        case 'heading': return applyEdit(toggleHeading(text, s, e, action.level));
        case 'list': return applyEdit(toggleList(text, s, e, action.ordered));
        case 'checklist': return applyEdit(toggleChecklist(text, s, e));
        case 'quote': return applyEdit(toggleQuote(text, s, e));
        case 'link': return applyEdit(insertLink(text, s, e));
        case 'table': return applyEdit(insertTable(text, s, e));
        case 'rule': return applyEdit(insertRule(text, s, e));
        case 'code': return applyEdit(insertFence(text, s, e));
        case 'mermaid': return applyEdit(insertMermaid(text, s, e));
        // The two-step inserts: the path comes from the picker, so the caret
        // is parked and the edit lands on the pick.
        case 'image': return setPicker({ at: s, for: 'image' });
        case 'csvtable': return setPicker({ at: s, for: 'csvtable' });
      }
    },
    [text, applyEdit],
  );

  // ── The workspace file picker (ADR-572 D17, D18) ────────────────────────
  // Reuses Docs' `StudioCitablePicker` and its `/studio/citable` listing —
  // there is no second index, and no upload flow here for the same reason Docs
  // has none: files arrive through Files or IMAGES, and Insert cites what the
  // workspace already holds.
  //
  // ONE picker serving two kinds, not two pickers: the endpoint already
  // returns both lists (`images` and `tables`), and `cites` selects between
  // them. `for` carries which insert the pick will run.
  const [picker, setPicker] = useState<{ at: number; for: 'image' | 'csvtable' } | null>(null);

  const takeImage = useCallback(
    (path: string) => {
      const at = picker?.at ?? canvasRef.current?.selection()?.[0] ?? text.length;
      setPicker(null);
      applyEdit(insertImage(text, at, at, relPath(path)));
    },
    [picker, text, applyEdit],
  );

  /**
   * Take a CSV pick — read the file, write its rows (ADR-572 D18).
   *
   * The only insert in this app that performs I/O, because it is the only one
   * whose content lives in another file. It resolves to TEXT before touching
   * the document: the rows are written into the `.md` as real markdown, so
   * what a connector reads back is a table, not a pointer to one.
   *
   * `text` is re-read from the canvas rather than closed over — the member can
   * keep typing while the picker is open and the fetch is in flight, and
   * applying a stale string would delete whatever they wrote (the D12 shape).
   */
  const takeCsv = useCallback(
    async (path: string) => {
      const at = picker?.at ?? canvasRef.current?.selection()?.[0] ?? text.length;
      setPicker(null);
      try {
        // Transient-surfacing streamline 2026-08-22: the D18 notice rides the
        // canonical toast layer (was a hand-rolled bottom-center div). The
        // D18 contract is unchanged: the fetch says so while in flight, and
        // a read that fails inserts NOTHING — a source note with no rows
        // under it would read as "that file is empty", which is a different
        // and false claim (the file may be fine and the request may not
        // have been).
        await reportAction(
          async () => {
            const file = await api.workspace.getFile(relPath(path));
            const current = canvasRef.current?.text() ?? text;
            const where = Math.min(at, current.length);
            applyEdit(insertCsvTable(current, where, where, relPath(path), file.content ?? '', new Date()));
          },
          {
            pending: 'Reading the CSV…',
            error: `Couldn’t read ${relPath(path)} — nothing was inserted.`,
          },
        );
      } catch {
        // Reported by the toast; nothing was inserted.
      }
    },
    [picker, text, applyEdit, reportAction],
  );

  /**
   * Go to a source range and scroll it into view — the outline jump.
   *
   * The canvas lands the caret COLLAPSED at the start (ADR-572 D20); the end
   * is passed so a heading taller than one line is scrolled fully into view.
   */
  const reveal = useCallback((span: [number, number]) => {
    canvasRef.current?.reveal(span[0], span[1]);
  }, []);

  // ── The `/` insert palette (ADR-572 D14) ────────────────────────────────
  // Notion's gesture, which Docs also has. The run is read by the CANVAS (only
  // the view knows the caret) and handed up; the palette is chrome, so it lives
  // here beside the toolbar it shares its actions with.
  const [slash, setSlash] = useState<SlashRun | null>(null);
  const [slashIndex, setSlashIndex] = useState(0);
  const slashItems = useMemo(() => filterSlashItems(slash?.filter ?? ''), [slash]);
  // A filter that matches nothing closes the palette rather than showing an
  // empty box — the member is typing prose that happens to start with `/`.
  const slashOpen = slash !== null && slashItems.length > 0;
  const slashCoords = useMemo(
    () => (slash ? canvasRef.current?.coordsAt(slash.from) ?? null : null),
    // `text` is a dep so the anchor re-reads as the line moves under the caret.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [slash, text],
  );

  useEffect(() => { setSlashIndex(0); }, [slash?.filter]);

  /**
   * Take a slash pick — as ONE edit (ADR-572 D15).
   *
   * The first cut did this in two steps: `deleteRange(run)` on the view, then
   * `applyEdit(...)` — a second dispatch whose text was computed from a string
   * the view had already moved past, plus two `setText` calls racing one
   * render. It worked in isolation for every piece and **did nothing when the
   * member clicked a row** (*"the slash command pops up but when i select it
   * nothing happens"*).
   *
   * Bisecting the composition was the wrong instinct: the composition itself
   * was the defect. The run is plain text in a plain string, so removing it and
   * applying the edit is ONE pure computation over `text`, handed to the canvas
   * as ONE transaction — the same path every toolbar button already takes, and
   * one that cannot half-apply.
   *
   * The canvas reads the current document itself (`selection()`), so nothing
   * here depends on React state having caught up.
   */
  const takeSlash = useCallback(
    (item: SlashItem) => {
      const run = slash;
      if (!run) return;
      setSlash(null);
      // Cut the `/filter` run out first — every offset below is into `next`.
      const next = text.slice(0, run.from) + text.slice(run.to);
      const at = run.from;
      let edit: Edit;
      switch (item.action.kind) {
        case 'heading': edit = toggleHeading(next, at, at, item.action.level); break;
        case 'list': edit = toggleList(next, at, at, item.action.ordered); break;
        case 'checklist': edit = toggleChecklist(next, at, at); break;
        case 'quote': edit = toggleQuote(next, at, at); break;
        case 'table': edit = insertTable(next, at, at); break;
        case 'rule': edit = insertRule(next, at, at); break;
        case 'code': edit = insertFence(next, at, at); break;
        case 'mermaid': edit = insertMermaid(next, at, at); break;
        case 'image':
        case 'csvtable':
          // Two-step: cut the run now (so the `/img` text is gone while the
          // picker is open), then land the insert where it stood.
          applyEdit({ text: next, selectionStart: at, selectionEnd: at });
          setPicker({ at, for: item.action.kind });
          return;
        default: return;
      }
      applyEdit(edit);
    },
    [slash, text, applyEdit],
  );

  // ↑/↓/Enter/Tab/Escape belong to the palette while it is open. Capture phase,
  // because CodeMirror's own keymap would otherwise move the caret or insert a
  // newline before this handler ever sees the key.
  useEffect(() => {
    if (!slashOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown' || (e.key === 'Tab' && !e.shiftKey)) {
        e.preventDefault();
        setSlashIndex((i) => (i + 1) % slashItems.length);
      } else if (e.key === 'ArrowUp' || (e.key === 'Tab' && e.shiftKey)) {
        e.preventDefault();
        setSlashIndex((i) => (i - 1 + slashItems.length) % slashItems.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        takeSlash(slashItems[slashIndex] ?? slashItems[0]);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setSlash(null);
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [slashOpen, slashItems, slashIndex, takeSlash]);

  // ── Keyboard: ⌘S save · ⌘B/⌘I/⌘K formatting ────────────────────────────
  // Window-level, because the document is the subject of the whole surface
  // (the Docs reflex). No mode gate any more — there is one canvas, so a
  // formatting key always has a caret to act on.
  //
  // ⌘F is NOT handled here: `@codemirror/search`'s own keymap owns it inside
  // the canvas, which is the better find than the one this surface shipped
  // (incremental, match-highlighted, regex-capable) — so the hand-rolled bar
  // is deleted rather than kept beside it (ADR-572 D8, no dual implementation).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey)) return;
      const k = e.key.toLowerCase();
      // ⌘S is kept as a FORCE-COMMIT even though saving is automatic: the
      // reflex is universal, and a member who presses it should get the
      // reassurance of an immediate write rather than a browser save dialog.
      if (k === 's') { e.preventDefault(); flush(); return; }
      if (k === 'b') { e.preventDefault(); runAction({ kind: 'wrap', marker: '**' }); }
      else if (k === 'i') { e.preventDefault(); runAction({ kind: 'wrap', marker: '_' }); }
      else if (k === 'k') { e.preventDefault(); runAction({ kind: 'link' }); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [flush, runAction]);

  // Rename through the shared organize grammar; the surface follows the file
  // to its new path (the Docs `setParam({ file })` reflex).
  const { verbs: organizeVerbs, modals: organizeModals } = useFileOrganizeVerbs({
    onAfterMutate: (newPath) => {
      onSaved?.();
      if (newPath && newPath !== path) onRenamed?.(newPath);
      else if (!newPath) onClose();
      else setReloadKey((n) => n + 1);
    },
  });

  /** The member-facing deep link to this document — Docs' own grammar. */
  const copyLink = useCallback(() => {
    const url = `${window.location.origin}/desktop?text.file=${encodeURIComponent(relPath(path))}`;
    void navigator.clipboard.writeText(url);
  }, [path]);

  // ── The FILE menu (ADR-572 D10) ─────────────────────────────────────────
  // The `⋯` existed on the LANDING cards and vanished once a document was
  // open: the open state wired rename only, hidden behind clicking the crumb.
  // So the moment the member was actually working on a document was the one
  // moment they could not act on it as a file.
  //
  // Docs answers this with ~90 lines of hand-rolled popover inlined in
  // `StudioDesignTab` — deliberately NOT copied. The shared
  // `useFileContextMenu` already renders this exact menu (it is what the
  // landing cards use), and `openMenuFromButton` exists for precisely this
  // kebab affordance. Copy link is the one Docs-specific verb, added through
  // the documented `extraItemsFor` extension point rather than by forking.
  const { openMenuFromButton, menu: fileMenu } = useFileContextMenu(
    organizeVerbs,
    () => [
      {
        id: 'copy-link',
        label: 'Copy link',
        icon: <Link2 className="h-3.5 w-3.5 text-muted-foreground" />,
        onClick: copyLink,
      },
    ],
  );

  // ── The bound lane (find-or-create) — the ADR-567 D4 binding contract,
  //    same two-field call every app makes. `app: 'text'` selects Editor
  //    server-side (ADR-562) and the Text job posture (ADR-571 D4).
  const [lanesEnabled, setLanesEnabled] = useState<boolean | null>(null);
  const [lanes, setLanes] = useState<LaneRow[]>([]);
  const [agents, setAgents] = useState<LanesEnv['agents']>([]);
  const [apps, setApps] = useState<NonNullable<LanesEnv['apps']>>([]);
  // ADR-602 — the BEINGS roster. See StudioSurface: `agents` is the HIRE
  // roster (empty since ADR-599), so a resident's name was never found there
  // and the composer addressed the ENGINE instead of Editor.
  const [beings, setBeings] = useState<NonNullable<LanesEnv['beings']>>([]);
  const [models, setModels] = useState<LanesEnv['models']>([]);
  const [creatingLane, setCreatingLane] = useState(false);

  const refreshLanes = useCallback(async () => {
    try {
      const env = await api.lanes.list(true);
      setLanesEnabled(env.enabled);
      setLanes(env.lanes ?? []);
      setAgents(env.agents ?? []);
      setApps(env.apps ?? []);
      setBeings(env.beings ?? []);
      setModels(env.models ?? []);
    } catch {
      setLanesEnabled(false);
    }
  }, []);

  useEffect(() => { void refreshLanes(); }, [refreshLanes]);

  const boundLane = useMemo(
    () => lanes.find((l) => l.status === 'active' && l.artifact_path === path) ?? null,
    [lanes, path],
  );

  useEffect(() => {
    if (!path || !lanesEnabled || boundLane || creatingLane) return;
    setCreatingLane(true);
    api.lanes
      .create({ name: documentName(path).slice(0, 60), app: 'text', artifact_path: path })
      .then(() => refreshLanes())
      .catch(() => { /* the rail states why below */ })
      .finally(() => setCreatingLane(false));
  }, [path, lanesEnabled, boundLane, creatingLane, refreshLanes]);

  const modelLabel = useMemo(() => {
    const id = boundLane?.model;
    return models.find((m) => m.id === id)?.label || id || 'Editor';
  }, [models, boundLane]);

  // ADR-562 D5 — WHO the member reads: the app's name for its resident, read
  // back from the wire, never asserted here.
  const speakerLabel = useMemo(() => {
    // ADR-602 D7 — see StudioSurface: this surface IS the Text app, which is
    // a stronger fact than a lane stamp that may predate ADR-567.
    const slug = apps.find((a) => a.slug === 'text')?.resident || boundLane?.agent;
    if (slug) {
      const appName = apps.find((a) => a.slug === 'text')?.name;
      if (appName) return appName;
      const being = beings.find((b) => b.slug === slug)?.name;
      if (being) return being;
      const named = agents.find((a) => a.slug === slug)?.name;
      if (named) return named;
    }
    return modelLabel;
  }, [agents, apps, beings, boundLane, modelLabel]);

  const words = useMemo(
    () => (text.trim() ? text.trim().split(/\s+/).length : 0),
    [text],
  );
  const outline = useMemo(() => parseOutline(text), [text]);

  // ── ADR-606 D4 — the desk declares where the member stands (ADR-522) ──
  // The declaration ADR-522's own acceptance case named ("caret under a
  // heading, ask 'rewrite this section'") — Docs carried it, the Docs→Text
  // transition dropped it, and until now this desk's colleague knew the
  // document but never the place. The canvas reports offsets; the surface
  // derives the commitment: a held selection (the member's own text, the
  // truest grain), else the nearest h1/h2 at or above the caret (D4's
  // flow reading, by SOURCE LINE — minting nothing), else the document.
  // Derived fields are stored with an equality guard so caret travel inside
  // one section re-renders nothing.
  const [focusPoint, setFocusPoint] = useState<{
    selection: string | null;
    heading: string | null;
    // ADR-609 D2 — the selection's EXTENT, kept beside its clipped name.
    // `selection` is a 120-char prefix for the focus SENTENCE; these offsets
    // are what an anchored edit acts on. Before this they were computed here
    // and dropped on the next line, so the colleague could be told a
    // selection existed but never which bytes it covered.
    range: { start: number; end: number } | null;
  }>({ selection: null, heading: null, range: null });
  const onCanvasSelection = useCallback((from: number, to: number) => {
    // Read the view's doc, not React's `text` — during a keystroke the state
    // lags a render and the offsets belong to the NEW doc (the D12 lesson).
    const doc = canvasRef.current?.text() ?? '';
    const selection =
      from !== to ? doc.slice(from, to).slice(0, 120).trim() || null : null;
    const range = selection ? { start: from, end: to } : null;
    let heading: string | null = null;
    if (!selection) {
      const line = doc.slice(0, from).split('\n').length - 1;
      const heads = parseOutline(doc).filter(
        (h) => h.level <= 2 && h.line <= line,
      );
      heading = heads.length ? heads[heads.length - 1].text : null;
    }
    setFocusPoint((prev) =>
      prev.selection === selection &&
      prev.heading === heading &&
      prev.range?.start === range?.start &&
      prev.range?.end === range?.end
        ? prev
        : { selection, heading, range },
    );
  }, []);
  const focus = useMemo<SurfaceFocus | null>(() => {
    const base = {
      app: 'text',
      path: relPath(path),
      id: null,
      pageIndex: null,
      viewport: null,
    };
    if (focusPoint.selection) {
      return {
        ...base,
        scope: 'block' as const,
        label: 'selection',
        excerpt: focusPoint.selection,
      };
    }
    if (focusPoint.heading) {
      return {
        ...base,
        scope: 'block' as const,
        label: 'heading',
        excerpt: focusPoint.heading,
      };
    }
    // The whole document — renders nothing on the bound lane (the binding
    // already names it) but keeps the declaration live for /chat's fallback.
    return {
      ...base,
      scope: 'document' as const,
      label: leafOf(path),
      excerpt: null,
    };
  }, [focusPoint, path]);
  useDeclareFocus('text', focus);

  // ── ADR-609 D2 — the gesture door this desk never had ─────────────────
  // The whole SeedTarget protocol (ADR-579 D7) existed and Text produced no
  // seeds, so its strongest targeting sentence ("that is this turn's target")
  // was unreachable here: the only way to ask for a change was free prose
  // over a document the colleague held in full, with a clipped prefix naming
  // the selection and nothing naming its extent. The door carries the
  // member's OFFSETS, so the edit lands on exactly what they highlighted.
  const [seed, setSeed] = useState<{
    text: string;
    nonce: number;
    target?: SeedTarget;
  } | null>(null);
  // ADR-612 D1 — where the gesture sits: the END of the selection, in viewport
  // coordinates, read from the view (the SlashMenu precedent). The SELECTION's
  // rect, never the pointer's position — a selection has a rect on touch,
  // where a pointer has none, so this is the anchor that survives both media
  // (lane-frame §6, amended).
  const selectionAnchor = useMemo(
    () => (focusPoint.range ? canvasRef.current?.selectionRect() ?? null : null),
    // `text` is a dep so the anchor re-reads as the line moves underneath —
    // the same reason slashCoords carries it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [focusPoint.range, text],
  );
  // ── ADR-612 D4/D5 — the act has a LIFETIME, and it ends somewhere ─────
  // Clicking Rewrite used to be the end of the visible story: the door
  // vanished the moment the selection moved, the turn ran unseen, and the
  // document then silently replaced itself under the member — who had to hunt
  // for what changed. Two facts were missing and both are held here: that a
  // turn is IN FLIGHT for this selection, and WHERE it was, so the member can
  // be put back on it when the write lands.
  const [pendingRewrite, setPendingRewrite] = useState<{
    start: number;
    end: number;
    /** The selected text at click time — how the landed range is re-found
     *  when the rewrite changed the document's length. */
    excerpt: string;
  } | null>(null);
  const rewriteSelection = useCallback(() => {
    if (!focusPoint.selection || !focusPoint.range) return;
    // The click only SEEDS the composer (ADR-579 D7): the member still edits
    // the intent and presses Send, or dismisses the chip, or never sends. So
    // this ARMS the target and claims nothing — `pendingRewrite` is set when
    // the lane reports a seeded turn actually going up.
    armedRewriteRef.current = { ...focusPoint.range, excerpt: focusPoint.selection };
    setSeed((s) => ({
      text: 'Rewrite the selection: ',
      nonce: (s?.nonce ?? 0) + 1,
      target: {
        verb: 'rewrite',
        path: relPath(path),
        blockId: null,
        label: 'selection',
        excerpt: focusPoint.selection,
        pageIndex: null,
        range: focusPoint.range,
      },
    }));
    setRightTab('chat');
  }, [focusPoint, path]);

  // ADR-612 D5 — land the member back on the work. When the lane's write
  // arrives, the document has already replaced itself; without this the member
  // is left wherever the canvas happened to put them (the caret is preserved
  // by an offset-from-the-END heuristic, which is exactly wrong when the
  // rewrite landed in the MIDDLE — text above it shifts and the anchor drifts).
  //
  // Re-find by CONTENT, not by offset: the rewritten passage is a different
  // length, so the old span no longer describes it. The prefix before the
  // selection is the stable part, so its end is where the new passage starts;
  // the following text locates its end. Both are best-effort — a rewrite that
  // also restructured the surroundings simply scrolls to the start, which is
  // still the right neighbourhood and never a wrong claim.
  const landOnRewrite = useCallback(
    (before: string, after: string, span: { start: number; end: number }) => {
      const head = before.slice(0, span.start);
      const tail = before.slice(span.end);
      // The unchanged prefix pins the start.
      let start = 0;
      while (start < head.length && start < after.length && head[start] === after[start]) start++;
      // The unchanged suffix pins the end, walked from the far side.
      let back = 0;
      while (
        back < tail.length &&
        back < after.length - start &&
        tail[tail.length - 1 - back] === after[after.length - 1 - back]
      ) back++;
      const end = after.length - back;
      canvasRef.current?.scrollRangeIntoView(start, Math.max(start, end));
    },
    [],
  );

  landOnRewriteRef.current = landOnRewrite;

  // A pending rewrite is cleared by the write landing (D5). A turn that
  // answers WITHOUT writing — a refusal, a question back, an error — would
  // otherwise leave the door saying "Rewriting…" for the rest of the session.
  // The ceiling is generous on purpose: it is a stuck-state release, not a
  // timeout on the turn, and expiring an in-flight turn early would be the
  // worse lie.
  useEffect(() => {
    if (!pendingRewrite) return;
    const t = setTimeout(() => setPendingRewrite(null), 180_000);
    return () => clearTimeout(t);
  }, [pendingRewrite]);

  const name = documentName(path);
  // On the single-pane rung the rail becomes a tabbed pane; above it, an
  // overlay drawer or a resting column.
  const showCanvas = !singlePane || activePane === 'canvas';
  // At single-pane the tab bar decides; above it the member's own show/hide
  // does. A column the member has withdrawn is not rendered at all — hiding it
  // with a class would leave its border painting a seam against the canvas.
  const showRail = singlePane ? activePane === 'chat' : sideOpen;

  return (
    <div ref={setWorkbenchNode} className="flex h-full min-h-0 flex-col">
      {/* ── ONE row: identity · verbs · view controls + boundary acts ─────
          THREE ZONES, and the middle one is the CANVAS COLUMN.

          It was two rows — a crumb row over an Insert row — and the second cost
          a full band of vertical space to hold twelve glyphs. Collapsed: the
          identity returns to the LEFT, beside the back arrow it belongs with
          (a crumb is where you came FROM, which is a left-edge fact in every
          file surface we have), and the Insert row takes the centre, where it
          sits over the page it acts on.

          The zone that matters is the middle one: at the FULL rung it is
          `FACE.column` wide and centred, matching the column the canvas
          occupies, so the verbs line up with the text they edit and nothing
          moves when the right pane opens or closes.

          THE FLANKS MUST BE `flex-1 basis-0` FOR THAT TO HOLD. The canvas
          centres itself with `margin: 0 auto`, so the chrome only agrees with it
          when the free space is split EQUALLY on both sides. Sizing the flanks
          to their content instead lands the centre wherever the left zone
          happens to end — which is what shipped, and read as "the alignment
          looks off" because it WAS off by exactly the difference between the two
          flanks' content widths.

          Column-centring is gated on `fullLabels` (the 1280px rung) because
          below it the arithmetic stops working: the column (784) plus room for
          the identity (~200) and the acts (~260) needs ~1270px, so a narrower
          pane cannot honour all three and pinning the centre would crush the
          flanks. Under that rung it degrades to an ordinary flow row — the
          verbs stay beside the identity, nothing is hidden, and the canvas is
          near enough full-width that there is no column to miss. */}
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-3 py-1.5">
        <div
          className={cn(
            'flex min-w-0 items-center gap-1.5 text-sm',
            fullLabels ? 'flex-1 basis-0' : 'shrink',
          )}
        >
          <button
            type="button"
            onClick={onClose}
            title="Back to documents"
            aria-label="Back to documents"
            className="inline-flex shrink-0 items-center rounded px-1 py-1 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          {/* The "Text /" ancestry withdraws before the NAME does — the name is
              the document's identity, the crumb is a convenience, and the back
              arrow beside it already carries the same act. Gated on the measured
              RUNG, not a `lg:` class: this surface's own width ladder is what
              decides, and a viewport breakpoint would disagree with it inside a
              narrow window (PANES.md §11). */}
          {fullLabels && (
            <>
              <button
                type="button"
                onClick={onClose}
                className="shrink-0 text-muted-foreground hover:text-foreground"
              >
                Text
              </button>
              <span className="text-muted-foreground/60">/</span>
            </>
          )}
          <button
            type="button"
            onClick={() => organizeVerbs.onRename?.({ path, name: leafOf(path) })}
            title={`${relPath(path)} — click to rename`}
            className="flex min-w-0 items-center gap-1.5 truncate rounded px-1.5 py-0.5 font-medium text-foreground/90 hover:bg-muted/50"
          >
            <FileText className="h-4 w-4 shrink-0 text-sky-600 dark:text-sky-400" aria-hidden />
            <span className="truncate">{name}</span>
          </button>
        </div>

        {/* The verbs. At the full rung the zone IS the canvas column and does
            not yield (`shrink-0`) — the toolbar keeps the page's width while the
            equal flanks absorb everything else. Below it the zone is an ordinary
            flexible cell. */}
        {/* Padded by the canvas's own gutter, so the first verb sits over the
            first CHARACTER rather than over the page's outer edge — the canvas
            pads `.cm-content` by `FACE.gutter` inside this same column. */}
        <div
          className={cn('flex min-w-0', fullLabels ? 'shrink-0' : 'shrink')}
          style={
            fullLabels
              ? { width: FACE.column, paddingLeft: FACE.gutter, paddingRight: FACE.gutter }
              : undefined
          }
        >
          <MarkdownToolbar onAction={runAction} />
        </div>

        <div
          className={cn(
            'flex min-w-0 items-center justify-end gap-2',
            fullLabels ? 'flex-1 basis-0' : 'shrink',
          )}
        >

        {/* Zoom — a VIEW control (doesn't touch the file), Docs' own clamp. */}
        <div className="hidden shrink-0 items-center gap-0.5 sm:flex">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(ZOOM_MIN, Math.round((z - 0.1) * 100) / 100))}
            className="rounded px-1.5 py-0.5 text-sm text-muted-foreground hover:bg-muted/40"
            title="Zoom out"
            aria-label="Zoom out"
          >
            −
          </button>
          <button
            type="button"
            onClick={() => setZoom(1)}
            className="min-w-[3ch] rounded px-1 py-0.5 text-[11px] tabular-nums text-muted-foreground hover:bg-muted/40"
            title="Reset zoom to 100%"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(ZOOM_MAX, Math.round((z + 0.1) * 100) / 100))}
            className="rounded px-1.5 py-0.5 text-sm text-muted-foreground hover:bg-muted/40"
            title="Zoom in"
            aria-label="Zoom in"
          >
            +
          </button>
        </div>

        {/* Save STATUS, not a save CONTROL (ADR-572 D10). Saving is automatic
            on idle/blur, so the header reports rather than asks. "Editing…"
            is deliberate over "Unsaved changes": nothing is at risk, so the
            copy should not imply it is. */}
        <span
          className="hidden shrink-0 items-center gap-1 text-[11px] text-muted-foreground lg:flex"
          aria-live="polite"
        >
          {saving ? (
            <>
              <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> Saving…
            </>
          ) : conflict ? (
            // ADR-575. A conflict SUSPENDS autosave (the effect returns early
            // on `conflict`), so the surface must not keep saying "Editing…",
            // whose whole point is that nothing is at risk. During a conflict
            // something is: nothing will be written until the member chooses.
            <span className="flex items-center gap-1 text-amber-600">
              <AlertTriangle className="h-3 w-3" aria-hidden /> Paused — resolve above
            </span>
          ) : dirty ? (
            'Editing…'
          ) : savedAt ? (
            <>
              <Check className="h-3 w-3" aria-hidden /> Saved
            </>
          ) : (
            `${words} words`
          )}
        </span>

        <TextExport
          share={() => setShareTarget({ path, name: leafOf(path) })}
          text={text}
          name={name}
          path={path}
          compact={!fullLabels}
        />

        {/* The side pane's DOOR — at every rung that HAS a side pane, not only
            where it is an overlay. The overlay rung already dismisses itself;
            the COLUMN rung was the one permanently spending width with no way
            to reclaim it. Hidden at single-pane, where the bottom tab bar is
            the switcher. */}
        {!singlePane && (
          <button
            type="button"
            onClick={side.toggle}
            title={`${sideOpen ? 'Hide' : 'Show'} properties and chat`}
            aria-label={`${sideOpen ? 'Hide' : 'Show'} properties and chat`}
            aria-expanded={sideOpen}
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded border border-border text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
          >
            <PanelRight className="h-3.5 w-3.5" />
          </button>
        )}
        </div>
      </div>

      {/* ── Canvas + rail ─────────────────────────────────────────────── */}
      <div className="relative flex min-h-0 flex-1">
        {showCanvas && (
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          {/* ADR-575 — the peer-write notice. Shown when someone else's
              revision lands WHILE the member has unsaved text, which is the
              moment the old design said nothing and then raised a 409 at save
              time. It is informational, not a decision: the member's text is
              untouched and saving still works (their save will simply be the
              one that moves the head). Suppressed once a real conflict is up,
              so the surface never stacks two amber bars saying similar things. */}
          {peerEdit && !conflict && (
            <div className="border-b border-border bg-muted/40 px-4 py-2 text-xs">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <div className="space-y-2">
                  <p className="text-muted-foreground">
                    <span className="font-medium text-foreground">
                      {formatAuthorLabel(peerEdit.actor) || peerEdit.actor}
                    </span>{' '}
                    saved a new version of this document
                    {peerEdit.at ? ` ${formatRelativeTime(peerEdit.at, { rollToDate: true })}` : ''}.
                    Your text here is untouched — saving will put your version on top.
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => { setPeerEdit(null); setReloadKey((n) => n + 1); }}
                      className="rounded-md border border-border px-2 py-1 hover:bg-muted/40"
                    >
                      Discard mine, show theirs
                    </button>
                    <button
                      type="button"
                      onClick={() => setPeerEdit(null)}
                      className="rounded-md px-2 py-1 text-muted-foreground hover:bg-muted/40"
                    >
                      Keep writing
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
          {conflict && (
            <div className="border-b border-amber-500/40 bg-amber-500/10 px-4 py-2 text-xs">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
                <div className="space-y-2">
                  <p>
                    <span className="font-medium">{conflict.actor}</span> revised this
                    document while you were editing. Your text is still here — nothing
                    was lost, and nothing merges silently.
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => { setConflict(null); setReloadKey((n) => n + 1); }}
                      className="rounded-md border border-border px-2 py-1 hover:bg-muted/40"
                    >
                      Discard mine, show theirs
                    </button>
                    {/* ADR-572 D11 — the override is ALWAYS offered.
                        It was conditional on `currentHeadId`, so whenever the
                        server could not name the head the button silently
                        vanished and the member was left with one exit where
                        the design promises two. D7 fixed one cause of that
                        (an envelope mismatch); the condition itself was the
                        deeper defect, because ANY future cause reproduces it.
                        `null` means "write regardless of head" — the same
                        force-overwrite the member is asking for, so the
                        affordance no longer depends on the diagnosis. */}
                    <button
                      type="button"
                      // Commit against THEIR head — the explicit override.
                      // Passing the head explicitly (even as null) bypasses
                      // the no-op guard, so this always writes.
                      onClick={() => void commit(conflict.currentHeadId)}
                      className="rounded-md border border-border px-2 py-1 hover:bg-muted/40"
                    >
                      Save mine over theirs
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
          {saveError && (
            <p className="border-b border-destructive/30 bg-destructive/5 px-4 py-2 text-xs text-destructive">
              {saveError}
            </p>
          )}

          {loading ? (
            <div className="flex flex-1 items-center justify-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Opening…
            </div>
          ) : notFound ? (
            <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-muted-foreground">
              Nothing exists at <span className="mx-1 font-mono text-xs">{relPath(path)}</span> —
              it may have been moved or never written.
            </div>
          ) : error ? (
            /* A real failure says so, and offers the retry — never "it doesn't
               exist", which reads as data loss (the Docs honesty rule). */
            <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
              <p className="text-sm text-muted-foreground">
                Couldn’t load {relPath(path)}. The document is still there — the
                request failed.
              </p>
              <button
                type="button"
                onClick={() => setReloadKey((n) => n + 1)}
                className="rounded border border-border px-2.5 py-1 text-xs hover:bg-muted/40"
              >
                Try again
              </button>
            </div>
          ) : (
            // ── ONE canvas: always editable, always styled (ADR-572 D8).
            //    The Insert verbs are a permanent part of the header row, not a
            //    mode-gated band — nothing here is hidden behind a state the
            //    surface doesn't open in, which is what the Read/Write split
            //    did. They moved INTO the header (one row, three zones) rather
            //    than sitting in a band of their own above this canvas.
            <>
              <ProseCanvas
                value={text}
                onChange={setText}
                onSlashRun={setSlash}
                onSelectionChange={onCanvasSelection}
                handleRef={(h) => { canvasRef.current = h; }}
                zoom={zoom}
              />
              {slashOpen && slashCoords && (
                <SlashMenu
                  items={slashItems}
                  active={slashIndex}
                  coords={slashCoords}
                  onPick={takeSlash}
                  onHover={setSlashIndex}
                />
              )}
              {/* ADR-612 D1 — the judged act, at the thing it acts on. Yields
                  to the slash palette: both anchor off the same canvas, and
                  two floating doors at one caret is a collision, not a
                  choice. */}
              {!slashOpen && (
                <SelectionGesture
                  anchor={selectionAnchor}
                  label="the selection"
                  onClick={rewriteSelection}
                  pending={pendingRewrite !== null}
                />
              )}
            </>
          )}
        </main>
        )}

        {/* The rail — Properties | Chat, Docs' grammar. At the narrow rungs it
            becomes an overlay with a header door; at the narrowest it is a
            pane the bottom bar switches to (never an unreachable pane). */}
        {/* The resize divider — a column edge, so only where the pane IS a
            column. An overlay is dismissed, not resized. */}
        {slotIsColumn(wb, side) && (
          <div
            onPointerDown={side.startResize}
            role="separator"
            aria-orientation="vertical"
            title="Drag to resize"
            className="w-1 shrink-0 cursor-col-resize bg-transparent transition-colors hover:bg-primary/20 active:bg-primary/30"
          />
        )}
        {showRail && (
        <aside
          style={slotIsColumn(wb, side) ? { width: side.width } : undefined}
          className={cn(
            'flex min-h-0 flex-col border-border bg-background',
            singlePane
              ? 'min-w-0 flex-1'
              : sideIsOverlay
                ? cn('absolute inset-y-0 right-0 z-20 w-[min(22rem,85vw)] border-l shadow-lg', sideOpen ? 'flex' : 'hidden')
                : 'shrink-0 border-l',
          )}
        >
          <div className="flex shrink-0 border-b border-border">
            {([['properties', 'Properties'], ['chat', 'Chat']] as const).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setRightTab(tab)}
                className={cn(
                  'flex-1 py-1.5 text-[11px] font-medium transition-colors',
                  rightTab === tab
                    ? 'border-b-2 border-foreground text-foreground'
                    : 'border-b-2 border-transparent text-muted-foreground hover:text-foreground',
                )}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Properties — what a prose document HAS. Docs' inspector answers
              block properties AND carries the document's Outline (ADR-526 D2
              put the outline in the pane, not a rail); Text mirrors the
              outline and answers the document itself for the rest. */}
          <div className={cn('min-h-0 flex-1 overflow-auto', rightTab === 'properties' ? 'block' : 'hidden')}>
            <div className="space-y-4 p-3 text-xs">
              {/* The file itself — the same organize verbs every other surface
                  offers, behind the Docs FILE-card `⋯` served from the SHARED
                  menu (ADR-572 D10). NO "File" heading: the icon + name + ⋯
                  already say what this row is, and the label cost a whole
                  line that the name now spends on itself. */}
              <section className="space-y-1">
                <div className="flex items-center gap-1.5">
                  <FileText className="h-4 w-4 shrink-0 text-sky-600 dark:text-sky-400" />
                  <span className="min-w-0 flex-1 truncate text-xs font-medium" title={relPath(path)}>
                    {leafOf(path)}
                  </span>
                  <button
                    type="button"
                    aria-label="File actions"
                    title="File actions"
                    onClick={(e) => openMenuFromButton({ path, name: leafOf(path), isFile: true }, e)}
                    className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </button>
                </div>
                <p className="break-all font-mono text-[10px] text-muted-foreground">{relPath(path)}</p>
              </section>

              {/* The OUTLINE — Docs' own pane section, addressed by SOURCE
                  LINE rather than by block id (ADR-572 D3). A line number is
                  a coordinate into the bytes, not an annotation on them. */}
              <section className="space-y-1">
                <p className={PANE_HEADING}>
                  Outline
                </p>
                {outline.length > 0 ? (
                  <ul className="space-y-px">
                    {outline.map((h) => (
                      <li key={`${h.line}-${h.text}`}>
                        <button
                          type="button"
                          onClick={() => {
                            // Address the whole heading LINE, never the
                            // outline's label: `plain()` strips `#`, `**` and
                            // link targets, so a label-derived length is short
                            // by exactly the markup (ADR-572 D20).
                            const off = offsetOfLine(text, h.line);
                            const nl = text.indexOf('\n', off);
                            reveal([off, nl === -1 ? text.length : nl]);
                          }}
                          title={h.text}
                          style={{ paddingLeft: `${(h.level - 1) * 10}px` }}
                          className="flex w-full items-baseline truncate rounded px-1 py-px text-left text-[10px] text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
                        >
                          <span className="truncate">{h.text}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : (
                  // The honest empty state — never invent a structure the
                  // document doesn't have (Docs' rule, ADR-526 §7).
                  <p className="text-[10px] text-muted-foreground">
                    No headings yet — add one and it appears here.
                  </p>
                )}
              </section>

              {/* ── THE READBACK TAIL (lib/authoring/pane-spine) ──────────────
                  Everything below is a FACT about the document, not a control.
                  The shared spine puts Identity first, controls next, readback
                  last — so the member's eye lands on the subject, walks what
                  they can change, and finds the facts where facts always are.

                  Text has no control rungs at all (markdown has no box, so no
                  Position or Layout), which is exactly why the tail had to be
                  named: without it, conforming would have meant rendering
                  sections this app does not have. "Last edited" used to sit
                  ABOVE Length and Format — one fact interleaved with two, for
                  no reason but the order they were written in. */}
              <section className="space-y-1">
                <p className={PANE_HEADING}>
                  Length
                </p>
                <p className="text-muted-foreground">
                  {words.toLocaleString()} words · {text.length.toLocaleString()} characters
                </p>
                <p className="text-muted-foreground">
                  {outline.length.toLocaleString()} heading{outline.length === 1 ? '' : 's'} ·
                  {' '}about {readingMinutes(words)} min read
                </p>
              </section>

              <section className="space-y-1">
                <p className={PANE_HEADING}>
                  Format
                </p>
                <p className="text-muted-foreground">
                  Markdown, plain text. It stays a <span className="font-mono">.md</span> file —
                  the same one your connectors read and write.
                </p>
              </section>

              <section className="space-y-1">
                <p className={PANE_HEADING}>
                  Last edited
                </p>
                {headRevision ? (
                  <p className="text-muted-foreground">
                    {formatAuthorLabel(headRevision.authored_by) || headRevision.authored_by}
                    {headRevision.created_at
                      ? ` · ${formatRelativeTime(headRevision.created_at, { rollToDate: true })}`
                      : ''}
                  </p>
                ) : (
                  <p className="text-muted-foreground">No revisions yet.</p>
                )}
                <p className="text-muted-foreground/80">
                  Every save is signed and revertible — the full history lives in
                  Files → Get Info.
                </p>
              </section>

            </div>
          </div>

          {/* Chat — Editor's bound lane. Mounted always, hidden by CSS. */}
          <div className={cn('min-h-0 flex-1 flex-col', rightTab === 'chat' ? 'flex' : 'hidden')}>
            {lanesEnabled === false ? (
              <div className="flex flex-1 items-center justify-center p-6 text-center text-sm text-muted-foreground">
                Lanes are not enabled on this deployment — Editor needs the model
                router. The document still opens and saves.
              </div>
            ) : boundLane ? (
              <LanePanel
                key={boundLane.id}
                laneId={boundLane.id}
                laneName={boundLane.name}
                modelLabel={modelLabel}
                speakerLabel={speakerLabel}
                artifactWrite="none"
                onSeededTurn={(running) => {
                  // ADR-612 D4 — the ONE moment the act becomes real: a turn
                  // carrying this desk's gesture has gone up. `false` settles
                  // it however it ended (reply, refusal, error, stop) — the
                  // write-landing path clears it first when there was one.
                  if (running) {
                    // One arming feeds two lifetimes: the spinner (ends when
                    // the turn settles) and the landing (ends when the WRITE
                    // arrives, which is later).
                    setPendingRewrite(armedRewriteRef.current);
                    landingTargetRef.current = armedRewriteRef.current;
                    armedRewriteRef.current = null;
                  } else {
                    setPendingRewrite(null);
                  }
                }}
                onArtifactWrite={() => {
                  // Hold the text as it stands BEFORE the refetch: the landing
                  // is computed by diffing it against what arrives (D5).
                  preWriteRef.current = textRef.current;
                  setReloadKey((n) => n + 1);
                }}
                suggestions={SUGGESTIONS}
              composerSeed={seed}
                emptyState={
                  <div className="space-y-2 text-center text-xs text-muted-foreground">
                    <p className="text-sm font-medium text-foreground/80">Editor is reading this document.</p>
                    <p>
                      Ask for a tighter draft, a restructure, or a second opinion —
                      every change lands as a signed revision on{' '}
                      <span className="font-medium text-foreground/70">{leafOf(path)}</span>,
                      and the page updates as it works.
                    </p>
                  </div>
                }
              />
            ) : (
              <div className="flex flex-1 items-center justify-center gap-2 p-6 text-xs text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" /> Opening Editor…
              </div>
            )}
          </div>
        </aside>
        )}
      </div>

      {/* The single-pane rung's bottom tab bar: one pane at a time. 44px is
          the touch floor (Apple/Google) and this is the PRIMARY navigation on
          a phone — the Docs ladder's last rung, ported. */}
      {singlePane && (
        <nav className="flex shrink-0 border-t border-border">
          {([['canvas', 'Document'], ['chat', 'Editor']] as const).map(([pane, label]) => (
            <button
              key={pane}
              type="button"
              onClick={() => setActivePane(pane)}
              className={cn(
                'min-h-[44px] flex-1 py-2 text-xs font-medium transition-colors',
                activePane === pane
                  ? 'border-t-2 border-foreground text-foreground'
                  : 'border-t-2 border-transparent text-muted-foreground',
              )}
            >
              {label}
            </button>
          ))}
        </nav>
      )}

      {picker && (
        <StudioCitablePicker
          // `table` makes the picker title read "Insert a table from a CSV",
          // which it already carried for Docs; `cites` switches the listing
          // between the two arrays the endpoint already returns.
          kind={picker.for === 'csvtable' ? 'table' : 'figure'}
          cites={picker.for === 'csvtable' ? 'source' : 'picture'}
          left={Math.round(window.innerWidth / 2) - 150}
          top={Math.round(window.innerHeight / 3)}
          onPickOne={(p) => (picker.for === 'csvtable' ? void takeCsv(p) : takeImage(p))}
          // Gallery is Docs' multi-select, and it does not translate: a gallery
          // is a CSS grid over N citations, which in markdown degrades to N
          // consecutive images — i.e. to using Image N times. So the door is
          // single-pick, and the callback is a no-op rather than absent.
          onPickGallery={() => setPicker(null)}
          onClose={() => setPicker(null)}
        />
      )}
      {/* ADR-572 D18's CSV notice now rides the canonical toast layer
          (runAction in takeCsv) — the hand-rolled bottom-center div is
          deleted (transient-surfacing streamline 2026-08-22). */}
      {organizeModals}
      {fileMenu}
      <ShareDialog target={shareTarget} onClose={() => setShareTarget(null)} />
    </div>
  );
}
