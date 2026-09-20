'use client';

/**
 * StandingDetail — one piece of standing work, opened (ADR-658 D6).
 *
 * The cockpit's row-to-detail: what a member sees when they open a piece of
 * standing work to configure and manage it. Bounded to the declaration's OWN
 * facts — which file it keeps, who looks after it (derived), when it runs,
 * where its updates come from, its instructions, and its runs from the ledger.
 * ADR-639 D4 deleted the strings pane's parties/consumers/head-facts chrome;
 * this is not that.
 *
 * The verbs act on the DECLARATION, never on a being: Run now · Pause/Resume ·
 * change the schedule (the composer's own field, refused by name when it
 * would break the work) · edit the instructions (as the FILE they are, through
 * the ordinary file door — never a second one) · Retire (the declaration goes
 * to Trash; the kept file and its instructions stay, with their history).
 */

import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, CalendarClock, FolderOpen, Loader2, Pause, Play, Trash2, Zap } from 'lucide-react';
import { api, type StandingDetailData, type StandingRun } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { Working } from '@/components/shared/Working';
import { PROBLEM_COPY, describeSchedule, lowerFirst, minderLine, scheduleLine } from '@/components/standing/StandingRow';
import { useFeedback } from '@/contexts/FeedbackContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { formatLedgerTime } from '@/lib/formatting';

function runLine(r: StandingRun): string {
  const what = r.step === 'write' ? 'Update' : 'Read sources';
  if (r.status === 'success') return `${what} — done`;
  if (r.status === 'skipped' && r.error_reason === 'no_change') return `${what} — nothing changed`;
  if (r.status === 'skipped' && r.error_reason === 'sources_unchanged') return `${what} — not needed, nothing new to read`;
  if (r.status === 'skipped') return `${what} — skipped${r.error_reason ? ` (${r.error_reason})` : ''}`;
  if (r.error_reason === 'shape_violation') return `${what} — refused, the data didn’t fit the file’s shape`;
  if (r.error_reason === 'no_sources_fetched') return `${what} — no source could be read`;
  if (r.error_reason === 'balance_exhausted') return `${what} — did not run, the balance is used up`;
  if (r.error_reason === 'output_truncated') return `${what} — refused, the file has grown too long to keep current in one run`;
  return `${what} — failed${r.error_reason ? ` (${r.error_reason})` : ''}`;
}

const PRESETS: Array<{ label: string; cron: string }> = [
  { label: 'Every weekday at 09:00', cron: '0 9 * * 1-5' },
  { label: 'Every day at 09:00', cron: '0 9 * * *' },
  { label: 'Every Monday at 09:00', cron: '0 9 * * 1' },
  { label: 'Every hour', cron: '0 * * * *' },
];

export function StandingDetail({
  topic, onBack, onChanged,
}: {
  topic: string;
  onBack: () => void;
  onChanged: () => void;
}) {
  const { runAction } = useFeedback();
  const { navigateToSurface } = useSurfacePreferences();
  const [detail, setDetail] = useState<StandingDetailData | null>(null);
  const [missing, setMissing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [editingSchedule, setEditingSchedule] = useState(false);
  const [cron, setCron] = useState('');
  const [editingText, setEditingText] = useState(false);
  const [text, setText] = useState('');
  const [confirmRetire, setConfirmRetire] = useState(false);

  const load = useCallback(async () => {
    try {
      const d = await api.standing.get(topic);
      setDetail(d);
      setMissing(false);
    } catch {
      setMissing(true);
    }
  }, [topic]);

  useEffect(() => { void load(); }, [load]);

  if (missing) {
    return (
      <div className="flex-1 px-5 py-4">
        <button type="button" onClick={onBack} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3.5 w-3.5" /> All standing work
        </button>
        <div className="mt-4 rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
          This standing work is no longer here. It may have been retired.
        </div>
      </div>
    );
  }
  if (!detail) return <Working label="Loading…" fill />;

  const s = detail.summary;
  const kept = s.target_path ?? `/workspace/${s.topic}/${s.target}`;
  const minder = minderLine(s);
  const currentCron = Array.isArray(s.schedule) ? s.schedule[0] ?? '' : String(s.schedule ?? '');

  const runNow = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const res = await runAction(() => api.standing.run(s.topic), { pending: `Running ${s.topic}…` });
      setNote(res.no_change ? 'Ran — nothing changed.' : res.success ? 'Ran — the file was updated.' : `Run failed (${res.error_reason ?? 'unknown'}).`);
    } catch (e) {
      setNote(`Run failed (${e instanceof Error ? e.message : String(e)}).`);
    } finally {
      setBusy(false);
      void load();
      onChanged();
    }
  };

  const togglePause = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await runAction(() => api.standing.update(s.topic, { paused: !s.paused }), {
        success: s.paused ? 'Resumed' : 'Paused',
        error: s.paused ? 'Could not resume this' : 'Could not pause this',
      });
    } catch {
      /* reported; the reload restores the true state */
    } finally {
      setBusy(false);
      void load();
      onChanged();
    }
  };

  const saveSchedule = async () => {
    const next = cron.trim();
    if (!next || busy) return;
    setBusy(true);
    try {
      await runAction(() => api.standing.update(s.topic, { schedule: next }), {
        success: `Now ${describeSchedule(next)}`,
        error: 'Could not change the schedule',
      });
      setEditingSchedule(false);
    } catch {
      /* reported */
    } finally {
      setBusy(false);
      void load();
      onChanged();
    }
  };

  const saveText = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await runAction(
        () => api.workspace.editFile(detail.contract_path, text, undefined, `edit the instructions for ${s.topic}`),
        { success: 'Instructions saved', error: 'Could not save the instructions' },
      );
      setEditingText(false);
    } catch {
      /* reported */
    } finally {
      setBusy(false);
      void load();
    }
  };

  const retire = async () => {
    if (busy) return;
    setBusy(true);
    try {
      await runAction(() => api.standing.retire(s.topic), {
        success: `${s.target} is no longer kept current. The file stays.`,
        error: 'Could not retire this',
      });
      onChanged();
      onBack();
    } catch {
      setBusy(false);
      setConfirmRetire(false);
    }
  };

  return (
    <div className="flex-1 space-y-5 px-5 py-4">
      <button type="button" onClick={onBack} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> All standing work
      </button>

      <section className="rounded-lg border border-border/70 bg-background p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <button
              type="button"
              onClick={() => navigateToSurface('files', { path: kept })}
              className="flex items-center gap-1.5 text-[15px] font-semibold text-foreground hover:underline"
              title="Open in Files"
            >
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
              <span className="truncate">{s.target || '(no file named)'}</span>
            </button>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {s.topic}{minder ? ` · ${minder}` : ''}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => void runNow()}
              disabled={busy || s.problem != null}
              title={s.problem != null ? 'It can’t run until its instructions are fixed' : 'Update the file now'}
              className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
            >
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />} Run now
            </button>
            <button
              type="button"
              onClick={() => void togglePause()}
              disabled={busy}
              className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
            >
              {s.paused ? (<><Play className="h-3.5 w-3.5" /> Resume</>) : (<><Pause className="h-3.5 w-3.5" /> Pause</>)}
            </button>
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-2 text-xs sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">When</dt>
            <dd className="mt-0.5 text-foreground">
              {editingSchedule ? (
                <span className="flex flex-wrap items-center gap-2">
                  <select
                    value={PRESETS.some((p) => p.cron === cron) ? cron : 'custom'}
                    onChange={(e) => setCron(e.target.value === 'custom' ? currentCron : e.target.value)}
                    className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                  >
                    {PRESETS.map((p) => <option key={p.cron} value={p.cron}>{p.label}</option>)}
                    <option value="custom">Custom…</option>
                  </select>
                  {!PRESETS.some((p) => p.cron === cron) && (
                    <input
                      value={cron}
                      onChange={(e) => setCron(e.target.value)}
                      className="w-32 rounded-md border border-border bg-background px-2 py-1 font-mono text-xs"
                    />
                  )}
                  <button type="button" onClick={() => void saveSchedule()} disabled={busy} className="rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-40">Save</button>
                  <button type="button" onClick={() => setEditingSchedule(false)} className="text-xs text-muted-foreground hover:text-foreground">Cancel</button>
                </span>
              ) : (
                <span className="inline-flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1"><CalendarClock className="h-3 w-3" /> {scheduleLine(s.schedule, s.timezone)}</span>
                  {s.paused && <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium text-foreground/70">Paused</span>}
                  <button type="button" onClick={() => { setCron(currentCron); setEditingSchedule(true); }} className="text-[11px] text-muted-foreground underline hover:text-foreground">Change</button>
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Next</dt>
            <dd className="mt-0.5 text-foreground">{s.paused ? 'Paused' : s.next_run_at ? formatLedgerTime(s.next_run_at) : 'Soon'}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-muted-foreground">Where its updates come from</dt>
            <dd className="mt-0.5 text-foreground">
              {s.sources.length === 0 ? 'No sources named.' : (
                <ul className="space-y-0.5">
                  {s.sources.map((src) => (
                    <li key={src.id} className="truncate">
                      {src.connector
                        ? <><span className="font-medium">{src.connector}</span>{src.selector ? ` · ${src.selector}` : ''}{src.reads ? <span className="text-muted-foreground"> — reads {lowerFirst(src.reads)}</span> : null}</>
                        : src.path
                          ? <><span className="font-mono">{src.path}</span><span className="text-muted-foreground"> — {src.path.endsWith('/') ? 'a folder in this workspace, newest files first' : 'a file in this workspace'}</span></>
                          : <span className="font-mono">{src.url}</span>}
                    </li>
                  ))}
                </ul>
              )}
            </dd>
          </div>
        </dl>

        {s.problem != null && (
          <p className="mt-3 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            {PROBLEM_COPY[s.problem] ?? `Cannot run: ${s.problem}`}
          </p>
        )}
        {note && <p className="mt-3 text-xs text-foreground">{note}</p>}
      </section>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-[13px] font-medium text-foreground/80">Instructions</h3>
          {!editingText && (
            <button
              type="button"
              onClick={() => { setText(detail.contract ?? ''); setEditingText(true); }}
              className="text-[11px] text-muted-foreground underline hover:text-foreground"
            >
              Edit
            </button>
          )}
        </div>
        {editingText ? (
          <div className="space-y-2">
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              className="w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus:border-foreground/30"
            />
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setEditingText(false)} className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40">Cancel</button>
              <button type="button" onClick={() => void saveText()} disabled={busy || !text.trim()} className="rounded-md bg-foreground px-3 py-1.5 text-xs text-background disabled:opacity-50">Save</button>
            </div>
          </div>
        ) : detail.contract ? (
          <div className="rounded-md border border-border/60 px-4 py-3">
            <MarkdownRenderer content={detail.contract} />
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            No instructions yet. Write what the file must stay true to.
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h3 className="text-[13px] font-medium text-foreground/80">Runs</h3>
        {detail.runs.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            Nothing has run yet. The first run starts within a few minutes.
          </div>
        ) : (
          <ul className="rounded-md border border-border/60">
            {detail.runs.map((r, i) => (
              <li key={`${r.at}-${i}`} className="flex items-center justify-between gap-3 border-b border-border/60 px-3 py-2 text-xs last:border-b-0">
                <span className="min-w-0 text-foreground">
                  {runLine(r)}
                  {/* ADR-659 D2 — what this update was MADE FROM, read off the
                      kept file's own revision. The ledger row alone could only
                      say that a run happened, never what it produced. */}
                  {r.derived_from && r.derived_from.length > 0 && (
                    <span className="block truncate text-muted-foreground">
                      from {r.derived_from.slice(0, 3).map((p) => p.replace(/^\/workspace\//, '')).join(', ')}
                      {r.derived_from.length > 3 ? ` and ${r.derived_from.length - 3} more` : ''}
                    </span>
                  )}
                </span>
                <span className="shrink-0 text-muted-foreground">{r.at ? formatLedgerTime(r.at) : ''}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-md border border-border/60 px-4 py-3">
        {confirmRetire ? (
          <div className="space-y-2">
            <p className="text-sm text-foreground">Stop keeping {s.target} current?</p>
            <p className="text-xs text-muted-foreground">The file and its history stay. Only the schedule and its instructions are retired, and you can set them up again.</p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setConfirmRetire(false)} disabled={busy} className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40">Keep it running</button>
              <button type="button" onClick={() => void retire()} disabled={busy} className="inline-flex items-center gap-1.5 rounded-md border border-destructive/40 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/5 disabled:opacity-50">
                {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />} Retire
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">Retiring stops the updates. The file stays.</p>
            <button type="button" onClick={() => setConfirmRetire(true)} className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground">
              <Trash2 className="h-3 w-3" /> Retire
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
