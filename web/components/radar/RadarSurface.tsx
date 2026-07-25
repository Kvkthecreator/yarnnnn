'use client';

/**
 * RadarSurface — the AI Radar app window (ADR-486 R2, re-cut 2026-07-25).
 *
 * The STANDING app: topic hubs that sweep while the member is away. This is
 * a dedicated app in the ADR-472 sense — its own surface slug, param
 * namespace (`radar.file` / `radar.topic`), and chrome — NEVER a view grown
 * inside Files (the Images lesson: an app developed inside an existing
 * surface forces a carve later). Files stays the finder; opening a hub's
 * `_radar.yaml` from Files routes here via the type→app association.
 *
 * Layout: hub roster (left rail) + the composed hub view (main) — the D5
 * lazy projection served by GET /api/radar/hubs/{topic}: declaration ·
 * briefs shelf · sweep health · signal freshness. Nothing is stored for
 * this window; substrate + ledger are the only sources.
 *
 * Briefs open in Files (Quick Look) — a brief is a plain markdown file and
 * the record must never require the app. The app owns the STANDING loop's
 * legibility, not a private reader.
 *
 * launcher_tier is search-only until R3 (ADR-486 D7): the app works today,
 * summonable by name; the dock icon is earned by the falsifier window.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  Loader2, Pause, Play, Plus, Radar as RadarIcon, RefreshCw,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import {
  useSurfaceParam, useSurfacePreferences,
} from '@/lib/shell/useSurfacePreferences';

// ---------------------------------------------------------------------------
// Shapes (mirror routes/radar.py)
// ---------------------------------------------------------------------------

interface HubSource { id: string; url: string; max_entries?: number }

interface HubSummary {
  topic: string;
  declaration_path: string;
  schedule?: string | string[] | null;
  paused: boolean;
  prompt?: string | null;
  sources: HubSource[];
  last_run_at?: string | null;
  next_run_at?: string | null;
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
  briefs: BriefEntry[];
  recent_sweeps: SweepEvent[];
  signal_observed_at?: string | null;
}

// ---------------------------------------------------------------------------

const CADENCES: Array<{ label: string; cron: string }> = [
  { label: 'Daily · 06:00 KST', cron: '0 21 * * *' },
  { label: 'Every 6 hours', cron: '0 */6 * * *' },
  { label: 'Hourly', cron: '0 * * * *' },
  { label: 'Weekly · Mon 06:00 KST', cron: '0 21 * * 0' },
];

function topicFromDeclarationPath(path: string): string | null {
  const m = /operation\/([^/]+)\/_radar\.yaml$/.exec(path || '');
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

export default function RadarSurface() {
  const { navigateToSurface } = useSurfacePreferences();
  const param = useSurfaceParam('radar');

  const [hubs, setHubs] = useState<HubSummary[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<HubView | null>(null);
  const [viewLoading, setViewLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHubs = useCallback(async (): Promise<HubSummary[]> => {
    try {
      const rows = await api.radar.list();
      setHubs(rows);
      return rows;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed to load hubs');
      setHubs([]);
      return [];
    }
  }, []);

  const loadView = useCallback(async (topic: string) => {
    setViewLoading(true);
    try {
      setView(await api.radar.get(topic));
      setError(null);
    } catch (e) {
      setView(null);
      setError(e instanceof Error ? e.message : 'failed to load hub');
    } finally {
      setViewLoading(false);
    }
  }, []);

  // Mount: load the roster, then resolve the deep-link — `radar.file` (a
  // declaration path handed over by the Files association) wins over
  // `radar.topic`; else the first hub.
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
    if (selected) void loadView(selected);
    else setView(null);
  }, [selected, loadView]);

  const selectHub = useCallback((topic: string) => {
    setSelected(topic);
    setCreating(false);
    param.set({ topic, file: null });
  }, [param]);

  const togglePause = useCallback(async () => {
    if (!view) return;
    const updated = await api.radar.update(view.topic, { paused: !view.paused });
    setView((v) => (v ? { ...v, paused: updated.paused } : v));
    void loadHubs();
  }, [view, loadHubs]);

  const openBrief = useCallback((path: string) => {
    navigateToSurface('files', { path });
  }, [navigateToSurface]);

  // ── render ────────────────────────────────────────────────────────────
  return (
    <div className="flex h-full min-h-0 bg-background text-foreground">
      {/* Hub roster */}
      <aside className="flex w-64 shrink-0 flex-col border-r">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <RadarIcon className="h-4 w-4" /> Radar
          </div>
          <button
            type="button"
            title="New hub"
            onClick={() => setCreating(true)}
            className="rounded p-1 hover:bg-muted"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {hubs === null ? (
            <div className="p-4 text-xs text-muted-foreground">Loading…</div>
          ) : hubs.length === 0 ? (
            <div className="p-4 text-xs text-muted-foreground">
              No hubs yet. A hub watches a topic while you&apos;re away.
            </div>
          ) : (
            hubs.map((h) => (
              <button
                key={h.topic}
                type="button"
                onClick={() => selectHub(h.topic)}
                className={`block w-full border-b px-4 py-3 text-left hover:bg-muted/60 ${
                  selected === h.topic && !creating ? 'bg-muted' : ''
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium">{h.topic}</span>
                  {h.paused && <Pause className="h-3 w-3 shrink-0 text-muted-foreground" />}
                </div>
                <div className="mt-0.5 truncate text-xs text-muted-foreground">
                  {h.brief_count} brief{h.brief_count === 1 ? '' : 's'}
                  {h.latest_brief_title ? ` · ${h.latest_brief_title}` : ''}
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Main: create form or hub view */}
      <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">
        {creating ? (
          <CreateHubForm
            onCancel={() => setCreating(false)}
            onCreated={async (topic) => {
              setCreating(false);
              await loadHubs();
              selectHub(topic);
            }}
          />
        ) : !selected ? (
          <EmptyState onCreate={() => setCreating(true)} />
        ) : viewLoading && !view ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : view ? (
          <div className="mx-auto max-w-3xl space-y-6 p-6">
            {/* Header */}
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-lg font-semibold">{view.topic}</h1>
                <p className="mt-1 text-xs text-muted-foreground">
                  {view.paused ? 'Paused' : 'Standing'} · last sweep {fmtWhen(view.last_run_at)} ·
                  next {view.paused ? '—' : fmtWhen(view.next_run_at)}
                </p>
              </div>
              <div className="flex items-center gap-2">
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
            </div>

            {view.prompt && (
              <p className="rounded-md border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                {view.prompt}
              </p>
            )}

            {/* Briefs shelf — the felt unit */}
            <section>
              <h2 className="mb-2 text-sm font-medium">Briefs</h2>
              {view.briefs.length === 0 ? (
                <p className="text-xs text-muted-foreground">
                  No briefs yet — the first lands after the next sweep with
                  something worth saying. An empty sweep is reported honestly,
                  never padded.
                </p>
              ) : (
                <ul className="divide-y rounded-md border">
                  {view.briefs.map((b) => (
                    <li key={b.path}>
                      <button
                        type="button"
                        onClick={() => openBrief(b.path)}
                        className="flex w-full items-baseline justify-between gap-3 px-3 py-2.5 text-left hover:bg-muted/60"
                      >
                        <span className="truncate text-sm">{b.title}</span>
                        <span className="shrink-0 text-xs text-muted-foreground">{b.date || ''}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            {/* Sources */}
            <section>
              <h2 className="mb-2 text-sm font-medium">Watching</h2>
              <ul className="space-y-1">
                {view.sources.map((s) => (
                  <li key={s.id} className="truncate text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">{s.id}</span> · {s.url}
                  </li>
                ))}
              </ul>
            </section>

            {/* Sweep health — straight off the ledger */}
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
          </div>
        ) : (
          <div className="p-6 text-sm text-muted-foreground">{error || 'Hub not found.'}</div>
        )}
      </main>
    </div>
  );
}

// ---------------------------------------------------------------------------

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <RadarIcon className="h-8 w-8 text-muted-foreground" />
      <div>
        <p className="text-sm font-medium">Nothing on the radar yet</p>
        <p className="mx-auto mt-1 max-w-sm text-xs text-muted-foreground">
          A hub watches a topic while you&apos;re away: declared sources swept on
          schedule, what changed distilled into a cited brief.
        </p>
      </div>
      <button
        type="button"
        onClick={onCreate}
        className="mt-2 flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
      >
        <Plus className="h-4 w-4" /> Put something on the radar
      </button>
    </div>
  );
}

function CreateHubForm({
  onCancel, onCreated,
}: {
  onCancel: () => void;
  onCreated: (topic: string) => void | Promise<void>;
}) {
  const [topic, setTopic] = useState('');
  const [urls, setUrls] = useState('');
  const [cron, setCron] = useState(CADENCES[0].cron);
  const [steer, setSteer] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = useCallback(async () => {
    setErr(null);
    const slug = topic.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
    const sources = urls
      .split('\n')
      .map((u) => u.trim())
      .filter((u) => /^https?:\/\//.test(u))
      .map((u) => {
        let id = 'source';
        try { id = new URL(u).hostname.replace(/^www\./, '').split('.')[0] || 'source'; } catch { /* keep default */ }
        return { id, url: u };
      });
    // Two sources from one host would collide on id — suffix deterministically.
    const seen = new Map<string, number>();
    for (const s of sources) {
      const n = (seen.get(s.id) || 0) + 1;
      seen.set(s.id, n);
      if (n > 1) s.id = `${s.id}-${n}`;
    }
    if (!slug) { setErr('Name the topic.'); return; }
    if (sources.length === 0) { setErr('Add at least one feed URL (RSS/Atom, one per line).'); return; }
    setBusy(true);
    try {
      await api.radar.create({
        topic: slug,
        sources,
        schedule: cron,
        prompt: steer.trim() || undefined,
      });
      await onCreated(slug);
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'create failed');
    } finally {
      setBusy(false);
    }
  }, [topic, urls, cron, steer, onCreated]);

  return (
    <div className="mx-auto max-w-xl space-y-4 p-6">
      <div>
        <h1 className="text-lg font-semibold">New hub</h1>
        <p className="mt-1 text-xs text-muted-foreground">
          The first sweep runs within about five minutes of creating the hub;
          after that, on the cadence you pick.
        </p>
      </div>

      <label className="block text-sm">
        <span className="mb-1 block font-medium">Topic</span>
        <input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="competitor-x"
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        />
      </label>

      <label className="block text-sm">
        <span className="mb-1 block font-medium">Feeds to watch</span>
        <textarea
          value={urls}
          onChange={(e) => setUrls(e.target.value)}
          placeholder={'https://example.com/feed\nhttps://blog.example.com/atom.xml'}
          rows={4}
          className="w-full rounded-md border bg-background px-3 py-2 font-mono text-xs"
        />
        <span className="mt-1 block text-xs text-muted-foreground">
          RSS or Atom URLs, one per line (up to 12).
        </span>
      </label>

      <label className="block text-sm">
        <span className="mb-1 block font-medium">Cadence</span>
        <select
          value={cron}
          onChange={(e) => setCron(e.target.value)}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        >
          {CADENCES.map((c) => (
            <option key={c.cron} value={c.cron}>{c.label}</option>
          ))}
        </select>
      </label>

      <label className="block text-sm">
        <span className="mb-1 block font-medium">What matters (optional)</span>
        <textarea
          value={steer}
          onChange={(e) => setSteer(e.target.value)}
          placeholder="What should the brief focus on — and what should it skip?"
          rows={3}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm"
        />
      </label>

      {err && <p className="text-xs text-red-600">{err}</p>}

      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void submit()}
          className="flex items-center gap-1.5 rounded-md border bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-50"
        >
          {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />} Create hub
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
