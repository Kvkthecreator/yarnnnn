'use client';

/**
 * StringsSurface — Supervisor's desk over the maintained file (ADR-569 →
 * ADR-604/610): Supervisor is the conversation about standing work AND
 * the standing executor whose face is on every run receipt.
 *
 * A STRING is the member's designation of one file as kept current: a
 * contract (CONTRACT.md — what it must stay true to), sources (where currency
 * comes from), a cadence, and the standing run revising the head while the
 * member corrects it like any file.
 *
 * THE TENDING SURFACE (ADR-595): this pane shows the file's SITUATION —
 * currency, provenance, governance, audience — and never the file's
 * contents. Reading and correcting happen at the file's own surface (the
 * Open door); the desk view doesn't even carry the head (D1 — enforced at
 * the API). Four tabs (D2): Overview (status + the N→1 flow strip) ·
 * Sources (each source as a PARTY: standing, receipts, contribution) ·
 * Activity (the attributed rail) · Contract (the terms). Loud states render
 * ABOVE the tabs — a repair is never hidden behind one.
 *
 * The chrome is the shared `DeskHousing` (ADR-569 D6 — the second tenant;
 * radar was the first). This file keeps what is STRINGS': the string state
 * machine, the params, the format renderers, and every operator word.
 *
 * The desk's identity is the `strings.topic` param (the folder — one string
 * per folder, v1). `strings.target` carries a designation-in-flight's leaf so
 * a refresh resumes the unconfigured desk with its lane intact; the desk
 * promotes itself the moment the declaration parses (the substrate is
 * the state machine, ADR-567 D3). `strings.file` is inbound transport from
 * Files ("Keep this current…"), drained on the param VALUE (the 3f44a8f
 * lesson), never at mount.
 *
 * Creation is conversational with exactly ONE direct gesture — the file pick
 * (an existing file, or a folder plus a name for the new leaf). Direct
 * switches stay direct: Pause/Resume and Run now.
 */

import { useCallback, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  ArrowRight, Cable, ChevronDown, ExternalLink, FileText, Globe, Loader2,
  MessageSquare, Pause, Play, Plus, RefreshCw, X, Zap,
} from 'lucide-react';
import {
  api, type StringSource, type StringSummary, type StringView,
} from '@/lib/api/client';
import { scheduleDisplay } from '@/lib/schedule';
import {
  useSurfaceParam, useSurfacePreferences,
} from '@/lib/shell/useSurfacePreferences';
import { useDeclareFocus } from '@/lib/shell/useSurfaceFocus';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { WorkspacePickerBody } from '@/components/workspace/WorkspacePicker';
import { DeskHousing, type DeskContext } from '@/components/desk/DeskHousing';
import {
  DeskActivityRail, type RailEvent,
} from '@/components/desk/DeskActivityRail';
import { FRESHNESS_PROVIDERS } from '@/lib/connectors/registry';
import type { WorkspaceTreeNode } from '@/types';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

const WORKSPACE_ROOT = '/workspace';

/** The v1 designation scope (ADR-569 D1) — mirrors SUPPORTED_FORMATS
 *  server-side; the picker refuses outside it rather than letting the kernel
 *  refuse later. */
const DESIGNATABLE_RE = /\.(md|csv|json|txt)$/i;

function isDesignatable(leaf: string): boolean {
  return (
    DESIGNATABLE_RE.test(leaf) &&
    !leaf.startsWith('_') &&
    leaf !== 'CONTRACT.md'
  );
}

function relPath(abs: string): string | null {
  if (!abs.startsWith(`${WORKSPACE_ROOT}/`)) return null;
  return abs.slice(WORKSPACE_ROOT.length + 1);
}

function fmtWhen(iso?: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  });
}

const kebab = (s: string) =>
  s.trim().toLowerCase().replace(/[^a-z0-9.]+/g, '-').replace(/^-+|-+$/g, '');

/** What the desk knows about the selected folder. The substrate is the state
 *  machine: `unconfigured` = no declaration YET (a fresh designation, or one
 *  setup is mid-flight on); `repair` = the declaration exists and fails to
 *  parse (the loud state — ADR-567 D6 / ADR-569 D3). A PARSEABLE declaration
 *  in trouble (problem / refused write) arrives as `ready` and renders its
 *  own loud cards. */
type DeskState =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'ready'; view: StringView }
  | { phase: 'unconfigured'; contract: string | null }
  | { phase: 'repair'; detail: string }
  | { phase: 'error'; detail: string };

const SETUP_SUGGESTIONS = [
  'This file must stay true to: ',
  'Pull from this source: ',
  'Refresh it every morning and keep it current.',
];

/** One selected slice on a connection — an aperture chip the setup pane
 *  offers as a source (ADR-595 D4: the aperture surfaced at designation,
 *  where it matters, instead of failing later as an out-of-selection source). */
interface ApertureSlice {
  provider: string;
  id: string;
  name: string | null;
}

const CADENCE_PRESETS: Array<{ label: string; seed: string }> = [
  { label: 'every morning', seed: 'Refresh it every morning and keep it current.' },
  { label: 'hourly', seed: 'Refresh it hourly.' },
  { label: 'weekly', seed: 'Refresh it weekly, Monday morning.' },
];

const TUNE_SUGGESTIONS = [
  'What changed in the last run?',
  'Tighten the contract: ',
  'Change the cadence: ',
];

// ── Strings' vocabulary for the shared activity rail ────────────────────────

function stringsAuthorLabel(authoredBy: string): string | undefined {
  return authoredBy === 'system:strings' ? 'Supervisor' : undefined;
}

function stringsAuthorChip(authoredBy: string): string | undefined {
  return authoredBy === 'system:strings'
    ? 'bg-emerald-500/10 text-emerald-700 border-emerald-500/30'
    : undefined;
}

function runStatusLine(e: RailEvent): string {
  if (e.status === 'skipped' && e.error_reason === 'no_change')
    return 'Run — nothing changed';
  if (e.status === 'skipped' && e.error_reason === 'router_disabled')
    return 'Run skipped — the engine is unavailable';
  if (e.status === 'skipped')
    return `Run skipped${e.error_reason ? ` — ${e.error_reason}` : ''}`;
  if (e.error_reason === 'shape_violation')
    return 'Update refused — the fetched data broke the declared shape';
  if (e.error_reason === 'no_sources_fetched')
    return 'Fetch failed — no source could be read';
  return `Run failed${e.error_reason ? ` — ${e.error_reason}` : ''}`;
}

// The private format renderers are DELETED (ADR-595 D1): the tending surface
// never renders the maintained file — the OS owns exactly one reading face
// and one editing face, and this pane hands you the door instead.

// ── The tabs (ADR-595 D2) — remembered posture, `strings.tab` ───────────────

const STRINGS_TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'sources', label: 'Sources' },
  { key: 'activity', label: 'Activity' },
  { key: 'contract', label: 'Contract' },
] as const;
type StringsTab = (typeof STRINGS_TABS)[number]['key'];

//: The arity law (server: `_classify_sources`) — stated in the pane, not
//: discovered by refusal.
const PROSE_SOURCE_CAP = 12;

// ── Operator words for the problem states (D3 — served loudly) ──────────────

const PROBLEM_COPY: Record<string, string> = {
  missing_target: 'The declaration names no target file. Ask Supervisor to declare which file this string keeps current.',
  invalid_target: 'The declared target is not a plain file in this folder. Ask Supervisor to point the string at a single file here.',
  unsupported_format: 'The declared target is a format the standing run does not maintain (v1 keeps md, csv, json and txt — an authored artifact stays current through reference instead).',
  sources_invalid: 'The declared sources cannot run — a structured format keeps exactly one source (an http(s) endpoint or a connector slice). Ask Supervisor to repair the source list.',
};

export default function StringsSurface() {
  const { navigateToSurface } = useSurfacePreferences();
  const param = useSurfaceParam('strings');

  const topic = param.get('topic');
  const targetParam = param.get('target');
  const deskRoot = topic ? `${WORKSPACE_ROOT}/${topic}` : null;

  // The tab (ADR-595 D2) — remembered posture; 'overview' is the unset default.
  const tabRaw = param.get('tab');
  const tab: StringsTab = STRINGS_TABS.some((t) => t.key === tabRaw)
    ? (tabRaw as StringsTab)
    : 'overview';
  const setTab = useCallback(
    (t: StringsTab) => param.set({ tab: t === 'overview' ? null : t }),
    [param],
  );

  const [strings, setStrings] = useState<StringSummary[] | null>(null);
  const [desk, setDesk] = useState<DeskState>({ phase: 'idle' });
  //: The aperture chips for the setup pane — selected slices across the
  //: member's connections. null = not loaded; [] = loaded, none selected.
  const [apertureSlices, setApertureSlices] = useState<ApertureSlice[] | null>(null);
  const [attachOpen, setAttachOpen] = useState(false);
  const [activityNonce, setActivityNonce] = useState(0);
  const [switcherOpen, setSwitcherOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [runNote, setRunNote] = useState<string | null>(null);

  const view = desk.phase === 'ready' ? desk.view : null;

  // The lane's binding leaf: the declared target once it parses, else the
  // designation-in-flight's picked leaf (the `target` param) — so the
  // unconfigured desk still seats the desk voice (Supervisor, ADR-604).
  const artifactPath =
    view?.target && deskRoot
      ? `${deskRoot}/${view.target}`
      : targetParam && deskRoot
        ? `${deskRoot}/${targetParam}`
        : null;

  // ADR-522 — the desk declares its focus: the maintained file is the unit.
  useDeclareFocus(
    'strings',
    topic
      ? {
          app: 'strings',
          path: artifactPath ?? (deskRoot ? `${deskRoot}/_string.yaml` : null),
          scope: 'document',
          id: null,
          pageIndex: null,
          label: view?.target ?? targetParam ?? topic,
          excerpt: null,
          viewport: null,
        }
      : null,
  );

  const loadStrings = useCallback(async (): Promise<StringSummary[]> => {
    try {
      const rows = await api.strings.list();
      setStrings(rows);
      return rows;
    } catch {
      setStrings([]);
      return [];
    }
  }, []);

  const loadDesk = useCallback(async (t: string) => {
    setDesk((d) => (d.phase === 'ready' ? d : { phase: 'loading' }));
    try {
      const v = await api.strings.get(t);
      setDesk({ phase: 'ready', view: v });
    } catch (e) {
      const status = (e as { status?: number })?.status;
      if (status === 404) {
        // No declaration yet — the unconfigured desk. Show the contract if
        // the lane has already authored one (setup lands file by file).
        let contract: string | null = null;
        try {
          const f = await api.workspace.getFile(`${WORKSPACE_ROOT}/${t}/CONTRACT.md`);
          contract = f?.content ?? null;
        } catch { /* not written yet */ }
        setDesk({ phase: 'unconfigured', contract });
      } else if (status === 422) {
        // The declaration exists and fails to parse — the loud repair state.
        setDesk({
          phase: 'repair',
          detail: e instanceof Error ? e.message : 'declaration unparseable',
        });
      } else {
        setDesk({
          phase: 'error',
          detail: e instanceof Error ? e.message : 'the folder could not be read',
        });
      }
    }
  }, []);

  // ONE arrival door: `strings.file` is inbound transport — Files delivering
  // "Keep this current…" with a file (or a declaration) path. Drained keyed
  // on the param VALUE (desktop mode delivers params to mounted surfaces —
  // the 3f44a8f defect shape), converted to topic/target and cleared.
  const fileParam = param.get('file');
  useEffect(() => {
    if (!fileParam) return;
    const rel = relPath(fileParam);
    if (!rel) { param.set({ file: null }); return; }
    if (rel.endsWith('/_string.yaml')) {
      param.set({ topic: rel.slice(0, -'/_string.yaml'.length), target: null, file: null });
    } else if (rel.includes('/')) {
      const leaf = rel.slice(rel.lastIndexOf('/') + 1);
      const folder = rel.slice(0, rel.lastIndexOf('/'));
      param.set(
        leaf.includes('.')
          ? { topic: folder, target: leaf, file: null }
          : { topic: rel, target: null, file: null }, // a folder path
      );
    } else {
      // A bare top-level name is a folder (a file at the workspace root has
      // no folder to hold its string).
      param.set({ topic: rel, target: null, file: null });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileParam]);

  // Mount: the roster; a bare launch with no topic rests on the first string.
  useEffect(() => {
    void (async () => {
      const rows = await loadStrings();
      if (!param.get('topic') && !param.get('file') && rows.length > 0) {
        param.set({ topic: rows[0].topic });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (topic) void loadDesk(topic);
    else setDesk({ phase: 'idle' });
  }, [topic, loadDesk]);

  // The setup pane's aperture chips (ADR-595 D4) — loaded once, on first
  // entering the unconfigured state. Best-effort per provider: an
  // unconnected platform simply contributes no chips.
  useEffect(() => {
    if (desk.phase !== 'unconfigured' || apertureSlices !== null) return;
    void (async () => {
      const results = await Promise.all(
        FRESHNESS_PROVIDERS.map(async (p) => {
          try {
            const signal = await api.integrations.getCaptureSignal(
              p as 'slack' | 'notion' | 'github',
            );
            return (signal.declared ?? [])
              .filter((d) => d.selected)
              .map((d) => ({ provider: p, id: d.id, name: d.name }));
          } catch {
            return [];
          }
        }),
      );
      setApertureSlices(results.flat());
    })();
  }, [desk.phase, apertureSlices]);

  const selectTopic = useCallback((t: string, target?: string | null) => {
    param.set({ topic: t, target: target ?? null, file: null });
    setSwitcherOpen(false);
    setRunNote(null);
  }, [param]);

  const togglePause = useCallback(async () => {
    if (!view) return;
    const updated = await api.strings.update(view.topic, { paused: !view.paused });
    setDesk((d) =>
      d.phase === 'ready' ? { ...d, view: { ...d.view, paused: updated.paused } } : d,
    );
    void loadStrings();
  }, [view, loadStrings]);

  const openInFiles = useCallback((path: string) => {
    navigateToSurface('files', { path });
  }, [navigateToSurface]);

  const refreshDesk = useCallback(() => {
    if (topic) void loadDesk(topic);
    void loadStrings();
    setActivityNonce((n) => n + 1);
  }, [topic, loadDesk, loadStrings]);

  const runNow = useCallback(async () => {
    if (!view || running) return;
    setRunning(true);
    setRunNote(null);
    try {
      const res = await api.strings.run(view.topic);
      if (res.no_change) setRunNote('Ran — nothing changed.');
      else if (res.success) setRunNote('Ran — the file was updated.');
      else if (res.error_reason === 'shape_violation')
        setRunNote(`Update refused — ${res.detail ?? 'the fetched data broke the declared shape'}.`);
      else if (res.error_reason === 'router_disabled')
        setRunNote('Run skipped — the engine is unavailable on this workspace.');
      else setRunNote(`Run failed (${res.error_reason ?? 'unknown'}).`);
    } catch (e) {
      setRunNote(`Run failed (${e instanceof Error ? e.message : String(e)}).`);
    } finally {
      setRunning(false);
      refreshDesk();
    }
  }, [view, running, refreshDesk]);

  const onLaneWrite = useCallback(() => {
    refreshDesk();
  }, [refreshDesk]);

  const setupIncomplete =
    desk.phase === 'unconfigured' || desk.phase === 'repair' ||
    (desk.phase === 'ready' && desk.view.problem != null);

  // Freshness/staleness (D7.1): the last successful write is the "as of";
  // a failed latest fetch is stated plainly — the head is the last good
  // version, never silently stale.
  const lastGoodWrite = view?.recent_runs.find(
    (r) => r.slug.startsWith('string-write:') && r.status === 'success',
  )?.created_at ?? null;
  const latestSweep = view?.recent_runs.find((r) => r.slug.startsWith('string-sweep:'));
  const fetchBroken = latestSweep?.status === 'failed';

  // ── The center pane — the file's lifecycle (D7) ─────────────────────────
  const renderCenter = (ctx: DeskContext) => {
    if (!topic) return null;
    const { lanesEnabled, seedChat, showRailColumn } = ctx;
    return (
      <div className="mx-auto max-w-3xl space-y-8 p-6">
        {/* ── The file — what this desk keeps ── */}
        <header className="space-y-1.5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex min-w-0 items-center gap-2">
              {!showRailColumn ? (
                <StringSwitcher
                  strings={strings}
                  topic={topic}
                  open={switcherOpen}
                  setOpen={setSwitcherOpen}
                  onSelect={selectTopic}
                  onAttach={() => { setSwitcherOpen(false); setAttachOpen(true); }}
                  lanesEnabled={lanesEnabled}
                />
              ) : (
                <>
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <h1 className="truncate text-lg font-semibold">
                    {view?.target ?? targetParam ?? topic.split('/').join(' / ')}
                  </h1>
                </>
              )}
            </div>
            {view && (
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={refreshDesk}
                  title="Refresh"
                  className="rounded border p-1.5 hover:bg-muted"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => void runNow()}
                  disabled={running || view.problem != null}
                  title={view.problem != null
                    ? 'The string cannot run until its declaration is repaired'
                    : 'Fetch the sources and update the file now'}
                  className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
                >
                  {running
                    ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    : <Zap className="h-3.5 w-3.5" />} Run now
                </button>
                <button
                  type="button"
                  onClick={() => void togglePause()}
                  className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted"
                >
                  {view.paused
                    ? (<><Play className="h-3.5 w-3.5" /> Resume</>)
                    : (<><Pause className="h-3.5 w-3.5" /> Pause</>)}
                </button>
              </div>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {desk.phase === 'ready' && view && (
              <>
                {view.paused ? 'Paused' : 'Kept current'}
                {' · as of '}{fmtWhen(lastGoodWrite ?? view.last_run_at)}
                {' · next '}{view.paused ? '—' : fmtWhen(view.next_run_at)}
              </>
            )}
            {desk.phase === 'unconfigured' &&
              'Not kept yet — Supervisor sets it up in the conversation.'}
            {desk.phase === 'loading' && 'Loading…'}
            {deskRoot && (
              <>
                {' · '}
                <button
                  type="button"
                  className="underline-offset-2 hover:underline"
                  onClick={() => openInFiles(deskRoot)}
                  title="The folder in Files — the file, its contract and its setup live there as ordinary files"
                >
                  open folder
                </button>
              </>
            )}
          </p>
          {runNote && (
            <p className="text-xs text-muted-foreground">{runNote}</p>
          )}
        </header>

        {/* ── Transient read failure — retry, never fake repair ── */}
        {desk.phase === 'error' && (
          <div className="rounded-md border bg-muted/30 p-4 text-sm">
            <p>This folder could not be read right now ({desk.detail}).</p>
            <button
              type="button"
              onClick={refreshDesk}
              className="mt-2 inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs hover:bg-muted"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Retry
            </button>
          </div>
        )}

        {/* ── Repair — an unparseable declaration is LOUD (D3) ── */}
        {desk.phase === 'repair' && (
          <RepairCard
            title="The string declaration can't be read."
            body={
              <>
                <code>_string.yaml</code> failed to parse ({desk.detail}).
                The standing loop is dark until it&apos;s repaired — nothing
                is being kept current.
              </>
            }
            lanesEnabled={lanesEnabled}
            seed="The string declaration (_string.yaml) fails to parse — re-read it and repair it."
            seedChat={seedChat}
          />
        )}

        {/* ── Problem — parses but cannot run (D3, served loudly) ── */}
        {view?.problem && (
          <RepairCard
            title="The string cannot run."
            body={<>{PROBLEM_COPY[view.problem] ?? `Declaration problem: ${view.problem}.`}</>}
            lanesEnabled={lanesEnabled}
            seed={`The string declaration has a problem (${view.problem}) — re-read _string.yaml and repair it.`}
            seedChat={seedChat}
          />
        )}

        {/* ── Refused write — the shape held the line (D3) ── */}
        {view?.repair && !view.problem && (
          <RepairCard
            title="The last update was refused."
            body={
              <>
                The fetched data didn&apos;t satisfy the declared shape
                ({view.repair.reason}{view.repair.at ? `, ${fmtWhen(view.repair.at)}` : ''}).
                The file still shows the last good version — no bad numbers
                landed silently.
              </>
            }
            lanesEnabled={lanesEnabled}
            seed="The last run was refused with a shape violation — check the source and the declared shape, and repair whichever is wrong."
            seedChat={seedChat}
          />
        )}

        {/* ── Unconfigured — SETUP IS FIRST-CLASS (ADR-595 D4): the pane IS
            the setup surface. The string's anatomy renders as numbered
            slots; each act is a precise seed into Supervisor's lane; the slots
            fill live as the files land (the substrate is the state machine),
            and the desk promotes to the tabs the moment the declaration
            parses. Authorship stays conversational — the one direct gesture
            is still the file pick. ── */}
        {desk.phase === 'unconfigured' && (
          <SetupPanel
            targetParam={targetParam}
            topic={topic}
            contract={desk.contract}
            slices={apertureSlices}
            lanesEnabled={lanesEnabled}
            seedChat={seedChat}
            onPick={() => setAttachOpen(true)}
          />
        )}

        {/* ── The tabs (ADR-595 D2) — loud states stay ABOVE, never behind ── */}
        {desk.phase === 'ready' && view && (
          <>
            <nav className="flex gap-1 border-b" aria-label="String tabs">
              {STRINGS_TABS.map((t) => (
                <button
                  key={t.key}
                  type="button"
                  onClick={() => setTab(t.key)}
                  aria-current={tab === t.key ? 'page' : undefined}
                  className={`-mb-px border-b-2 px-3 py-1.5 text-xs font-medium ${
                    tab === t.key
                      ? 'border-foreground text-foreground'
                      : 'border-transparent text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {t.label}
                  {t.key === 'sources' && ` (${view.sources.length})`}
                </button>
              ))}
            </nav>

            {tab === 'overview' && (
              <div className="space-y-6">
                <StatusCard
                  view={view}
                  lastGoodWrite={lastGoodWrite}
                  fetchBroken={fetchBroken}
                  onOpenFile={() => view.target_path && openInFiles(view.target_path)}
                />
                <FlowStrip
                  view={view}
                  onSources={() => setTab('sources')}
                  onOpenFile={() => view.target_path && openInFiles(view.target_path)}
                />
                <section>
                  <SectionHeading className="mb-2">Cited by</SectionHeading>
                  {view.consumers.length === 0 ? (
                    <p className="rounded-md border border-dashed px-4 py-4 text-xs text-muted-foreground">
                      Nothing cites this file yet. Reference it from a doc or a
                      deck and the projection stays current as the file moves —
                      the artifact itself is never rewritten.
                    </p>
                  ) : (
                    <ul className="divide-y rounded-md border">
                      {view.consumers.map((p) => (
                        <li key={p}>
                          <button
                            type="button"
                            onClick={() => openInFiles(p)}
                            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs hover:bg-muted/60"
                          >
                            <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                            <span className="truncate">{relPath(p) ?? p}</span>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>
            )}

            {tab === 'sources' && (
              <SourcesPanel
                view={view}
                lanesEnabled={lanesEnabled}
                seedChat={seedChat}
                openInFiles={openInFiles}
              />
            )}

            {tab === 'activity' && deskRoot && (
              <section>
                <DeskActivityRail
                  deskRoot={deskRoot}
                  events={view.recent_runs}
                  refreshNonce={activityNonce}
                  onReverted={refreshDesk}
                  authorLabel={stringsAuthorLabel}
                  authorChip={stringsAuthorChip}
                  fileLabel={(rel) => {
                    if (view.target && rel === view.target) return 'File';
                    if (rel === 'CONTRACT.md') return 'Contract';
                    if (rel === '_string.yaml') return 'Setup';
                    return undefined;
                  }}
                  canRevert={(p) =>
                    (view.target != null && p === `${deskRoot}/${view.target}`) ||
                    p === `${deskRoot}/CONTRACT.md`}
                  eventLine={runStatusLine}
                />
              </section>
            )}

            {tab === 'contract' && (
              <section className="space-y-5">
                <div className="rounded-md border">
                  <div className="flex items-center justify-between border-b px-4 py-2">
                    <span className="text-xs font-medium">What this file must stay true to</span>
                    {lanesEnabled && (
                      <SeedButton onClick={() => seedChat('Refine the contract: ')}>
                        refine in chat
                      </SeedButton>
                    )}
                  </div>
                  <div className="px-4 py-3">
                    {view.contract ? (
                      <MarkdownRenderer content={view.contract} compact />
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        No contract declared — runs hold a conservative bar.
                        Declaring one sharpens every future run.
                      </p>
                    )}
                  </div>
                </div>

                {/* Cadence — plain words; the raw cron is the tooltip. */}
                <div className="flex items-center justify-between rounded-md border px-4 py-2.5">
                  <div className="text-xs">
                    <span className="font-medium">Cadence</span>
                    <span
                      className="ml-2 text-muted-foreground"
                      title={Array.isArray(view.schedule)
                        ? view.schedule.join(' · ')
                        : view.schedule || undefined}
                    >
                      {view.schedule ? scheduleDisplay(view.schedule) : '—'}
                    </span>
                  </div>
                  {lanesEnabled && (
                    <SeedButton onClick={() => seedChat('Change the cadence: ')}>
                      change in chat
                    </SeedButton>
                  )}
                </div>

                {/* The shape, in words (structured formats only) */}
                {(view.shape?.columns?.length || view.shape?.keys?.length) ? (
                  <div className="flex items-center justify-between rounded-md border px-4 py-2.5">
                    <div className="min-w-0 text-xs">
                      <span className="font-medium">Shape</span>
                      <span className="ml-2 text-muted-foreground">
                        {view.shape.columns?.length
                          ? <>Columns: <span className="font-mono">{view.shape.columns.join(', ')}</span></>
                          : <>Keys: <span className="font-mono">{view.shape.keys?.join(', ')}</span></>}
                        {' — a fetched update that breaks this is refused, never written.'}
                      </span>
                    </div>
                    {lanesEnabled && (
                      <SeedButton onClick={() => seedChat('Change the declared shape: ')}>
                        change in chat
                      </SeedButton>
                    )}
                  </div>
                ) : null}
              </section>
            )}
          </>
        )}
      </div>
    );
  };

  // ── Render — the shared housing, wearing the standing-work vocabulary ───
  return (
    <DeskHousing
      app="strings"
      subject={topic}
      artifactPath={artifactPath}
      laneReady={desk.phase !== 'idle' && desk.phase !== 'loading'}
      laneName={topic ? `Keep: ${view?.target ?? targetParam ?? topic}` : ''}
      laneTabLabel="Supervisor"
      suggestions={setupIncomplete ? SETUP_SUGGESTIONS : TUNE_SUGGESTIONS}
      laneFallbackLabel={
        targetParam || view
          ? 'Supervisor’s lane could not be opened.'
          : 'Pick the file to keep current — Supervisor joins once it’s chosen.'
      }
      onLaneWrite={onLaneWrite}
      laneEmptyState={
        <div className="space-y-2 text-center text-xs text-muted-foreground">
          <p className="text-sm font-medium text-foreground/80">
            {setupIncomplete
              ? 'Tell Supervisor what this file must stay true to.'
              : 'This file is on the standing-work desk.'}
          </p>
          <p>
            Say what the file means and where currency comes from — Supervisor
            writes the contract and the string declaration into the folder,
            and its standing runs take it from there. Change the source,
            the cadence, or the contract the same way, any time; your own
            edits to the file are corrections that compound.
          </p>
        </div>
      }
      renderRail={(ctx) => (
        <StringRail
          strings={strings}
          topic={topic}
          condensed={!ctx.wb.fullLabels}
          lanesEnabled={ctx.lanesEnabled}
          onSelect={selectTopic}
          onAttach={() => setAttachOpen(true)}
        />
      )}
      renderFrontDoor={(ctx) => (
        <main className="flex min-h-0 min-w-0 flex-1 items-center justify-center">
          <div className="max-w-sm space-y-3 p-6 text-center">
            <Cable className="mx-auto h-8 w-8 text-muted-foreground" />
            <h1 className="text-lg font-semibold">Keep a file current</h1>
            <p className="text-sm text-muted-foreground">
              Designate a file and Supervisor maintains it — pulling its declared
              sources on a schedule and revising the file under a contract
              you set in plain words, while your own corrections compound.
              Docs and decks that cite it stay current by reference.
            </p>
            {ctx.lanesEnabled === false ? (
              <p className="text-xs text-amber-700 dark:text-amber-400">
                Keeping a file is set up in conversation with Supervisor, which
                isn&apos;t enabled on this workspace yet.
              </p>
            ) : (
              <button
                type="button"
                onClick={() => setAttachOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-md border bg-foreground px-3 py-1.5 text-sm text-background"
              >
                <Plus className="h-3.5 w-3.5" /> Keep a file current
              </button>
            )}
          </div>
        </main>
      )}
      overlay={() => (
        <DesignateFileModal
          open={attachOpen}
          existing={strings ?? []}
          onClose={() => setAttachOpen(false)}
          onDesignate={(t, target) => {
            setAttachOpen(false);
            selectTopic(t, target);
          }}
        />
      )}
    >
      {renderCenter}
    </DeskHousing>
  );
}

// ── Setup — first-class (ADR-595 D4): the anatomy as numbered slots ─────────

function SetupSlot({
  n, title, done, children,
}: {
  n: number;
  title: React.ReactNode;
  done?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-md border">
      <div className="flex items-center gap-2.5 border-b px-4 py-2.5">
        <span
          className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
            done
              ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400'
              : 'bg-muted text-muted-foreground'
          }`}
        >
          {done ? '✓' : n}
        </span>
        <span className="text-xs font-medium">{title}</span>
      </div>
      {children && <div className="px-4 py-3">{children}</div>}
    </div>
  );
}

function SetupPanel({
  targetParam, topic, contract, slices, lanesEnabled, seedChat, onPick,
}: {
  targetParam: string | null;
  topic: string | null;
  contract: string | null;
  slices: ApertureSlice[] | null;
  lanesEnabled: boolean | null;
  seedChat: (text: string) => void;
  onPick: () => void;
}) {
  const seeds = lanesEnabled !== false;
  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        Four things make a string. Say each one to Supervisor — it writes the
        contract and the declaration into the folder, attributed and
        revisable, and this desk becomes the file&apos;s tending surface the
        moment the declaration lands.
      </p>
      {lanesEnabled === false && (
        <p className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
          Setting up happens in conversation with Supervisor, which isn&apos;t
          enabled on this workspace yet — so this file can&apos;t be
          designated from here right now.
        </p>
      )}

      {/* ① The file — the one direct gesture */}
      <SetupSlot n={1} title="The file" done={!!targetParam}>
        {targetParam ? (
          <p className="text-xs">
            <code>{targetParam}</code>
            <span className="text-muted-foreground"> in {topic}</span>
          </p>
        ) : (
          <button
            type="button"
            onClick={onPick}
            disabled={!seeds}
            className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-40"
          >
            <Plus className="h-3.5 w-3.5" /> Pick the file to keep current
          </button>
        )}
      </SetupSlot>

      {/* ② The contract — fills live once CONTRACT.md lands */}
      <SetupSlot n={2} title="The contract — what must it stay true to?" done={!!contract}>
        {contract ? (
          <MarkdownRenderer content={contract} compact />
        ) : seeds ? (
          <SeedButton onClick={() => seedChat('This file must stay true to: ')}>
            This file must stay true to…
          </SeedButton>
        ) : (
          <p className="text-xs text-muted-foreground">Not declared yet.</p>
        )}
      </SetupSlot>

      {/* ③ The sources — the aperture surfaced where it matters */}
      <SetupSlot n={3} title="The sources — where does currency come from?">
        <div className="space-y-2.5">
          {slices === null ? (
            <p className="text-xs text-muted-foreground">Checking your connections…</p>
          ) : slices.length > 0 ? (
            <div>
              <p className="mb-1.5 text-[11px] text-muted-foreground">
                From your connections — already in your selection, ready to pull:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {slices.map((s) => (
                  <button
                    key={`${s.provider}:${s.id}`}
                    type="button"
                    disabled={!seeds}
                    onClick={() =>
                      seedChat(
                        `Pull from the ${s.provider} slice '${s.name ?? s.id}' (${s.id}). `,
                      )}
                    className="inline-flex items-center gap-1.5 rounded border px-2 py-1 text-[11px] hover:bg-muted disabled:opacity-40"
                  >
                    <Cable className="h-3 w-3 shrink-0 text-muted-foreground" />
                    <span className="font-medium">{s.provider}</span>
                    <span className="max-w-40 truncate text-muted-foreground">
                      {s.name ?? s.id}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-[11px] text-muted-foreground">
              No connection slices selected yet — connect a platform and select
              what it may read, or pull from an address instead.
            </p>
          )}
          {seeds && (
            <div className="flex items-center gap-1.5">
              <Globe className="h-3 w-3 shrink-0 text-muted-foreground" />
              <SeedButton onClick={() => seedChat('Pull from this source: ')}>
                Pull from an address (URL)…
              </SeedButton>
            </div>
          )}
        </div>
      </SetupSlot>

      {/* ④ The cadence */}
      <SetupSlot n={4} title="The cadence — how often?">
        {seeds ? (
          <div className="flex flex-wrap gap-1.5">
            {CADENCE_PRESETS.map((c) => (
              <SeedButton key={c.label} onClick={() => seedChat(c.seed)}>
                {c.label}
              </SeedButton>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">Not declared yet.</p>
        )}
      </SetupSlot>

      {contract && (
        <p className="text-xs text-muted-foreground">
          The declaration is still pending — Supervisor finishes it in the
          conversation, and the standing loop begins on the next tick
          (~5&nbsp;minutes). Your own edits to the file are corrections, and
          they compound into every future run.
        </p>
      )}
    </div>
  );
}

function fmtBytes(n?: number | null): string | null {
  if (n == null) return null;
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/** One source's identity line — shared by the flow strip and the source card. */
function sourceKindLine(s: StringSource): string {
  return s.url ?? `${s.connector} · ${s.selector}`;
}

// ── Overview: the status card — file FACTS, never the file (ADR-595 D1) ────

function StatusCard({
  view, lastGoodWrite, fetchBroken, onOpenFile,
}: {
  view: StringView;
  lastGoodWrite: string | null;
  fetchBroken: boolean;
  onOpenFile: () => void;
}) {
  const facts = [
    view.format?.toUpperCase(),
    view.head_lines != null
      ? `${view.head_lines} ${view.format === 'csv' ? 'rows' : 'lines'}`
      : null,
    fmtBytes(view.head_bytes),
  ].filter(Boolean);
  return (
    <div className="rounded-md border p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-sm font-medium">
            <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate">{view.target}</span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {facts.join(' · ')}
            {(view.head_updated_at ?? lastGoodWrite) &&
              ` · updated ${fmtWhen(view.head_updated_at ?? lastGoodWrite)}`}
          </p>
        </div>
        {view.target_path ? (
          <button
            type="button"
            onClick={onOpenFile}
            title="Open the file at its own surface — correcting it there corrects every future run"
            className="inline-flex shrink-0 items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium hover:bg-muted"
          >
            <ExternalLink className="h-3.5 w-3.5" /> Open file
          </button>
        ) : (
          <span className="text-xs text-muted-foreground">
            No version yet — the first lands on the next run
            {!view.paused && view.next_run_at ? ` (${fmtWhen(view.next_run_at)})` : ''}.
          </span>
        )}
      </div>
      {fetchBroken && (
        <p className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-100">
          The last fetch failed — the file still shows the last good version
          (as of {fmtWhen(lastGoodWrite)}).
        </p>
      )}
    </div>
  );
}

// ── Overview: the N→1 flow strip — the relation itself, legible (D2) ────────

function FlowStrip({
  view, onSources, onOpenFile,
}: {
  view: StringView;
  onSources: () => void;
  onOpenFile: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-md border px-4 py-3">
      <div className="flex min-w-0 flex-col gap-1.5">
        {view.sources.length === 0 ? (
          <span className="rounded border border-dashed px-2 py-1 text-[11px] text-muted-foreground">
            no sources declared
          </span>
        ) : (
          view.sources.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={onSources}
              title={sourceKindLine(s)}
              className={`flex max-w-56 items-center gap-1.5 rounded border px-2 py-1 text-left text-[11px] hover:bg-muted ${
                s.in_aperture === false ? 'border-amber-400 text-amber-700 dark:text-amber-400' : ''
              }`}
            >
              {s.connector
                ? <Cable className="h-3 w-3 shrink-0" />
                : <Globe className="h-3 w-3 shrink-0" />}
              <span className="truncate font-medium">{s.id}</span>
              <span className="shrink-0 text-muted-foreground">
                {s.in_aperture === false
                  ? 'not selected'
                  : s.last_landed_at
                    ? fmtWhen(s.last_landed_at)
                    : 'no receipt'}
              </span>
            </button>
          ))
        )}
      </div>
      <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      <button
        type="button"
        onClick={onOpenFile}
        disabled={!view.target_path}
        className="min-w-0 rounded border px-3 py-2 text-left hover:bg-muted disabled:opacity-60"
      >
        <div className="truncate text-xs font-medium">{view.target}</div>
        <div className="text-[11px] text-muted-foreground">
          {view.paused ? 'paused' : 'kept current'}
        </div>
      </button>
      <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
      <span className="text-[11px] text-muted-foreground">
        cited by {view.consumers.length}
      </span>
    </div>
  );
}

// ── Sources: each source as a PARTY — standing · receipts · contribution ────

function SourcesPanel({
  view, lanesEnabled, seedChat, openInFiles,
}: {
  view: StringView;
  lanesEnabled: boolean | null;
  seedChat: (text: string) => void;
  openInFiles: (path: string) => void;
}) {
  const n = view.sources.length;
  const arity = view.format === 'md'
    ? `A prose string can weave up to ${PROSE_SOURCE_CAP} sources — ${n} declared.`
    : `A ${view.format ?? 'structured'} string keeps exactly one feed.`;
  const canAdd = view.format === 'md' ? n < PROSE_SOURCE_CAP : n === 0;
  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">{arity}</p>
        {lanesEnabled && canAdd && (
          <SeedButton onClick={() => seedChat('Add a source: ')}>
            add a source
          </SeedButton>
        )}
      </div>
      {n === 0 ? (
        <p className="rounded-md border border-dashed px-4 py-6 text-center text-xs text-muted-foreground">
          No sources declared yet — tell Supervisor where currency comes from.
        </p>
      ) : (
        view.sources.map((s) => (
          <div key={s.id} className="rounded-md border">
            <div className="flex items-center justify-between border-b px-4 py-2.5">
              <div className="flex min-w-0 items-center gap-2">
                {s.connector
                  ? <Cable className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                  : <Globe className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />}
                <span className="truncate text-xs font-medium">{s.id}</span>
                <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                  {s.connector ? `${s.connector} slice` : 'http pull'}
                </span>
              </div>
              {lanesEnabled && (
                <div className="flex shrink-0 items-center gap-1.5">
                  <SeedButton onClick={() => seedChat(`Change source '${s.id}': `)}>
                    change
                  </SeedButton>
                  <SeedButton onClick={() => seedChat(`Remove source '${s.id}'.`)}>
                    remove
                  </SeedButton>
                </div>
              )}
            </div>
            <dl className="space-y-1.5 px-4 py-3 text-xs">
              <div className="flex gap-2">
                <dt className="w-24 shrink-0 text-muted-foreground">Reads</dt>
                <dd className="min-w-0 truncate">
                  {s.url ?? `${s.connector} · ${s.selector} — through your connection`}
                </dd>
              </div>
              {s.connector && (
                <div className="flex gap-2">
                  <dt className="w-24 shrink-0 text-muted-foreground">Standing</dt>
                  <dd className={s.in_aperture === false ? 'text-amber-700 dark:text-amber-400' : ''}>
                    {s.in_aperture === false
                      ? `outside your ${s.connector} selection — nothing is read until you select it on the connection`
                      : s.in_aperture === true
                        ? `inside your ${s.connector} selection`
                        : 'selection unknown — the connection could not be read'}
                  </dd>
                </div>
              )}
              <div className="flex gap-2">
                <dt className="w-24 shrink-0 text-muted-foreground">Last landed</dt>
                <dd className="min-w-0">
                  {s.last_landed_path ? (
                    <button
                      type="button"
                      onClick={() => s.last_landed_path && openInFiles(s.last_landed_path)}
                      className="truncate underline-offset-2 hover:underline"
                      title="Open the landed snapshot — the receipt this source's last read left"
                    >
                      {fmtWhen(s.last_landed_at)} · open receipt
                    </button>
                  ) : (
                    <span className="text-muted-foreground">
                      nothing landed yet — the next run reaches and retains
                    </span>
                  )}
                </dd>
              </div>
              <div className="flex gap-2">
                <dt className="w-24 shrink-0 text-muted-foreground">Contributed</dt>
                <dd className="text-muted-foreground">
                  {s.last_contributed_at
                    ? `last moved the file ${fmtWhen(s.last_contributed_at)}`
                    : 'hasn’t moved the file yet'}
                </dd>
              </div>
            </dl>
          </div>
        ))
      )}
    </section>
  );
}

function SectionHeading({
  children,
  className,
}: { children: React.ReactNode; className?: string }) {
  return (
    <h2 className={`text-[11px] font-semibold uppercase tracking-wider text-muted-foreground ${className ?? ''}`}>
      {children}
    </h2>
  );
}

function SeedButton({
  onClick,
  children,
}: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] text-muted-foreground hover:bg-muted hover:text-foreground"
    >
      <MessageSquare className="h-3 w-3" /> {children}
    </button>
  );
}

function RepairCard({
  title, body, lanesEnabled, seed, seedChat,
}: {
  title: string;
  body: React.ReactNode;
  lanesEnabled: boolean | null;
  seed: string;
  seedChat: (text: string) => void;
}) {
  return (
    <div className="rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
      <p className="font-semibold">{title}</p>
      <p className="mt-1 text-xs">{body}</p>
      {lanesEnabled && (
        <button
          type="button"
          onClick={() => seedChat(seed)}
          className="mt-2 inline-flex items-center gap-1.5 rounded border border-red-400 px-2.5 py-1 text-xs font-medium hover:bg-red-100 dark:hover:bg-red-900"
        >
          <MessageSquare className="h-3.5 w-3.5" /> Ask Supervisor to repair it
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// The string rail — rows are maintained FILES (the subject-first guard,
// ADR-486 D2 inherited: this roster is the only roster; no workspace-global
// pane). A selected topic with no roster row renders as the setting-up row.
// ---------------------------------------------------------------------------

function StringRail({
  strings,
  topic,
  condensed,
  lanesEnabled,
  onSelect,
  onAttach,
}: {
  strings: StringSummary[] | null;
  topic: string | null;
  condensed: boolean;
  lanesEnabled: boolean | null;
  onSelect: (topic: string) => void;
  onAttach: () => void;
}) {
  const settingUp = topic && !(strings ?? []).some((s) => s.topic === topic);
  return (
    <aside className={`flex ${condensed ? 'w-52' : 'w-64'} shrink-0 flex-col border-r`}>
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Cable className="h-4 w-4" /> Strings
        </div>
        <button
          type="button"
          title={
            lanesEnabled === false
              ? 'Keeping a file is set up in conversation with Supervisor, which isn’t enabled here yet'
              : 'Keep a file current'
          }
          disabled={lanesEnabled === false}
          onClick={onAttach}
          className="rounded p-1 hover:bg-muted disabled:opacity-40"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {strings === null ? (
          <div className="p-4 text-xs text-muted-foreground">Looking…</div>
        ) : (
          <>
            {settingUp && topic && (
              <div className="block w-full border-b bg-muted px-4 py-3 text-left">
                <StringRow
                  title={topic.split('/').pop() ?? topic}
                  subtitle="setting up with Supervisor…"
                  dot="pending"
                />
              </div>
            )}
            {strings.length === 0 && !settingUp ? (
              <div className="p-4 text-xs text-muted-foreground">
                No files kept yet. Designate one and Supervisor maintains it while
                you&apos;re away.
              </div>
            ) : (
              strings.map((s) => (
                <button
                  key={s.topic}
                  type="button"
                  onClick={() => onSelect(s.topic)}
                  className={`block w-full border-b px-4 py-3 text-left hover:bg-muted/60 ${
                    topic === s.topic ? 'bg-muted' : ''
                  }`}
                >
                  <StringRow
                    title={s.target || (s.topic.split('/').pop() ?? s.topic)}
                    subtitle={
                      s.problem
                        ? 'needs repair'
                        : `${s.topic}${s.paused ? ' · paused' : ''}`
                    }
                    dot={s.problem ? 'repair' : s.paused ? 'paused' : 'active'}
                  />
                </button>
              ))
            )}
          </>
        )}
      </div>
    </aside>
  );
}

function StringRow({
  title,
  subtitle,
  dot,
}: {
  title: string;
  subtitle: string;
  dot: 'active' | 'paused' | 'pending' | 'repair';
}) {
  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5 text-sm font-medium">
          <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate">{title}</span>
        </span>
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${
            dot === 'active' ? 'bg-emerald-500'
              : dot === 'paused' ? 'bg-amber-500'
              : dot === 'repair' ? 'bg-red-500'
              : 'bg-zinc-400'
          }`}
          title={
            dot === 'active' ? 'Kept current'
              : dot === 'paused' ? 'Paused'
              : dot === 'repair' ? 'Needs repair'
              : 'Setting up'
          }
        />
      </div>
      <div className="mt-0.5 truncate text-xs text-muted-foreground">{subtitle}</div>
    </>
  );
}

// ---------------------------------------------------------------------------
// The string switcher — the rail, folded into the header on narrow rungs.
// ---------------------------------------------------------------------------

function StringSwitcher({
  strings,
  topic,
  open,
  setOpen,
  onSelect,
  onAttach,
  lanesEnabled,
}: {
  strings: StringSummary[] | null;
  topic: string;
  open: boolean;
  setOpen: (v: boolean) => void;
  onSelect: (topic: string) => void;
  onAttach: () => void;
  lanesEnabled: boolean | null;
}) {
  const current = (strings ?? []).find((s) => s.topic === topic);
  return (
    <div className="relative min-w-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex min-w-0 items-center gap-2 rounded px-1 py-0.5 hover:bg-muted"
      >
        <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
        <h1 className="truncate text-lg font-semibold">
          {current?.target || topic.split('/').join(' / ')}
        </h1>
        <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-20 mt-1 w-72 rounded-md border bg-card py-1 shadow-lg">
          {(strings ?? []).map((s) => (
            <button
              key={s.topic}
              type="button"
              onClick={() => onSelect(s.topic)}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted ${
                s.topic === topic ? 'font-medium' : ''
              }`}
            >
              <FileText className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{s.target || s.topic}</span>
            </button>
          ))}
          <div className="my-1 border-t" />
          <button
            type="button"
            onClick={onAttach}
            disabled={lanesEnabled === false}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted disabled:opacity-40"
          >
            <Plus className="h-3.5 w-3.5 shrink-0" /> Keep a file current…
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// The one direct gesture: picking the file (ADR-569 D7 / ADR-384 layer 1) —
// an existing file, or a folder plus a name for the new leaf. Everything
// after the pick is Supervisor's conversation.
// ---------------------------------------------------------------------------

function DesignateFileModal({
  open, existing, onClose, onDesignate,
}: {
  open: boolean;
  existing: StringSummary[];
  onClose: () => void;
  onDesignate: (topic: string, target: string | null) => void;
}) {
  const [mode, setMode] = useState<'existing' | 'new'>('existing');
  const [selected, setSelected] = useState<string | null>(null);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    if (open) { setMode('existing'); setSelected(null); setNewName(''); }
  }, [open]);

  if (!open) return null;

  const fileSelectable = (n: WorkspaceTreeNode) =>
    n.type === 'file' && isDesignatable(n.path.split('/').pop() ?? '');
  const folderSelectable = (n: WorkspaceTreeNode) =>
    n.type === 'folder' && n.path.startsWith(`${WORKSPACE_ROOT}/`);

  let topic: string | null = null;
  let target: string | null = null;
  let invalidName = false;
  if (mode === 'existing' && selected) {
    const rel = relPath(selected);
    if (rel && rel.includes('/')) {
      topic = rel.slice(0, rel.lastIndexOf('/'));
      target = rel.slice(rel.lastIndexOf('/') + 1);
    }
  } else if (mode === 'new' && selected) {
    const rel = relPath(selected);
    const leaf = kebab(newName);
    if (rel != null && leaf) {
      if (isDesignatable(leaf)) {
        topic = rel;
        target = leaf;
      } else {
        invalidName = true;
      }
    }
  }

  const held = topic != null ? existing.find((s) => s.topic === topic) : undefined;
  const sameFile = held != null && target != null && held.target === target;
  const collides = held != null && !sameFile;

  return createPortal(
    <>
      <div
        className="fixed inset-0 bg-black/50 animate-in fade-in duration-150"
        style={{ zIndex: Z_CONFIRM_BACKDROP }}
        onClick={onClose}
      />
      <div
        className="fixed inset-0 flex items-center justify-center p-4 pointer-events-none"
        style={{ zIndex: Z_CONFIRM_DIALOG }}
      >
        <div
          className="pointer-events-auto flex w-full max-w-md flex-col rounded-lg border border-border bg-card shadow-xl animate-in fade-in zoom-in-95 duration-150"
          role="dialog"
          aria-modal="true"
          aria-label="Keep a file current"
          style={{ maxHeight: '70vh' }}
        >
          <div className="flex items-start justify-between border-b border-border px-5 py-3.5">
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-card-foreground">Keep a file current</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Pick the file — Supervisor sets the rest up with you in
                conversation. One kept file per folder.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 text-muted-foreground/60 transition-colors hover:text-foreground"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex shrink-0 border-b border-border text-xs">
            {([['existing', 'An existing file'], ['new', 'A new file']] as const).map(([m, label]) => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); setSelected(null); }}
                className={`flex-1 py-2 text-center font-medium ${
                  mode === m
                    ? 'border-b-2 border-foreground text-foreground'
                    : 'text-muted-foreground'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto">
            {mode === 'existing' ? (
              <WorkspacePickerBody
                mode="file"
                selectable={fileSelectable}
                selected={selected}
                onSelect={setSelected}
                emptyMessage="No md, csv, json or txt files yet — switch to “A new file”."
              />
            ) : (
              <WorkspacePickerBody
                mode="folder"
                selectable={folderSelectable}
                selected={selected}
                onSelect={setSelected}
                emptyMessage="No folders yet."
              />
            )}
          </div>

          <div className="space-y-2 border-t border-border px-5 py-3">
            {mode === 'new' && (
              <label className="block text-xs">
                <span className="mb-1 block text-muted-foreground">
                  Name for the new file (md, csv, json or txt)
                </span>
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="metrics.csv"
                  className="w-full rounded-md border bg-background px-2.5 py-1.5 text-sm"
                />
              </label>
            )}
            <div className="flex items-center justify-between gap-3">
              <span className="min-w-0 truncate text-xs text-muted-foreground">
                {invalidName
                  ? 'The name needs an md, csv, json or txt extension.'
                  : collides
                    ? `This folder already keeps ${held?.target || 'a file'} current — one per folder. This opens its desk.`
                    : sameFile
                      ? `${target} is already kept — this opens its desk.`
                      : topic && target
                        ? `Will keep: ${topic}/${target}`
                        : mode === 'existing'
                          ? 'Pick a file to keep current.'
                          : 'Pick a folder and name the file.'}
              </span>
              <button
                type="button"
                disabled={!topic || (mode === 'new' && !target)}
                onClick={() => topic && onDesignate(topic, collides || sameFile ? null : target)}
                className="shrink-0 rounded-md border bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-50"
              >
                {collides || sameFile ? 'Open desk' : 'Designate'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
