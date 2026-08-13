'use client';

/**
 * RadarSurface — the Researcher's desk (ADR-567, over ADR-564/565).
 *
 * Derived from what the member DOES here, in frequency order: read the report
 * → see what changed → correct something → tune the setup → attach a folder.
 * The consequence that shapes everything: this is a READING desk. The report
 * is the canvas (rendered as a document, the last thing to lose width —
 * AUTHORING.md rule 15); the rail, the setup cards and the lane are chrome
 * around it and fold first.
 *
 * Layout: watched-folder rail · the folder's lifecycle (center) · Researcher
 * (the bound lane). Width rides `useWorkbenchWidth` on the desk's own
 * container (never the viewport, never raw `md:`/`lg:`):
 *   full/condensed → three columns;
 *   two-pane       → the rail folds into a header switcher;
 *   single-pane    → one pane + a Desk/Researcher tab bar.
 *
 * The desk's identity is the `radar.topic` param — an attach-in-flight IS a
 * topic with no declaration yet, so a refresh resumes the unconfigured desk
 * instead of losing it (the substrate is the state machine: the desk promotes
 * itself the moment Researcher's declaration parses, ADR-567 D3).
 *
 * Creation is conversational with exactly ONE direct gesture — the folder
 * pick (ADR-384/564 layer 1). Direct switches stay direct (Pause/Resume).
 * The lane is mounted through LaneMountSlots only; the desk owns the report
 * view, so lane artifact writes render as links, never duplicate cards.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  ChevronDown, Folder, Loader2, MessageSquare, Pause, Play, Plus,
  Radar as RadarIcon, RefreshCw, X,
} from 'lucide-react';
import { api, type RadarHubSummary, type RadarHubView } from '@/lib/api/client';
import {
  useSurfaceParam, useSurfacePreferences,
} from '@/lib/shell/useSurfacePreferences';
import { useDeclareFocus } from '@/lib/shell/useSurfaceFocus';
import { useWorkbenchWidth } from '@/lib/authoring/workbench-width';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { WorkspacePickerBody } from '@/components/workspace/WorkspacePicker';
import { DeskActivityRail } from '@/components/radar/DeskActivityRail';
import type { WorkspaceTreeNode } from '@/types';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

// Lane env shapes come from the client, never hand-copied (the drift seam
// the 567 first cut reopened).
type LanesEnv = Awaited<ReturnType<typeof api.lanes.list>>;
type LaneRow = LanesEnv['lanes'][number];

const OPERATION_ROOT = '/workspace/operation';

export function topicFromDeclarationPath(path: string): string | null {
  // Any depth under operation/ (ADR-565 D3) — the topic IS the folder path.
  const m = /operation\/(.+)\/_radar\.yaml$/.exec(path || '');
  return m ? m[1] : null;
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
  s.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');

/** What the desk knows about the selected folder. The substrate is the state
 *  machine: `unconfigured` = no parseable declaration YET (a fresh attach, or
 *  a folder Researcher is mid-setup on); `repair` = a declaration exists and
 *  fails to parse (ADR-567 D6 — loud, never silently dark). */
type DeskState =
  | { phase: 'idle' }
  | { phase: 'loading' }
  | { phase: 'ready'; view: RadarHubView }
  | { phase: 'unconfigured'; criterion: string | null }
  | { phase: 'repair'; detail: string }
  | { phase: 'error'; detail: string };

const SETUP_SUGGESTIONS = [
  "Here's what matters in this folder: ",
  'Watch these sources: ',
  'Sweep every morning and keep the report current.',
];

const TUNE_SUGGESTIONS = [
  'What changed since last week?',
  'Tighten the criterion — too much noise gets through.',
  "Which sources aren't earning their keep?",
];

export default function RadarSurface() {
  const { navigateToSurface } = useSurfacePreferences();
  const param = useSurfaceParam('radar');
  const [setWorkbenchNode, wb] = useWorkbenchWidth();

  const topic = param.get('topic');
  const deskRoot = topic ? `${OPERATION_ROOT}/${topic}` : null;
  const reportPath = deskRoot ? `${deskRoot}/report.md` : null;

  const [hubs, setHubs] = useState<RadarHubSummary[] | null>(null);
  const [desk, setDesk] = useState<DeskState>({ phase: 'idle' });
  const [attachOpen, setAttachOpen] = useState(false);
  const [activityNonce, setActivityNonce] = useState(0);
  // single-pane: which pane the tab bar shows.
  const [activePane, setActivePane] = useState<'desk' | 'lane'>('desk');
  const [switcherOpen, setSwitcherOpen] = useState(false);
  // Composer seed for the refine-in-chat gestures (LaneMountSlots contract).
  const [seed, setSeed] = useState<{ text: string; nonce: number } | null>(null);

  const view = desk.phase === 'ready' ? desk.view : null;

  // ADR-522 — the desk declares its focus: the folder is the unit; the report
  // is the felt object once it exists.
  useDeclareFocus(
    'radar',
    topic
      ? {
          app: 'radar',
          path: view?.report_path ?? (deskRoot ? `${deskRoot}/_radar.yaml` : null),
          scope: 'document',
          id: null,
          pageIndex: null,
          label: topic,
          excerpt: view?.report_title ?? null,
          viewport: null,
        }
      : null,
  );

  const loadHubs = useCallback(async (): Promise<RadarHubSummary[]> => {
    try {
      const rows = await api.radar.list();
      setHubs(rows);
      return rows;
    } catch {
      setHubs([]);
      return [];
    }
  }, []);

  const loadDesk = useCallback(async (t: string) => {
    setDesk((d) => (d.phase === 'ready' ? d : { phase: 'loading' }));
    try {
      const v = await api.radar.get(t);
      setDesk({ phase: 'ready', view: v });
    } catch (e) {
      const status = (e as { status?: number })?.status;
      if (status === 404) {
        // No declaration yet — the unconfigured desk. Show the criterion if
        // Researcher has already authored one (setup lands file by file).
        let criterion: string | null = null;
        try {
          const f = await api.workspace.getFile(`${OPERATION_ROOT}/${t}/CRITERION.md`);
          criterion = f?.content ?? null;
        } catch { /* not written yet */ }
        setDesk({ phase: 'unconfigured', criterion });
      } else if (status === 422) {
        // A declaration exists and fails to parse — the loud repair state
        // (ADR-567 D6), distinct from a transient read failure below.
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

  // Mount: roster + consume the Files-association deep-link (`radar.file` is
  // an open act — converted to `topic`, then cleared; ADR-494's ephemeral
  // classification keeps it off bare launches).
  useEffect(() => {
    void (async () => {
      const rows = await loadHubs();
      const fromFile = topicFromDeclarationPath(param.get('file') || '');
      if (fromFile) {
        param.set({ topic: fromFile, file: null });
        return;
      }
      if (!param.get('topic') && rows.length > 0) {
        param.set({ topic: rows[0].topic });
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (topic) void loadDesk(topic);
    else setDesk({ phase: 'idle' });
  }, [topic, loadDesk]);

  const selectTopic = useCallback((t: string) => {
    param.set({ topic: t, file: null });
    setSwitcherOpen(false);
    setActivePane('desk');
  }, [param]);

  const togglePause = useCallback(async () => {
    if (!view) return;
    const updated = await api.radar.update(view.topic, { paused: !view.paused });
    setDesk((d) =>
      d.phase === 'ready' ? { ...d, view: { ...d.view, paused: updated.paused } } : d,
    );
    void loadHubs();
  }, [view, loadHubs]);

  const openInFiles = useCallback((path: string) => {
    navigateToSurface('files', { path });
  }, [navigateToSurface]);

  const refreshDesk = useCallback(() => {
    if (topic) void loadDesk(topic);
    void loadHubs();
    setActivityNonce((n) => n + 1);
  }, [topic, loadDesk, loadHubs]);

  // ── The bound lane (find-or-create; the binding contract is ADR-567 D4:
  //    create_lane(app='radar', artifact_path={root}/report.md)) ────────────
  const [lanesEnabled, setLanesEnabled] = useState<boolean | null>(null);
  const [lanes, setLanes] = useState<LaneRow[]>([]);
  const [agents, setAgents] = useState<LanesEnv['agents']>([]);
  const [apps, setApps] = useState<NonNullable<LanesEnv['apps']>>([]);
  const [models, setModels] = useState<LanesEnv['models']>([]);

  const refreshLanes = useCallback(async () => {
    try {
      const res = await api.lanes.list(true);
      setLanesEnabled(res.enabled);
      setLanes(res.lanes);
      setAgents(res.agents ?? []);
      setApps(res.apps ?? []);
      setModels(res.models ?? []);
    } catch {
      setLanesEnabled(false);
    }
  }, []);

  useEffect(() => {
    void refreshLanes();
  }, [refreshLanes]);

  const boundLane = useMemo(() => {
    if (!reportPath) return null;
    return (
      lanes.find((l) => l.status === 'active' && l.artifact_path === reportPath) ??
      null
    );
  }, [lanes, reportPath]);

  const [creatingLane, setCreatingLane] = useState(false);
  useEffect(() => {
    if (!reportPath || !topic || !lanesEnabled || boundLane || creatingLane) return;
    if (desk.phase === 'idle' || desk.phase === 'loading') return;
    setCreatingLane(true);
    api.lanes
      .create({
        name: `Watch: ${topic}`.slice(0, 60),
        // ADR-562 D3/ADR-567 D4 — the surface names WHICH APP is asking; the
        // resident (Researcher) resolves server-side from radar's own
        // registration, and lane_meta.app selects the desk posture.
        app: 'radar',
        artifact_path: reportPath,
      })
      .then(() => refreshLanes())
      .catch(() => { /* the lane column states why below */ })
      .finally(() => setCreatingLane(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportPath, topic, lanesEnabled, boundLane, desk.phase]);

  const modelLabel = useMemo(() => {
    if (!boundLane) return '';
    return models.find((m) => m.id === boundLane.model)?.label ?? boundLane.model;
  }, [boundLane, models]);

  // ADR-562 D5 — WHO the member reads: the app's name for its resident
  // (served from radar's own registration), else the colleague's own name,
  // else the engine label. Read back from the wire, never asserted here.
  const speakerLabel = useMemo(() => {
    const slug = boundLane?.agent;
    if (slug) {
      const appName = apps.find((a) => a.slug === 'radar')?.name;
      if (appName) return appName;
      const named = agents.find((a) => a.slug === slug)?.name;
      if (named) return named;
    }
    return modelLabel;
  }, [agents, apps, boundLane, modelLabel]);

  // A lane write landed (criterion, declaration, report, a memo…): re-read
  // everything the desk projects. An unconfigured desk promotes itself the
  // moment the declaration parses — no client-side state machine.
  const onLaneWrite = useCallback(() => {
    refreshDesk();
  }, [refreshDesk]);

  const seedChat = useCallback((text: string) => {
    setSeed({ text, nonce: Date.now() });
    if (wb.singlePane) setActivePane('lane');
  }, [wb.singlePane]);

  // ── Layout flags ────────────────────────────────────────────────────────
  const showRailColumn = wb.threeColumn;
  const laneAvailable = !!topic && lanesEnabled === true;
  const showLaneColumn = laneAvailable && (!wb.singlePane || activePane === 'lane');
  const laneWidthClass = wb.fullLabels ? 'w-[400px]' : 'w-[360px]';

  const setupIncomplete = desk.phase === 'unconfigured' || desk.phase === 'repair';

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div
      ref={setWorkbenchNode}
      className="flex h-full min-h-0 flex-col bg-background text-foreground"
    >
      <div className="flex min-h-0 flex-1">
        {showRailColumn && (
          <FolderRail
            hubs={hubs}
            topic={topic}
            condensed={!wb.fullLabels}
            lanesEnabled={lanesEnabled}
            onSelect={selectTopic}
            onAttach={() => setAttachOpen(true)}
          />
        )}

        {topic ? (
          <>
            {(!wb.singlePane || activePane === 'desk') && (
              <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">
                <div className="mx-auto max-w-3xl space-y-8 p-6">
                  {/* ── The folder — what this desk manages ── */}
                  <header className="space-y-1.5">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex min-w-0 items-center gap-2">
                        {!showRailColumn ? (
                          <FolderSwitcher
                            hubs={hubs}
                            topic={topic}
                            open={switcherOpen}
                            setOpen={setSwitcherOpen}
                            onSelect={selectTopic}
                            onAttach={() => { setSwitcherOpen(false); setAttachOpen(true); }}
                            lanesEnabled={lanesEnabled}
                          />
                        ) : (
                          <>
                            <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <h1 className="truncate text-lg font-semibold">
                              {topic.split('/').join(' / ')}
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
                          {view.paused ? 'Paused' : 'Standing watch'}
                          {' · last sweep '}{fmtWhen(view.last_run_at)}
                          {' · next '}{view.paused ? '—' : fmtWhen(view.next_run_at)}
                        </>
                      )}
                      {desk.phase === 'unconfigured' &&
                        'Not watched yet — Researcher sets it up in the conversation.'}
                      {desk.phase === 'loading' && 'Loading…'}
                      {deskRoot && (
                        <>
                          {' · '}
                          <button
                            type="button"
                            className="underline-offset-2 hover:underline"
                            onClick={() => openInFiles(deskRoot)}
                            title="The folder in Files — the report and criterion are ordinary files in it"
                          >
                            open folder
                          </button>
                        </>
                      )}
                    </p>
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

                  {/* ── Repair — an unparseable declaration is LOUD (D6) ── */}
                  {desk.phase === 'repair' && (
                    <div className="rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100">
                      <p className="font-semibold">
                        The watch declaration can&apos;t be read.
                      </p>
                      <p className="mt-1 text-xs">
                        <code>_radar.yaml</code> failed to parse ({desk.detail}).
                        The standing sweep is dark until it&apos;s repaired — nothing
                        is being watched.
                      </p>
                      {lanesEnabled && (
                        <button
                          type="button"
                          onClick={() =>
                            seedChat('The watch declaration (_radar.yaml) fails to parse — re-read it and repair it.')
                          }
                          className="mt-2 inline-flex items-center gap-1.5 rounded border border-red-400 px-2.5 py-1 text-xs font-medium hover:bg-red-100 dark:hover:bg-red-900"
                        >
                          <MessageSquare className="h-3.5 w-3.5" /> Ask Researcher to repair it
                        </button>
                      )}
                    </div>
                  )}

                  {/* ── Unconfigured — the conversational setup (D3) ── */}
                  {desk.phase === 'unconfigured' && (
                    <div className="space-y-4">
                      <div className="rounded-md border bg-muted/30 p-4 text-sm">
                        <p className="font-medium">
                          Tell Researcher what to watch here.
                        </p>
                        <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">
                          Say what matters in this folder and where to look.
                          Researcher writes the criterion and the watch
                          declaration into the folder — attributed, revisable —
                          and the standing sweep begins on the next tick
                          (~5&nbsp;minutes). The first report lands while you
                          watch.
                        </p>
                        {lanesEnabled === false && (
                          <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                            Setting up happens in conversation with Researcher,
                            which isn&apos;t enabled on this workspace yet — so
                            this folder can&apos;t be configured from here right
                            now.
                          </p>
                        )}
                      </div>
                      {desk.criterion && (
                        <section>
                          <SectionHeading>Criterion — declared</SectionHeading>
                          <div className="rounded-md border p-4">
                            <MarkdownRenderer content={desk.criterion} compact />
                          </div>
                          <p className="mt-1.5 text-xs text-muted-foreground">
                            The watch declaration is still pending — Researcher
                            finishes the setup in the conversation.
                          </p>
                        </section>
                      )}
                    </div>
                  )}

                  {/* ── The report — the living artifact, THE canvas ── */}
                  {desk.phase === 'ready' && view && (
                    <section>
                      <div className="mb-2 flex items-baseline justify-between gap-3">
                        <SectionHeading>Report</SectionHeading>
                        {view.report && (
                          <span className="text-xs text-muted-foreground">
                            revised {fmtWhen(view.last_run_at)}
                            {view.report_path && (
                              <>
                                {' · '}
                                <button
                                  type="button"
                                  className="underline-offset-2 hover:underline"
                                  onClick={() => view.report_path && openInFiles(view.report_path)}
                                  title="Open the report file — correcting it corrects every future sweep"
                                >
                                  edit in Files
                                </button>
                              </>
                            )}
                          </span>
                        )}
                      </div>
                      {view.report ? (
                        <article className="rounded-md border px-5 py-4">
                          <MarkdownRenderer content={view.report} />
                        </article>
                      ) : (
                        <p className="rounded-md border border-dashed px-4 py-6 text-center text-xs text-muted-foreground">
                          No report yet. The first revision lands after the next
                          sweep with something worth saying
                          {!view.paused && view.next_run_at
                            ? ` — due ${fmtWhen(view.next_run_at)}`
                            : ''}.
                          An empty sweep is reported honestly, never padded.
                        </p>
                      )}
                    </section>
                  )}

                  {/* ── Recent changes — ONE attributed lifecycle rail ── */}
                  {desk.phase === 'ready' && deskRoot && (
                    <section>
                      <SectionHeading className="mb-2">Recent changes</SectionHeading>
                      <DeskActivityRail
                        deskRoot={deskRoot}
                        sweeps={view?.recent_sweeps ?? []}
                        refreshNonce={activityNonce}
                        onReverted={refreshDesk}
                      />
                    </section>
                  )}

                  {/* ── The setup — layer 2 held up to the light (D2.2) ── */}
                  {desk.phase === 'ready' && view && (
                    <section className="space-y-5">
                      <SectionHeading className="mb-0">Setup</SectionHeading>

                      {/* Criterion */}
                      <div className="rounded-md border">
                        <div className="flex items-center justify-between border-b px-4 py-2">
                          <span className="text-xs font-medium">What matters here</span>
                          {lanesEnabled && (
                            <SeedButton onClick={() => seedChat('Refine the criterion: ')}>
                              refine in chat
                            </SeedButton>
                          )}
                        </div>
                        <div className="px-4 py-3">
                          {view.criterion ? (
                            <MarkdownRenderer content={view.criterion} compact />
                          ) : (
                            <p className="text-xs text-muted-foreground">
                              No criterion declared — sweeps hold a conservative
                              bar. Declaring one sharpens every future sweep.
                            </p>
                          )}
                        </div>
                      </div>

                      {/* Source portfolio + the earn-their-keep reading */}
                      <div className="rounded-md border">
                        <div className="flex items-center justify-between border-b px-4 py-2">
                          <span className="text-xs font-medium">Sources</span>
                          {lanesEnabled && (
                            <SeedButton onClick={() => seedChat('Add a source: ')}>
                              add in chat
                            </SeedButton>
                          )}
                        </div>
                        {view.sources.length === 0 ? (
                          <p className="px-4 py-3 text-xs text-muted-foreground">
                            No sources declared yet.
                          </p>
                        ) : (
                          <ul className="divide-y">
                            {view.sources.map((s) => {
                              const windowSweeps = view.window_sweeps ?? 0;
                              const windowChanges = view.window_changes ?? 0;
                              const idle =
                                windowChanges >= 3 && (s.cited_count ?? 0) === 0;
                              return (
                                <li key={s.id} className="flex items-center gap-3 px-4 py-2">
                                  <div className="min-w-0 flex-1">
                                    <div className="truncate text-xs font-medium">{s.id}</div>
                                    <div className="truncate text-[11px] text-muted-foreground">{s.url}</div>
                                  </div>
                                  {windowSweeps > 0 && (
                                    <span
                                      className={`shrink-0 text-[11px] tabular-nums ${idle ? 'text-amber-600' : 'text-muted-foreground'}`}
                                      title={`Of the last ${windowSweeps} sweeps, ${s.fed_count ?? 0} fetched this source; ${s.cited_count ?? 0} of the last ${windowChanges} report changes drew on it. A source that feeds sweeps but never reaches the report may not be earning its keep.`}
                                    >
                                      {s.fed_count ?? 0}/{windowSweeps} sweeps ·{' '}
                                      {s.cited_count ?? 0}/{windowChanges} changes
                                    </span>
                                  )}
                                  {lanesEnabled && (
                                    <SeedButton onClick={() => seedChat(`Stop watching ${s.id}. `)}>
                                      prune
                                    </SeedButton>
                                  )}
                                </li>
                              );
                            })}
                          </ul>
                        )}
                      </div>

                      {/* Cadence */}
                      <div className="flex items-center justify-between rounded-md border px-4 py-2.5">
                        <div className="text-xs">
                          <span className="font-medium">Cadence</span>
                          <span className="ml-2 font-mono text-muted-foreground">
                            {Array.isArray(view.schedule)
                              ? view.schedule.join(' · ')
                              : view.schedule || '—'}
                          </span>
                        </div>
                        {lanesEnabled && (
                          <SeedButton onClick={() => seedChat('Change the cadence: ')}>
                            change in chat
                          </SeedButton>
                        )}
                      </div>
                    </section>
                  )}

                  {/* ── The legacy shelf — the record is the record ── */}
                  {view && view.briefs.length > 0 && (
                    <details className="group">
                      <summary className="cursor-pointer text-xs font-medium text-muted-foreground hover:text-foreground">
                        Earlier briefs ({view.briefs.length}) — the shelf before the
                        living report; new sweeps don&apos;t add here
                      </summary>
                      <ul className="mt-2 divide-y rounded-md border">
                        {view.briefs.map((b) => (
                          <li key={b.path}>
                            <button
                              type="button"
                              onClick={() => openInFiles(b.path)}
                              className="flex w-full items-baseline justify-between gap-3 px-3 py-2 text-left hover:bg-muted/60"
                            >
                              <span className="truncate text-xs">{b.title}</span>
                              <span className="shrink-0 text-[11px] text-muted-foreground">{b.date || ''}</span>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                </div>
              </main>
            )}

            {/* ── Researcher — the lane the lifecycle runs through ── */}
            {showLaneColumn && (
              <aside
                className={`flex ${wb.singlePane ? 'min-w-0 flex-1' : `${laneWidthClass} shrink-0 border-l`} flex-col`}
              >
                {boundLane ? (
                  <LanePanel
                    key={boundLane.id}
                    laneId={boundLane.id}
                    laneName={boundLane.name}
                    modelLabel={modelLabel}
                    speakerLabel={speakerLabel}
                    onArtifactWrite={onLaneWrite}
                    artifactWrite="link"
                    composerSeed={seed}
                    suggestions={setupIncomplete ? SETUP_SUGGESTIONS : TUNE_SUGGESTIONS}
                    emptyState={
                      <div className="space-y-2 text-center text-xs text-muted-foreground">
                        <p className="text-sm font-medium text-foreground/80">
                          {setupIncomplete
                            ? 'Tell Researcher what to watch.'
                            : 'This folder is Researcher’s desk.'}
                        </p>
                        <p>
                          Say what matters here and where to look — Researcher
                          writes the criterion and the watch declaration into
                          the folder, and the standing loop takes it from
                          there. Add or prune sources, change the cadence, or
                          tighten the criterion the same way, any time.
                        </p>
                      </div>
                    }
                  />
                ) : (
                  <div className="flex h-full items-center justify-center p-6 text-center text-xs text-muted-foreground">
                    {creatingLane || desk.phase === 'loading'
                      ? <Loader2 className="h-4 w-4 animate-spin" />
                      : 'Researcher’s lane could not be opened.'}
                  </div>
                )}
              </aside>
            )}
          </>
        ) : (
          /* ── The front door — nothing selected ── */
          <main className="flex min-h-0 min-w-0 flex-1 items-center justify-center">
            <div className="max-w-sm space-y-3 p-6 text-center">
              <RadarIcon className="mx-auto h-8 w-8 text-muted-foreground" />
              <h1 className="text-lg font-semibold">Watch a folder</h1>
              <p className="text-sm text-muted-foreground">
                Point Researcher at a folder and it keeps a living report there
                — sweeping the folder&apos;s declared sources on a schedule and
                folding what changed into the current understanding, under a
                criterion you set in plain words.
              </p>
              {lanesEnabled === false ? (
                <p className="text-xs text-amber-700 dark:text-amber-400">
                  Watching a folder is set up in conversation with Researcher,
                  which isn&apos;t enabled on this workspace yet.
                </p>
              ) : (
                <button
                  type="button"
                  onClick={() => setAttachOpen(true)}
                  className="inline-flex items-center gap-1.5 rounded-md border bg-foreground px-3 py-1.5 text-sm text-background"
                >
                  <Plus className="h-3.5 w-3.5" /> Watch a folder
                </button>
              )}
            </div>
          </main>
        )}
      </div>

      {/* ── single-pane: the Desk/Researcher tab bar ── */}
      {wb.singlePane && topic && lanesEnabled && (
        <nav className="flex shrink-0 border-t">
          {([['desk', 'Desk'], ['lane', 'Researcher']] as const).map(([pane, label]) => (
            <button
              key={pane}
              type="button"
              onClick={() => setActivePane(pane)}
              className={`flex-1 py-2.5 text-center text-xs font-medium ${
                activePane === pane
                  ? 'border-t-2 border-foreground text-foreground'
                  : 'text-muted-foreground'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      )}

      <AttachFolderModal
        open={attachOpen}
        existingTopics={(hubs ?? []).map((h) => h.topic)}
        onClose={() => setAttachOpen(false)}
        onAttach={(t) => {
          setAttachOpen(false);
          selectTopic(t);
        }}
      />
    </div>
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

// ---------------------------------------------------------------------------
// The watched-folder rail — rows are FOLDERS (path-shaped identity), plus the
// desk's one action. A selected topic with no roster row renders as the
// setting-up row (the unconfigured desk is a real place, refresh included).
// ---------------------------------------------------------------------------

function FolderRail({
  hubs,
  topic,
  condensed,
  lanesEnabled,
  onSelect,
  onAttach,
}: {
  hubs: RadarHubSummary[] | null;
  topic: string | null;
  condensed: boolean;
  lanesEnabled: boolean | null;
  onSelect: (topic: string) => void;
  onAttach: () => void;
}) {
  const settingUp = topic && !(hubs ?? []).some((h) => h.topic === topic);
  return (
    <aside className={`flex ${condensed ? 'w-52' : 'w-64'} shrink-0 flex-col border-r`}>
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <RadarIcon className="h-4 w-4" /> Radar
        </div>
        <button
          type="button"
          title={
            lanesEnabled === false
              ? 'Watching a folder is set up in conversation with Researcher, which isn’t enabled here yet'
              : 'Watch a folder'
          }
          disabled={lanesEnabled === false}
          onClick={onAttach}
          className="rounded p-1 hover:bg-muted disabled:opacity-40"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {hubs === null ? (
          <div className="p-4 text-xs text-muted-foreground">Looking…</div>
        ) : (
          <>
            {settingUp && topic && (
              <div className="block w-full border-b bg-muted px-4 py-3 text-left">
                <FolderRow
                  topic={topic}
                  subtitle="setting up with Researcher…"
                  dot="pending"
                />
              </div>
            )}
            {hubs.length === 0 && !settingUp ? (
              <div className="p-4 text-xs text-muted-foreground">
                No folders watched yet. Point Researcher at one and it keeps a
                living report while you&apos;re away.
              </div>
            ) : (
              hubs.map((h) => (
                <button
                  key={h.topic}
                  type="button"
                  onClick={() => onSelect(h.topic)}
                  className={`block w-full border-b px-4 py-3 text-left hover:bg-muted/60 ${
                    topic === h.topic ? 'bg-muted' : ''
                  }`}
                >
                  <FolderRow
                    topic={h.topic}
                    subtitle={
                      h.report_title ??
                      (h.brief_count > 0 ? 'earlier briefs only' : 'no report yet')
                    }
                    dot={h.paused ? 'paused' : 'active'}
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

function FolderRow({
  topic,
  subtitle,
  dot,
}: {
  topic: string;
  subtitle: string;
  dot: 'active' | 'paused' | 'pending';
}) {
  const segments = topic.split('/');
  const name = segments[segments.length - 1];
  const parents = segments.slice(0, -1).join(' / ');
  return (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5 text-sm font-medium">
          <Folder className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
          <span className="truncate">{name}</span>
        </span>
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${
            dot === 'active' ? 'bg-emerald-500' : dot === 'paused' ? 'bg-amber-500' : 'bg-zinc-400'
          }`}
          title={dot === 'active' ? 'Standing watch' : dot === 'paused' ? 'Paused' : 'Setting up'}
        />
      </div>
      <div className="mt-0.5 truncate text-xs text-muted-foreground">
        {parents ? `${parents} / · ` : ''}{subtitle}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// The folder switcher — the rail, folded into the header on narrow rungs
// (rule 15: chrome folds first; the roster never costs the report width).
// ---------------------------------------------------------------------------

function FolderSwitcher({
  hubs,
  topic,
  open,
  setOpen,
  onSelect,
  onAttach,
  lanesEnabled,
}: {
  hubs: RadarHubSummary[] | null;
  topic: string;
  open: boolean;
  setOpen: (v: boolean) => void;
  onSelect: (topic: string) => void;
  onAttach: () => void;
  lanesEnabled: boolean | null;
}) {
  return (
    <div className="relative min-w-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex min-w-0 items-center gap-2 rounded px-1 py-0.5 hover:bg-muted"
      >
        <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
        <h1 className="truncate text-lg font-semibold">
          {topic.split('/').join(' / ')}
        </h1>
        <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-20 mt-1 w-72 rounded-md border bg-card py-1 shadow-lg">
          {(hubs ?? []).map((h) => (
            <button
              key={h.topic}
              type="button"
              onClick={() => onSelect(h.topic)}
              className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted ${
                h.topic === topic ? 'font-medium' : ''
              }`}
            >
              <Folder className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="truncate">{h.topic}</span>
            </button>
          ))}
          <div className="my-1 border-t" />
          <button
            type="button"
            onClick={onAttach}
            disabled={lanesEnabled === false}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted disabled:opacity-40"
          >
            <Plus className="h-3.5 w-3.5 shrink-0" /> Watch a folder…
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// The one direct gesture: choosing the folder (ADR-567 D3 / ADR-384 layer 1).
// The kernel's own tree picker renders the workspace; folders under the
// commons root are selectable; an optional new-subfolder name lets the
// operator mint meaning without leaving the gesture.
// ---------------------------------------------------------------------------

function AttachFolderModal({
  open, existingTopics, onClose, onAttach,
}: {
  open: boolean;
  existingTopics: string[];
  onClose: () => void;
  onAttach: (topic: string) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [newName, setNewName] = useState('');

  useEffect(() => {
    if (open) { setSelected(null); setNewName(''); }
  }, [open]);

  if (!open) return null;

  const selectable = (n: WorkspaceTreeNode) =>
    n.type === 'folder' &&
    (n.path === OPERATION_ROOT || n.path.startsWith(`${OPERATION_ROOT}/`));

  const rel = selected && selected.startsWith(`${OPERATION_ROOT}/`)
    ? selected.slice(OPERATION_ROOT.length + 1)
    : selected === OPERATION_ROOT ? '' : null;
  const extra = kebab(newName);
  const topic = rel === null ? null : [rel, extra].filter(Boolean).join('/') || null;
  const alreadyWatched = topic !== null && existingTopics.includes(topic);

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
          aria-label="Watch a folder"
          style={{ maxHeight: '70vh' }}
        >
          <div className="flex items-start justify-between border-b border-border px-5 py-3.5">
            <div className="min-w-0">
              <h3 className="text-base font-semibold text-card-foreground">Watch a folder</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">
                Choose where the research lives — Researcher sets the rest up
                with you in conversation.
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

          <div className="min-h-0 flex-1 overflow-y-auto">
            <WorkspacePickerBody
              mode="folder"
              selectable={selectable}
              folderDisabledTitle={(n) =>
                selectable(n) ? undefined : 'Watched folders live under Documents'}
              selected={selected}
              onSelect={setSelected}
              emptyMessage="No folders yet — name a new one below."
            />
          </div>

          <div className="space-y-2 border-t border-border px-5 py-3">
            <label className="block text-xs">
              <span className="mb-1 block text-muted-foreground">
                New folder inside the selection (optional)
              </span>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="the-acme-deal"
                className="w-full rounded-md border bg-background px-2.5 py-1.5 text-sm"
              />
            </label>
            <div className="flex items-center justify-between gap-3">
              <span className="min-w-0 truncate text-xs text-muted-foreground">
                {topic
                  ? alreadyWatched
                    ? `${topic} is already watched — this opens its desk.`
                    : `Will watch: operation/${topic}/`
                  : 'Pick a folder (or the Documents root plus a new name).'}
              </span>
              <button
                type="button"
                disabled={!topic}
                onClick={() => topic && onAttach(topic)}
                className="shrink-0 rounded-md border bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-50"
              >
                {alreadyWatched ? 'Open desk' : 'Attach'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>,
    document.body,
  );
}
