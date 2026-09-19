'use client';

/**
 * NewStandingWorkModal — the door (ADR-658 D4), opened from a pre-shaped start
 * (D7) or from scratch.
 *
 * A member names a piece of standing work in their own words: where it lives
 * (a folder — new or picked with the ONE tree picker), which file it keeps
 * (one plain name, md · csv · json · txt), when it runs (a schedule in the
 * workspace's clock), where its updates come from (a connection they already
 * hold, or a web page), and what the file must stay true to (the
 * instructions — the load-bearing half, refused when blank).
 *
 * ⚠️ THE DOOR COMPOSES NOTHING ITSELF. It posts the fields; the server's ONE
 * composer writes the YAML, the ONE parser checks it, and a refusal comes back
 * BY NAME (`detail.problem` + `detail.message`) so the member reads which rule
 * refused, never "invalid". Designation stays explicit (ADR-569 D1): the
 * member names the file; nothing here infers one.
 *
 * The connector list is what the server DERIVED from reach (the starts) —
 * never a hand-typed catalogue. A connector with no capture binding is not
 * offered, because the kernel could not read it.
 */

import { useEffect, useMemo, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { APIError, api, type StandingStart, type StandingSummary } from '@/lib/api/client';
import { WorkspacePickerModal } from '@/components/workspace/WorkspacePicker';
import { describeSchedule, lowerFirst } from '@/components/standing/StandingRow';

const FORMATS = ['md', 'csv', 'json', 'txt'];

/** The schedules a member sets from the door — each one a cron the kernel
 *  reads in the workspace's clock. "Custom" takes any cron. */
const PRESETS: Array<{ label: string; cron: string }> = [
  { label: 'Every weekday at 09:00', cron: '0 9 * * 1-5' },
  { label: 'Every day at 09:00', cron: '0 9 * * *' },
  { label: 'Every Monday at 09:00', cron: '0 9 * * 1' },
  { label: 'Every hour', cron: '0 * * * *' },
];

function slugify(s: string): string {
  return s.trim().toLowerCase().replace(/[^a-z0-9/]+/g, '-').replace(/^-|-$/g, '').replace(/\/+/g, '/');
}

function refusalMessage(e: unknown): string {
  if (e instanceof APIError) {
    const detail = (e.data as { detail?: unknown } | undefined)?.detail;
    if (detail && typeof detail === 'object' && 'message' in detail) {
      const m = (detail as { message?: unknown }).message;
      if (typeof m === 'string' && m) return m;
    }
  }
  return e instanceof Error ? e.message : 'Could not set this up.';
}

export function NewStandingWorkModal({
  open, start, starts, timezone, onClose, onCreated,
}: {
  open: boolean;
  start: StandingStart | null;
  starts: StandingStart[];
  timezone?: string | null;
  onClose: () => void;
  onCreated: (created: StandingSummary) => void;
}) {
  const connectorStarts = useMemo(() => starts.filter((s) => s.kind === 'connector'), [starts]);
  const [folder, setFolder] = useState('');
  const [target, setTarget] = useState('');
  const [preset, setPreset] = useState<string>(PRESETS[0].cron);
  const [customCron, setCustomCron] = useState('');
  const [sourceKind, setSourceKind] = useState<'connector' | 'url'>('url');
  const [connector, setConnector] = useState<string>('');
  const [selector, setSelector] = useState<string>('');
  const [url, setUrl] = useState('');
  const [contract, setContract] = useState('');
  const [pickingFolder, setPickingFolder] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Re-open lands on the chosen start (pre-filled) or a blank door.
  useEffect(() => {
    if (!open) return;
    setError(null);
    setBusy(false);
    const s = start;
    setFolder(s?.suggested_folder ?? '');
    setTarget(s?.suggested_target ?? 'brief.md');
    const cron = s?.suggested_schedule ?? PRESETS[0].cron;
    if (PRESETS.some((p) => p.cron === cron)) {
      setPreset(cron);
      setCustomCron('');
    } else {
      setPreset('custom');
      setCustomCron(cron);
    }
    if (s?.kind === 'connector' && s.connector) {
      setSourceKind('connector');
      setConnector(s.connector);
      setSelector(s.selectors[0] ?? '');
    } else {
      const first = connectorStarts[0];
      setSourceKind(first && !s ? 'connector' : 'url');
      setConnector(first?.connector ?? '');
      setSelector(first?.selectors[0] ?? '');
    }
    setUrl('');
    setContract(s?.contract_seed ?? '');
  }, [open, start, connectorStarts]);

  if (!open) return null;

  const chosenStart = connectorStarts.find((s) => s.connector === connector) ?? null;
  const schedule = preset === 'custom' ? customCron.trim() : preset;
  const ext = target.includes('.') ? target.split('.').pop()!.toLowerCase() : '';
  const formatOk = FORMATS.includes(ext);
  const folderSlug = slugify(folder);
  const sourceOk = sourceKind === 'url' ? /^https?:\/\//.test(url.trim()) : Boolean(connector && selector);
  const canCreate = Boolean(folderSlug && target.trim() && formatOk && schedule && sourceOk && contract.trim()) && !busy;

  const create = async () => {
    if (!canCreate) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.standing.create({
        folder: folderSlug,
        target: target.trim(),
        schedule,
        contract: contract.trim(),
        sources: sourceKind === 'url'
          ? [{ id: 'page', url: url.trim() }]
          : [{ id: slugify(selector) || 'source', connector, selector }],
      });
      onCreated(created);
    } catch (e) {
      setError(refusalMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const tzLabel = timezone && timezone !== 'UTC' ? ` (${timezone})` : '';

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
        <div className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-lg border border-border bg-background shadow-lg">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-base font-semibold">New standing work</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              One file, kept current on a schedule. The first run starts within a few minutes.
            </p>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
            <div>
              <label className="block text-xs font-medium text-muted-foreground">Where</label>
              <div className="mt-1 flex items-center gap-2">
                <input
                  value={folder}
                  onChange={(e) => setFolder(e.target.value)}
                  placeholder="team-brief"
                  className="min-w-0 flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                />
                <button
                  type="button"
                  onClick={() => setPickingFolder(true)}
                  className="shrink-0 rounded-md border border-border px-2.5 py-2 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                >
                  Choose…
                </button>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">
                A folder of its own. New or existing, one piece of standing work per folder.
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground">The file it keeps</label>
              <input
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="brief.md"
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
              />
              <p className="mt-1 text-[11px] text-muted-foreground">
                {target && !formatOk
                  ? 'Only md, csv, json and txt files can be kept current.'
                  : `Lives at ${folderSlug || '…'}/${target || '…'}. Made on the first run if it does not exist yet.`}
              </p>
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground">When{tzLabel}</label>
              <select
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
                className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
              >
                {PRESETS.map((p) => (
                  <option key={p.cron} value={p.cron}>{p.label}</option>
                ))}
                <option value="custom">Custom…</option>
              </select>
              {preset === 'custom' && (
                <input
                  value={customCron}
                  onChange={(e) => setCustomCron(e.target.value)}
                  placeholder="0 13 * * *"
                  className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 font-mono text-sm outline-none focus:border-foreground/30"
                />
              )}
              {preset === 'custom' && customCron.trim() && (
                <p className="mt-1 text-[11px] text-muted-foreground">{describeSchedule(customCron)}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground">Where its updates come from</label>
              <div className="mt-1 flex gap-2">
                {connectorStarts.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setSourceKind('connector')}
                    className={`rounded-md border px-2.5 py-1.5 text-xs ${sourceKind === 'connector' ? 'border-foreground/40 bg-muted/40 text-foreground' : 'border-border text-muted-foreground hover:bg-muted/40'}`}
                  >
                    A connection
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setSourceKind('url')}
                  className={`rounded-md border px-2.5 py-1.5 text-xs ${sourceKind === 'url' ? 'border-foreground/40 bg-muted/40 text-foreground' : 'border-border text-muted-foreground hover:bg-muted/40'}`}
                >
                  A web page
                </button>
              </div>
              {sourceKind === 'connector' ? (
                <div className="mt-2 space-y-2">
                  <select
                    value={connector}
                    onChange={(e) => {
                      const next = connectorStarts.find((s) => s.connector === e.target.value);
                      setConnector(e.target.value);
                      setSelector(next?.selectors[0] ?? '');
                    }}
                    className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                  >
                    {connectorStarts.map((s) => (
                      <option key={s.connector ?? ''} value={s.connector ?? ''}>{s.name}</option>
                    ))}
                  </select>
                  {chosenStart && chosenStart.selectors.length > 0 ? (
                    <select
                      value={selector}
                      onChange={(e) => setSelector(e.target.value)}
                      className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                    >
                      {chosenStart.selectors.map((id) => (
                        <option key={id} value={id}>{id}</option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-[11px] text-amber-700 dark:text-amber-300">
                      Nothing is chosen on this connection yet. Choose what it reads in Reach first.
                    </p>
                  )}
                  {chosenStart?.reads && (
                    <p className="text-[11px] text-muted-foreground">It reads {lowerFirst(chosenStart.reads)}.</p>
                  )}
                </div>
              ) : (
                <input
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://…"
                  className="mt-2 w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
                />
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-muted-foreground">Instructions</label>
              <textarea
                value={contract}
                onChange={(e) => setContract(e.target.value)}
                rows={5}
                placeholder="What this file is, and what it must stay true to."
                className="mt-1 w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
              />
              <p className="mt-1 text-[11px] text-muted-foreground">
                Saved next to the file. Every run follows it, and you can change it any time.
              </p>
            </div>

            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>

          <div className="flex justify-end gap-2 border-t border-border px-5 py-3">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-muted/40 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void create()}
              disabled={!canCreate}
              className="inline-flex items-center gap-1.5 rounded-md bg-foreground px-3 py-1.5 text-sm text-background disabled:opacity-50"
            >
              {busy && <Loader2 className="h-3 w-3 animate-spin" />}
              Start
            </button>
          </div>
        </div>
      </div>

      <WorkspacePickerModal
        open={pickingFolder}
        mode="folder"
        title="Choose a folder"
        subtitle="Where this standing work lives"
        confirmLabel="Choose"
        emptyMessage="No folders yet."
        selectable={(node) => node.type === 'folder'}
        onClose={() => setPickingFolder(false)}
        onConfirm={(path) => {
          setFolder(path.replace(/^\/workspace\//, '').replace(/^\/+|\/+$/g, ''));
          setPickingFolder(false);
        }}
      />
    </>
  );
}
