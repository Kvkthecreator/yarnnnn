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
import { useFileLoad } from '@/components/workspace/useFileLoad';
import { useFileContextMenu } from '@/components/workspace/FileContextMenu';
import { useFileOrganizeVerbs } from '@/hooks/useFileOrganizeVerbs';
import { formatAuthorLabel } from '@/lib/workspace/attribution';
import { formatRelativeTime } from '@/lib/formatting';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { ShareDialog } from '@/components/workspace/ShareDialog';
import { TextExport } from '@/components/text/TextExport';
import { ProseCanvas, type ProseCanvasHandle, type SlashRun } from '@/components/text/ProseCanvas';
import { MarkdownToolbar, type ToolbarAction } from '@/components/text/MarkdownToolbar';
import { SlashMenu, filterSlashItems, type SlashItem } from '@/components/text/SlashMenu';
import { StudioCitablePicker } from '@/components/authoring/StudioCitablePicker';
import { readConflict, type ConflictState } from '@/components/text/conflict';
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
import { useWorkbenchWidth } from '@/lib/authoring/workbench-width';
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
  const [setWorkbenchNode, wb] = useWorkbenchWidth();
  const [reloadKey, setReloadKey] = useState(0);
  const { file, loading, notFound, error, headRevision } = useFileLoad(path, {
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

  // ── View state (ADR-572 D2) — zoom only; it never touches the file.
  const [zoom, setZoom] = useState(1);

  // Rail: Properties | Chat, the Docs grammar. The lane stays MOUNTED while
  // Properties is up (CSS-hidden) so a streaming turn survives the switch.
  const [rightTab, setRightTab] = useState<'properties' | 'chat'>('properties');
  const [sideOpen, setSideOpen] = useState(true);
  const { sideIsOverlay, singlePane, fullLabels } = wb;
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
          baseHead.current = (res as { head_version_id?: string }).head_version_id ?? null;
          setBaseline(body);
          setConflict(null);
          setSavedAt(Date.now());
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
    [path, onSaved],
  );

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
  /** Set while a picked CSV is being read, so the pane can say so. */
  const [csvLoading, setCsvLoading] = useState(false);

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
      setCsvLoading(true);
      try {
        const file = await api.workspace.getFile(relPath(path));
        const current = canvasRef.current?.text() ?? text;
        const where = Math.min(at, current.length);
        applyEdit(insertCsvTable(current, where, where, relPath(path), file.content ?? '', new Date()));
      } catch {
        // A read that fails writes NOTHING. A source note with no rows under
        // it would read as "that file is empty", which is a different and
        // false claim — the file may be fine and the request may not have been.
        setCsvError(relPath(path));
      } finally {
        setCsvLoading(false);
      }
    },
    [picker, text, applyEdit],
  );

  const [csvError, setCsvError] = useState<string | null>(null);
  useEffect(() => {
    if (!csvError) return;
    const t = setTimeout(() => setCsvError(null), 6000);
    return () => clearTimeout(t);
  }, [csvError]);

  /** Select a source range and scroll it into view (the outline jump). */
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
  const [models, setModels] = useState<LanesEnv['models']>([]);
  const [creatingLane, setCreatingLane] = useState(false);

  const refreshLanes = useCallback(async () => {
    try {
      const env = await api.lanes.list(true);
      setLanesEnabled(env.enabled);
      setLanes(env.lanes ?? []);
      setAgents(env.agents ?? []);
      setApps(env.apps ?? []);
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
    const slug = boundLane?.agent;
    if (slug) {
      const appName = apps.find((a) => a.slug === 'text')?.name;
      if (appName) return appName;
      const named = agents.find((a) => a.slug === slug)?.name;
      if (named) return named;
    }
    return modelLabel;
  }, [agents, apps, boundLane, modelLabel]);

  const words = useMemo(
    () => (text.trim() ? text.trim().split(/\s+/).length : 0),
    [text],
  );
  const outline = useMemo(() => parseOutline(text), [text]);

  const name = documentName(path);
  // On the single-pane rung the rail becomes a tabbed pane; above it, an
  // overlay drawer or a resting column.
  const showCanvas = !singlePane || activePane === 'canvas';
  const showRail = singlePane ? activePane === 'chat' : true;

  return (
    <div ref={setWorkbenchNode} className="flex h-full min-h-0 flex-col">
      {/* ── The crumb row + view controls + boundary acts ───────────────── */}
      <div className="flex shrink-0 items-center gap-2 border-b border-border px-3 py-1.5">
        <button
          type="button"
          onClick={onClose}
          title="Back to documents"
          aria-label="Back to documents"
          className="inline-flex shrink-0 items-center rounded px-1.5 py-1 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
        </button>
        <div className="flex min-w-0 items-center gap-1.5 text-sm">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            Text
          </button>
          <span className="text-muted-foreground/60">/</span>
          <button
            type="button"
            onClick={() => organizeVerbs.onRename?.({ path, name: leafOf(path) })}
            title={`${relPath(path)} — click to rename`}
            className="flex max-w-[26ch] items-center gap-1.5 truncate rounded px-1 py-0.5 font-medium text-foreground/80 hover:bg-muted/50"
          >
            <FileText className="h-3.5 w-3.5 shrink-0 text-sky-600 dark:text-sky-400" aria-hidden />
            <span className="truncate">{name}</span>
          </button>
        </div>

        <div className="min-w-0 flex-1" />

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

        {sideIsOverlay && !singlePane && (
          <button
            type="button"
            onClick={() => setSideOpen((v) => !v)}
            title="Properties and chat"
            aria-label="Properties and chat"
            aria-expanded={sideOpen}
            className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded border border-border text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
          >
            <PanelRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* ── Canvas + rail ─────────────────────────────────────────────── */}
      <div className="relative flex min-h-0 flex-1">
        {showCanvas && (
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
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
            //    The toolbar is a permanent row above it, not a mode-gated
            //    one — nothing here is hidden behind a state the surface
            //    doesn't open in, which is what the Read/Write split did.
            <>
              <MarkdownToolbar onAction={runAction} />
              <ProseCanvas
                value={text}
                onChange={setText}
                onSlashRun={setSlash}
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
            </>
          )}
        </main>
        )}

        {/* The rail — Properties | Chat, Docs' grammar. At the narrow rungs it
            becomes an overlay with a header door; at the narrowest it is a
            pane the bottom bar switches to (never an unreachable pane). */}
        {showRail && (
        <aside
          className={cn(
            'flex min-h-0 flex-col border-border bg-background',
            singlePane
              ? 'min-w-0 flex-1'
              : sideIsOverlay
                ? cn('absolute inset-y-0 right-0 z-20 w-[min(22rem,85vw)] border-l shadow-lg', sideOpen ? 'flex' : 'hidden')
                : 'w-80 shrink-0 border-l',
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
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Outline
                </p>
                {outline.length > 0 ? (
                  <ul className="space-y-px">
                    {outline.map((h) => (
                      <li key={`${h.line}-${h.text}`}>
                        <button
                          type="button"
                          onClick={() => {
                            const off = offsetOfLine(text, h.line);
                            reveal([off, off + h.text.length]);
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

              <section className="space-y-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
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

              <section className="space-y-1">
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
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
                <p className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                  Format
                </p>
                <p className="text-muted-foreground">
                  Markdown, plain text. It stays a <span className="font-mono">.md</span> file —
                  the same one your connectors read and write.
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
                onArtifactWrite={() => setReloadKey((n) => n + 1)}
                suggestions={SUGGESTIONS}
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
      {/* ADR-572 D18 — a CSV read is the one insert that can be slow or fail,
          so it says so. Silence during the fetch reads as a dead click, and a
          silent failure reads as "that file was empty". */}
      {(csvLoading || csvError) && (
        <div
          role="status"
          className="fixed bottom-4 left-1/2 z-50 -translate-x-1/2 rounded-md border border-border bg-popover px-3 py-1.5 text-xs shadow-md"
        >
          {csvLoading ? (
            <span className="text-muted-foreground">Reading the CSV…</span>
          ) : (
            <span className="text-destructive">Couldn’t read {csvError} — nothing was inserted.</span>
          )}
        </div>
      )}
      {organizeModals}
      {fileMenu}
      <ShareDialog target={shareTarget} onClose={() => setShareTarget(null)} />
    </div>
  );
}
