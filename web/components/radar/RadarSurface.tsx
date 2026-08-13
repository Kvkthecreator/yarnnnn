'use client';

/**
 * RadarSurface — the Researcher's desk (ADR-567, re-cutting ADR-486 R2).
 *
 * The folder is the object; the app is where it is MANAGED. The center pane
 * shows the watched folder's lifecycle — its identity, its setup restated
 * from the files (CRITERION.md + _radar.yaml), its recent changes, and its
 * living report (ADR-565 D1) — and the bound lane beside it is how the
 * member and Researcher run that lifecycle together (the Docs/Studio shape:
 * artifact + properties + lane; ADR-467 D1's fourth bound-lane app).
 *
 * Creation is conversational with ONE direct gesture (ADR-567 D3): picking
 * the folder is the operator's unscriptable act (ADR-384/564 layer 1 —
 * meaning is never delegated); everything after happens in the lane —
 * Researcher authors CRITERION.md and _radar.yaml through its ordinary
 * tools, and the kernel discovers the declaration on its next tick. The
 * pre-567 create FORM is deleted, not hidden (Singular Implementation).
 *
 * Reports/briefs open in Files (Quick Look) — plain markdown; the record
 * never requires the app. Direct switches (Pause) stay buttons: not every
 * gesture becomes chat.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  Folder, Loader2, Pause, Play, Plus, Radar as RadarIcon, RefreshCw, X,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import {
  useSurfaceParam, useSurfacePreferences,
} from '@/lib/shell/useSurfacePreferences';
import { useDeclareFocus } from '@/lib/shell/useSurfaceFocus';
import { LanePanel } from '@/components/chat-surface/LanePanel';
import { WorkspacePickerBody } from '@/components/workspace/WorkspacePicker';
import type { WorkspaceTreeNode } from '@/types';
import { Z_CONFIRM_BACKDROP, Z_CONFIRM_DIALOG } from '@/lib/shell/z-tiers';

// ---------------------------------------------------------------------------
// Shapes (mirror routes/radar.py + routes/lanes.py)
// ---------------------------------------------------------------------------

interface HubSource { id: string; url: string; max_entries?: number }

interface HubSummary {
  topic: string;
  declaration_path: string;
  schedule?: string | string[] | null;
  paused: boolean;
  /** ADR-564 D2 — what matters here (CRITERION.md); replaces the steer. */
  criterion?: string | null;
  sources: HubSource[];
  last_run_at?: string | null;
  next_run_at?: string | null;
  /** ADR-565 D1 — the living report, when a sweep has landed one. */
  report_path?: string | null;
  report_title?: string | null;
  // The pre-ADR-565 shelf — legacy reads only.
  latest_brief_path?: string | null;
  latest_brief_title?: string | null;
  brief_count: number;
}

interface BriefEntry { path: string; title: string; date?: string | null }

interface SweepEvent {
  slug: string;
  status: string;
  created_at?: string | null;
  error_reason?: string | null;
}

interface HubView extends HubSummary {
  /** The living report head content (ADR-565 D1). */
  report?: string | null;
  briefs: BriefEntry[];
  recent_sweeps: SweepEvent[];
  signal_observed_at?: string | null;
}

interface LaneInfo {
  id: string;
  name: string;
  model: string;
  agent?: string | null;
  app?: string | null;
  artifact_path?: string | null;
  status?: string;
}

// ---------------------------------------------------------------------------

const OPERATION_ROOT = '/workspace/operation';

function topicFromDeclarationPath(path: string): string | null {
  // Any depth under operation/ (ADR-565 D3) — the topic is the folder path.
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

// ---------------------------------------------------------------------------

export default function RadarSurface() {
  const { navigateToSurface } = useSurfacePreferences();
  const param = useSurfaceParam('radar');

  const [hubs, setHubs] = useState<HubSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<HubView | null>(null);
  const [viewLoading, setViewLoading] = useState(false);
  const [viewError, setViewError] = useState<string | null>(null);
  const [attachOpen, setAttachOpen] = useState(false);
  // A folder chosen for watching that carries NO declaration yet (ADR-567 D3
  // — the desk's unconfigured state; Researcher sets it up in the lane, the
  // scheduler discovers it, and the roster row appears on the next refresh).
  const [pendingFolder, setPendingFolder] = useState<string | null>(null);

  // The desk's subject this render: an existing hub or a pending folder.
  const deskTopic = pendingFolder ?? selected;
  const deskRoot = deskTopic ? `${OPERATION_ROOT}/${deskTopic}` : null;
  const reportPath = deskRoot ? `${deskRoot}/report.md` : null;

  // ADR-522 — Radar declares its focus deliberately: the hub is the unit.
  useDeclareFocus(
    'radar',
    deskTopic
      ? {
          app: 'radar',
          path: view?.declaration_path ?? (deskRoot ? `${deskRoot}/_radar.yaml` : null),
          scope: 'document',
          id: null,
          pageIndex: null,
          label: deskTopic,
          excerpt: view?.report_title ?? view?.latest_brief_title ?? null,
          viewport: null,
        }
      : null,
  );

  const loadHubs = useCallback(async (): Promise<HubSummary[]> => {
    try {
      const rows = await api.radar.list();
      setHubs(rows);
      return rows;
    } catch {
      setHubs([]);
      return [];
    }
  }, []);

  const loadView = useCallback(async (topic: string) => {
    setViewLoading(true);
    try {
      setView(await api.radar.get(topic));
      setViewError(null);
    } catch (e) {
      setView(null);
      setViewError(e instanceof Error ? e.message : 'failed to load the folder');
    } finally {
      setViewLoading(false);
    }
  }, []);

  // Mount: roster, then the deep-link — `radar.file` (Files association)
  // wins over `radar.topic`; else the first watched folder.
  useEffect(() => {
    void (async () => {
      const rows = await loadHubs();
      const fromFile = topicFromDeclarationPath(param.get('file') || '');
      const fromTopic = param.get('topic');
      const topic =
        (fromFile && rows.some((h) => h.topic === fromFile) && fromFile) ||
        (fromTopic && rows.some((h) => h.topic === fromTopic) && fromTopic) ||
        rows[0]?.topic || null;
      setSelected(topic);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selected && !pendingFolder) void loadView(selected);
    else setView(null);
  }, [selected, pendingFolder, loadView]);

  const selectHub = useCallback((topic: string) => {
    setSelected(topic);
    setPendingFolder(null);
    param.set({ topic, file: null });
  }, [param]);

  const togglePause = useCallback(async () => {
    if (!view) return;
    const updated = await api.radar.update(view.topic, { paused: !view.paused });
    setView((v) => (v ? { ...v, paused: updated.paused } : v));
    void loadHubs();
  }, [view, loadHubs]);

  const openInFiles = useCallback((path: string) => {
    navigateToSurface('files', { path });
  }, [navigateToSurface]);

  // ── Lane environment + the desk's bound lane (find-or-create) ───────────
  const [lanesEnabled, setLanesEnabled] = useState<boolean | null>(null);
  const [lanes, setLanes] = useState<LaneInfo[]>([]);
  const [agents, setAgents] = useState<Array<{ slug: string; name: string }>>([]);
  const [apps, setApps] = useState<Array<{ slug: string; resident: string; name: string }>>([]);
  const [models, setModels] = useState<Array<{ id: string; label: string }>>([]);

  const refreshLanes = useCallback(async () => {
    try {
      const res = await api.lanes.list(true);
      setLanesEnabled(res.enabled);
      setLanes(res.lanes as LaneInfo[]);
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
      lanes.find(
        (l) => l.status === 'active' && l.artifact_path === reportPath,
      ) ?? null
    );
  }, [lanes, reportPath]);

  const [creatingLane, setCreatingLane] = useState(false);
  useEffect(() => {
    if (!reportPath || !deskTopic || !lanesEnabled || boundLane || creatingLane) return;
    setCreatingLane(true);
    api.lanes
      .create({
        name: `Watch: ${deskTopic}`.slice(0, 60),
        // ADR-562 D3/ADR-567 — the surface names WHICH APP is asking; the
        // resident (Researcher) resolves server-side from radar's own
        // registration, and lane_meta.app selects the DESK job overlay.
        app: 'radar',
        artifact_path: reportPath,
      })
      .then(() => refreshLanes())
      .catch(() => { /* the desk still renders; the lane column shows why */ })
      .finally(() => setCreatingLane(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportPath, deskTopic, lanesEnabled, boundLane]);

  const modelLabel = useMemo(() => {
    if (!boundLane) return '';
    return models.find((m) => m.id === boundLane.model)?.label ?? boundLane.model;
  }, [boundLane, models]);

  // ADR-562 D5 — the member reads WHO: the app's name for its resident, else
  // the agent's own name ("Researcher"), else the engine label.
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

  // A write landed from the lane (criterion, declaration, report, …): the
  // desk re-reads the files — and a pending folder promotes to a real hub
  // the moment its declaration is discovered in the roster.
  const onLaneWrite = useCallback(() => {
    void (async () => {
      const rows = await loadHubs();
      if (pendingFolder && rows.some((h) => h.topic === pendingFolder)) {
        setSelected(pendingFolder);
        setPendingFolder(null);
        param.set({ topic: pendingFolder, file: null });
      } else if (selected && !pendingFolder) {
        void loadView(selected);
      }
    })();
  }, [loadHubs, loadView, pendingFolder, selected, param]);

  // ── render ────────────────────────────────────────────────────────────
  return (
    <div className="flex h-full min-h-0 bg-background text-foreground">
      {/* Watched folders (the roster) */}
      <aside className="flex w-64 shrink-0 flex-col border-r">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <RadarIcon className="h-4 w-4" /> Radar
          </div>
          <button
            type="button"
            title="Watch a folder"
            onClick={() => setAttachOpen(true)}
            className="rounded p-1 hover:bg-muted"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {hubs === null ? (
            <div className="p-4 text-xs text-muted-foreground">Looking…</div>
          ) : (
            <>
              {pendingFolder && (
                <div className="block w-full border-b bg-muted px-4 py-3 text-left">
                  <div className="flex items-center gap-1.5 text-sm font-medium">
                    <Folder className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">{pendingFolder}</span>
                  </div>
                  <div className="mt-0.5 truncate text-xs text-muted-foreground">
                    setting up with Researcher…
                  </div>
                </div>
              )}
              {hubs.length === 0 && !pendingFolder ? (
                <div className="p-4 text-xs text-muted-foreground">
                  No folders watched yet. Point Researcher at one and it keeps
                  a living report while you&apos;re away.
                </div>
              ) : (
                hubs.map((h) => (
                  <button
                    key={h.topic}
                    type="button"
                    onClick={() => selectHub(h.topic)}
                    className={`block w-full border-b px-4 py-3 text-left hover:bg-muted/60 ${
                      selected === h.topic && !pendingFolder ? 'bg-muted' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="flex min-w-0 items-center gap-1.5 text-sm font-medium">
                        <Folder className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <span className="truncate">{h.topic}</span>
                      </span>
                      {h.paused && <Pause className="h-3 w-3 shrink-0 text-muted-foreground" />}
                    </div>
                    <div className="mt-0.5 truncate text-xs text-muted-foreground">
                      {h.report_title
                        ? h.report_title
                        : h.brief_count > 0
                          ? `${h.brief_count} brief${h.brief_count === 1 ? '' : 's'}${h.latest_brief_title ? ` · ${h.latest_brief_title}` : ''}`
                          : 'no report yet'}
                    </div>
                  </button>
                ))
              )}
            </>
          )}
        </div>
      </aside>

      {/* The desk: the folder's lifecycle (center) + Researcher (right) */}
      {deskTopic ? (
        <>
          <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">
            <div className="mx-auto max-w-3xl space-y-6 p-6">
              {/* Folder identity — what this desk manages */}
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <h1 className="truncate text-lg font-semibold">
                      {deskTopic.split('/').join(' / ')}
                    </h1>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {pendingFolder
                      ? 'Not watched yet — Researcher sets it up in the conversation.'
                      : view
                        ? `${view.paused ? 'Paused' : 'Standing'} · last sweep ${fmtWhen(view.last_run_at)} · next ${view.paused ? '—' : fmtWhen(view.next_run_at)}`
                        : viewLoading ? 'Loading…' : ''}
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
                </div>
                {view && (
                  <div className="flex shrink-0 items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void loadView(view.topic)}
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

              {/* An unparseable declaration is a LOUD repair job (ADR-567 D6) */}
              {!pendingFolder && !view && !viewLoading && viewError && (
                <div className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
                  This folder&apos;s declaration could not be read
                  ({viewError}). The standing loop is dark until it is repaired
                  — ask Researcher to fix <code>_radar.yaml</code>.
                </div>
              )}

              {/* The setup, restated from the files (layer 2 held up to the light) */}
              {view?.criterion && (
                <div className="rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">What matters here · </span>
                  {view.criterion}
                </div>
              )}

              {/* The living report — the felt unit (ADR-565 D1) */}
              {!pendingFolder && (
                <section>
                  <h2 className="mb-2 text-sm font-medium">Report</h2>
                  {view?.report ? (
                    <div className="rounded-md border">
                      <button
                        type="button"
                        onClick={() => view.report_path && openInFiles(view.report_path)}
                        className="flex w-full items-baseline justify-between gap-3 border-b px-3 py-2.5 text-left hover:bg-muted/60"
                        title="Open in Files (history + diffs live there)"
                      >
                        <span className="truncate text-sm font-medium">
                          {view.report_title || 'The living report'}
                        </span>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          revised {fmtWhen(view.last_run_at)}
                        </span>
                      </button>
                      <div className="max-h-96 overflow-y-auto whitespace-pre-wrap px-3 py-2.5 text-sm">
                        {view.report}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      No report yet — the first revision lands after the next
                      sweep with something worth saying. An empty sweep is
                      reported honestly, never padded.
                    </p>
                  )}
                </section>
              )}

              {/* Watching — the source portfolio + cadence */}
              {view && view.sources.length > 0 && (
                <section>
                  <h2 className="mb-2 text-sm font-medium">Watching</h2>
                  <ul className="space-y-1">
                    {view.sources.map((s) => (
                      <li key={s.id} className="truncate text-xs text-muted-foreground">
                        <span className="font-medium text-foreground">{s.id}</span> · {s.url}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-1.5 text-xs text-muted-foreground">
                    Add, prune, or retune sources by telling Researcher.
                  </p>
                </section>
              )}

              {/* Recent changes — the lifecycle, straight off the ledger */}
              {view && (
                <section>
                  <h2 className="mb-2 text-sm font-medium">Recent sweeps</h2>
                  {view.recent_sweeps.length === 0 ? (
                    <p className="text-xs text-muted-foreground">No sweeps recorded yet.</p>
                  ) : (
                    <ul className="space-y-1">
                      {view.recent_sweeps.map((e, i) => (
                        <li key={`${e.slug}-${e.created_at}-${i}`} className="flex items-center gap-2 text-xs">
                          <span className={
                            e.status === 'success' ? 'text-emerald-600'
                              : e.status === 'skipped' ? 'text-muted-foreground'
                                : 'text-red-600'
                          }>
                            ●
                          </span>
                          <span className="text-muted-foreground">{fmtWhen(e.created_at)}</span>
                          <span>{e.slug.startsWith('radar-brief') ? 'derive' : 'sweep'}</span>
                          <span className="text-muted-foreground">
                            {e.status}{e.error_reason ? ` · ${e.error_reason}` : ''}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}

              {/* The pre-ADR-565 briefs shelf — legacy reads only */}
              {view && view.briefs.length > 0 && (
                <section>
                  <h2 className="mb-2 text-sm font-medium">Earlier briefs</h2>
                  <ul className="divide-y rounded-md border">
                    {view.briefs.map((b) => (
                      <li key={b.path}>
                        <button
                          type="button"
                          onClick={() => openInFiles(b.path)}
                          className="flex w-full items-baseline justify-between gap-3 px-3 py-2.5 text-left hover:bg-muted/60"
                        >
                          <span className="truncate text-sm">{b.title}</span>
                          <span className="shrink-0 text-xs text-muted-foreground">{b.date || ''}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          </main>

          {/* Researcher — the lane the lifecycle runs through (ADR-567 D2/D3) */}
          {lanesEnabled && (
            <aside className="flex w-[400px] shrink-0 flex-col border-l">
              {boundLane ? (
                <LanePanel
                  key={boundLane.id}
                  laneId={boundLane.id}
                  laneName={boundLane.name}
                  modelLabel={modelLabel}
                  speakerLabel={speakerLabel}
                  onArtifactWrite={onLaneWrite}
                  emptyState={
                    <div className="space-y-2 text-center text-xs text-muted-foreground">
                      <p className="text-sm font-medium text-foreground/80">
                        {pendingFolder || !view
                          ? 'Tell Researcher what to watch.'
                          : 'This folder is Researcher’s desk.'}
                      </p>
                      <p>
                        Say what matters here and where to look — Researcher
                        writes the criterion and the watch declaration into the
                        folder, and the standing loop takes it from there. Add
                        or prune sources, change the cadence, or tighten the
                        criterion the same way, any time.
                      </p>
                    </div>
                  }
                />
              ) : (
                <div className="flex h-full items-center justify-center p-6 text-center text-xs text-muted-foreground">
                  {creatingLane
                    ? <Loader2 className="h-4 w-4 animate-spin" />
                    : 'Researcher’s lane could not be opened.'}
                </div>
              )}
            </aside>
          )}
        </>
      ) : (
        <main className="flex min-h-0 min-w-0 flex-1 items-center justify-center">
          <div className="max-w-sm space-y-3 p-6 text-center">
            <RadarIcon className="mx-auto h-8 w-8 text-muted-foreground" />
            <h1 className="text-lg font-semibold">Watch a folder</h1>
            <p className="text-sm text-muted-foreground">
              Point Researcher at a folder and it keeps a living report there —
              sweeping the folder&apos;s declared sources on a schedule and
              folding what changed into the current understanding, under a
              criterion you set in plain words.
            </p>
            <button
              type="button"
              onClick={() => setAttachOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-md border bg-foreground px-3 py-1.5 text-sm text-background"
            >
              <Plus className="h-3.5 w-3.5" /> Watch a folder
            </button>
          </div>
        </main>
      )}

      <AttachFolderModal
        open={attachOpen}
        existingTopics={(hubs ?? []).map((h) => h.topic)}
        onClose={() => setAttachOpen(false)}
        onAttach={(topic) => {
          setAttachOpen(false);
          if ((hubs ?? []).some((h) => h.topic === topic)) {
            selectHub(topic);
          } else {
            setPendingFolder(topic);
            setSelected(null);
            setView(null);
            setViewError(null);
          }
        }}
      />
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
                    ? `${topic} is already watched — Attach opens its desk.`
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
