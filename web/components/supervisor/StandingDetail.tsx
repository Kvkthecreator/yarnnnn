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
import { useTranslations } from 'next-intl';
import { ArrowLeft, CalendarClock, FolderOpen, Loader2, Pause, Play, Trash2, Zap } from 'lucide-react';
import {
  api,
  type StandingDetailData,
  type StandingRun,
  type StandingSource,
  type StandingStart,
} from '@/lib/api/client';
import { AddSource, MAX_SOURCES_PROSE, SourceRow, isStructured } from '@/components/supervisor/SourceList';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { Working } from '@/components/shared/Working';
import { useStandingWords } from '@/components/standing/StandingRow';
import { useFeedback } from '@/contexts/FeedbackContext';
import { useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { formatLedgerTime } from '@/lib/formatting';

/** ADR-660 — the presets hold catalog KEYS, not words: this table is evaluated
 *  at import, before any member's language is known. */
const PRESETS: Array<{ labelKey: string; cron: string }> = [
  { labelKey: 'preset.weekdays9', cron: '0 9 * * 1-5' },
  { labelKey: 'preset.daily9', cron: '0 9 * * *' },
  { labelKey: 'preset.monday9', cron: '0 9 * * 1' },
  { labelKey: 'preset.hourly', cron: '0 * * * *' },
];

/** One run's line, worded. The whole sentence is one ICU message so the
 *  step and its outcome are not joined in English word order. */
function useRunLine() {
  const t = useTranslations('supervisor.runLine');
  return (r: StandingRun): string => {
    const what = r.step === 'write' ? t('write') : t('read');
    if (r.status === 'success') return t('done', { what });
    if (r.status === 'skipped' && r.error_reason === 'no_change') return t('noChange', { what });
    if (r.status === 'skipped' && r.error_reason === 'sources_unchanged') return t('sourcesUnchanged', { what });
    if (r.status === 'skipped') {
      return r.error_reason ? t('skippedWithReason', { what, reason: r.error_reason }) : t('skipped', { what });
    }
    if (r.error_reason === 'shape_violation') return t('shapeViolation', { what });
    if (r.error_reason === 'no_sources_fetched') return t('noSourcesFetched', { what });
    if (r.error_reason === 'balance_exhausted') return t('balanceExhausted', { what });
    if (r.error_reason === 'output_truncated') return t('outputTruncated', { what });
    return r.error_reason ? t('failedWithReason', { what, reason: r.error_reason }) : t('failed', { what });
  };
}

export function StandingDetail({
  topic, onBack, onChanged,
}: {
  topic: string;
  onBack: () => void;
  onChanged: () => void;
}) {
  const t = useTranslations('supervisor');
  const { runAction } = useFeedback();
  const { navigateToSurface } = useSurfacePreferences();
  const { problemCopy, describeSchedule, minderLine, scheduleLine } = useStandingWords();
  const runLine = useRunLine();
  const [detail, setDetail] = useState<StandingDetailData | null>(null);
  const [missing, setMissing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [editingSchedule, setEditingSchedule] = useState(false);
  const [cron, setCron] = useState('');
  const [editingText, setEditingText] = useState(false);
  const [text, setText] = useState('');
  const [confirmRetire, setConfirmRetire] = useState(false);
  // am.5 — the sources, editable. `starts` and `folders` are what the ADD
  // control offers; both degrade to empty rather than blocking the pane.
  const [editingSources, setEditingSources] = useState(false);
  const [draft, setDraft] = useState<StandingSource[]>([]);
  const [starts, setStarts] = useState<StandingStart[]>([]);
  const [folders, setFolders] = useState<Array<{ path: string; label: string }>>([]);

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

  // Read independently of the detail itself: an unreadable roster leaves the
  // sources editable by path or page, never a broken pane.
  useEffect(() => {
    let live = true;
    api.standing.starts().then(
      (st) => { if (live) setStarts(Array.isArray(st) ? st : []); },
      () => { if (live) setStarts([]); },
    );
    api.workspace.getRoots().then(
      (roots) => {
        if (!live) return;
        setFolders(
          roots
            .filter((r) => r.exists && r.name !== 'system' && r.name !== 'agents')
            .map((r) => ({ path: `${r.name}/`, label: r.display_name || r.name })),
        );
      },
      () => { if (live) setFolders([]); },
    );
    return () => { live = false; };
  }, []);

  if (missing) {
    return (
      <div className="flex-1 px-5 py-4">
        <button type="button" onClick={onBack} className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3.5 w-3.5" /> {t('detail.back')}
        </button>
        <div className="mt-4 rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
          {t('detail.gone')}
        </div>
      </div>
    );
  }
  if (!detail) return <Working label={t('detail.loading')} fill />;

  const s = detail.summary;
  const kept = s.target_path ?? `/workspace/${s.topic}/${s.target}`;
  const minder = minderLine(s);
  const currentCron = Array.isArray(s.schedule) ? s.schedule[0] ?? '' : String(s.schedule ?? '');
  // The server's rule, mirrored (`_classify_sources`): a structured target maps
  // exactly ONE source to the leaf; prose takes up to 12.
  const maxSources = isStructured(s.format ?? '') ? 1 : MAX_SOURCES_PROSE;

  // Worded here rather than inline: a multi-line ternary inside JSX reads to
  // the ADR-660 meter as literal copy even when every branch is a `t()` call.
  const nextLine = s.problem != null
    ? t('detail.blocked')
    : s.paused
      ? t('detail.paused')
      : s.next_run_at
        ? formatLedgerTime(s.next_run_at)
        : t('detail.soon');

  const runNow = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const res = await runAction(() => api.standing.run(s.topic), { pending: t('action.runningPending', { topic: s.topic }) });
      setNote(
        res.no_change
          ? t('action.ranNoChange')
          : res.success
            ? t('action.ranUpdated')
            : t('action.runFailed', { reason: res.error_reason ?? t('action.runFailedUnknown') }),
      );
    } catch (e) {
      setNote(t('action.runFailed', { reason: e instanceof Error ? e.message : String(e) }));
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
        success: s.paused ? t('action.resumed') : t('action.paused'),
        error: s.paused ? t('action.couldNotResume') : t('action.couldNotPause'),
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
        success: t('detail.scheduleChanged', { cadence: describeSchedule(next) }),
        error: t('detail.couldNotChangeSchedule'),
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

  const saveSources = async () => {
    if (busy || draft.length === 0) return;
    setBusy(true);
    try {
      await runAction(
        () => api.standing.update(s.topic, {
          sources: draft.map((x) => ({
            id: x.id,
            ...(x.connector ? { connector: x.connector, selector: x.selector ?? undefined } : {}),
            ...(x.path ? { path: x.path } : {}),
            ...(x.url ? { url: x.url } : {}),
          })),
        }),
        { success: t('detail.sourcesChanged'), error: t('detail.couldNotChangeSources') },
      );
      setEditingSources(false);
    } catch {
      /* reported by name; the reload restores the true state */
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
        () => api.workspace.editFile(detail.contract_path, text, undefined, t('detail.editMessage', { topic: s.topic })),
        { success: t('detail.instructionsSaved'), error: t('detail.couldNotSaveInstructions') },
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
        success: t('detail.retired', { target: s.target }),
        error: t('detail.couldNotRetire'),
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
        <ArrowLeft className="h-3.5 w-3.5" /> {t('detail.back')}
      </button>

      <section className="rounded-lg border border-border/70 bg-background p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <button
              type="button"
              onClick={() => navigateToSurface('files', { path: kept })}
              className="flex items-center gap-1.5 text-[15px] font-semibold text-foreground hover:underline"
              title={t('detail.openInFiles')}
            >
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
              <span className="truncate">{s.target || t('detail.noFileNamed')}</span>
            </button>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {minder ? t('row.withTopic', { topic: s.topic, minder }) : s.topic}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => void runNow()}
              disabled={busy || s.problem != null}
              title={s.problem != null ? t('row.blockedTitle') : t('row.runNowTitle')}
              className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
            >
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />} {t('detail.runNow')}
            </button>
            <button
              type="button"
              onClick={() => void togglePause()}
              disabled={busy}
              className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
            >
              {s.paused ? (<><Play className="h-3.5 w-3.5" /> {t('detail.resume')}</>) : (<><Pause className="h-3.5 w-3.5" /> {t('detail.pause')}</>)}
            </button>
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-1 gap-x-6 gap-y-2 text-xs sm:grid-cols-2">
          <div>
            <dt className="text-muted-foreground">{t('detail.when')}</dt>
            <dd className="mt-0.5 text-foreground">
              {editingSchedule ? (
                <span className="flex flex-wrap items-center gap-2">
                  <select
                    value={PRESETS.some((p) => p.cron === cron) ? cron : 'custom'}
                    onChange={(e) => setCron(e.target.value === 'custom' ? currentCron : e.target.value)}
                    className="rounded-md border border-border bg-background px-2 py-1 text-xs"
                  >
                    {PRESETS.map((p) => <option key={p.cron} value={p.cron}>{t(p.labelKey)}</option>)}
                    <option value="custom">{t('detail.custom')}</option>
                  </select>
                  {!PRESETS.some((p) => p.cron === cron) && (
                    <input
                      value={cron}
                      onChange={(e) => setCron(e.target.value)}
                      className="w-32 rounded-md border border-border bg-background px-2 py-1 font-mono text-xs"
                    />
                  )}
                  <button type="button" onClick={() => void saveSchedule()} disabled={busy} className="rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-40">{t('detail.save')}</button>
                  <button type="button" onClick={() => setEditingSchedule(false)} className="text-xs text-muted-foreground hover:text-foreground">{t('detail.cancel')}</button>
                </span>
              ) : (
                <span className="inline-flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1"><CalendarClock className="h-3 w-3" /> {scheduleLine(s.schedule, s.timezone)}</span>
                  {s.paused && <span className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium text-foreground/70">{t('detail.paused')}</span>}
                  <button type="button" onClick={() => { setCron(currentCron); setEditingSchedule(true); }} className="text-[11px] text-muted-foreground underline hover:text-foreground">{t('detail.change')}</button>
                </span>
              )}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">{t('detail.next')}</dt>
            {/* ⚠️ Same false promise the row carried: a declaration with a
                problem will NOT run at its next scheduled time, so the field
                says what is true instead of a time to plan around. */}
            <dd className="mt-0.5 text-foreground">{nextLine}</dd>
          </div>
          <div className="sm:col-span-2">
            <div className="flex items-baseline justify-between gap-3">
              <dt className="text-muted-foreground">{t('detail.sourcesLabel')}</dt>
              {!editingSources && (
                <button
                  type="button"
                  onClick={() => { setDraft(s.sources); setEditingSources(true); }}
                  className="text-[11px] text-muted-foreground underline hover:text-foreground"
                >
                  {t('detail.change')}
                </button>
              )}
            </div>
            <dd className="mt-1 text-foreground">
              {/* ⭐ EDITABLE (am.5). The sources were rendered read-only, so a
                  member who mis-picked one channel — or wanted a second one —
                  had no repair short of retiring the work and building it
                  again. `sources` has always been PATCHable and the server
                  refuses an invalid set BY NAME. */}
              {editingSources ? (
                <div className="space-y-2">
                  {draft.length > 0 && (
                    <ul className="space-y-1.5">
                      {draft.map((src) => (
                        <SourceRow
                          key={src.id}
                          source={src}
                          starts={starts}
                          onRemove={() => setDraft((xs) => xs.filter((x) => x.id !== src.id))}
                        />
                      ))}
                    </ul>
                  )}
                  <AddSource
                    starts={starts}
                    existing={draft}
                    folders={folders}
                    disabled={draft.length >= maxSources}
                    onAdd={(x) => setDraft((xs) => [...xs, x])}
                  />
                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={() => setEditingSources(false)} className="rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground">{t('detail.cancel')}</button>
                    <button
                      type="button"
                      onClick={() => void saveSources()}
                      disabled={busy || draft.length === 0 || draft.length > maxSources}
                      className="rounded-md bg-foreground px-2.5 py-1 text-xs text-background disabled:opacity-40"
                    >
                      {t('detail.save')}
                    </button>
                  </div>
                </div>
              ) : s.sources.length === 0 ? (
                t('detail.noSources')
              ) : (
                <ul className="space-y-1.5">
                  {s.sources.map((src) => (
                    <SourceRow key={src.id} source={src} starts={starts} />
                  ))}
                </ul>
              )}
            </dd>
          </div>
        </dl>

        {s.problem != null && (
          <p className="mt-3 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            {problemCopy(s.problem)}
          </p>
        )}
        {note && <p className="mt-3 text-xs text-foreground">{note}</p>}
      </section>

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-[13px] font-medium text-foreground/80">{t('detail.instructions')}</h3>
          {!editingText && (
            <button
              type="button"
              onClick={() => { setText(detail.contract ?? ''); setEditingText(true); }}
              className="text-[11px] text-muted-foreground underline hover:text-foreground"
            >
              {t('detail.edit')}
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
              <button type="button" onClick={() => setEditingText(false)} className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40">{t('detail.cancel')}</button>
              <button type="button" onClick={() => void saveText()} disabled={busy || !text.trim()} className="rounded-md bg-foreground px-3 py-1.5 text-xs text-background disabled:opacity-50">{t('detail.save')}</button>
            </div>
          </div>
        ) : detail.contract ? (
          <div className="rounded-md border border-border/60 px-4 py-3">
            <MarkdownRenderer content={detail.contract} />
          </div>
        ) : (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            {t('detail.instructionsEmpty')}
          </div>
        )}
      </section>

      <section className="space-y-2">
        <h3 className="text-[13px] font-medium text-foreground/80">{t('detail.runs')}</h3>
        {detail.runs.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            {t('detail.runsEmpty')}
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
                      {r.derived_from.length > 3
                        ? t('detail.derivedFromMore', {
                            paths: r.derived_from.slice(0, 3).map((p) => p.replace(/^\/workspace\//, '')).join(', '),
                            count: r.derived_from.length - 3,
                          })
                        : t('detail.derivedFrom', {
                            paths: r.derived_from.map((p) => p.replace(/^\/workspace\//, '')).join(', '),
                          })}
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
            <p className="text-sm text-foreground">{t('detail.retireConfirmTitle', { target: s.target })}</p>
            <p className="text-xs text-muted-foreground">{t('detail.retireConfirmBody')}</p>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setConfirmRetire(false)} disabled={busy} className="rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:bg-muted/40">{t('detail.keepRunning')}</button>
              <button type="button" onClick={() => void retire()} disabled={busy} className="inline-flex items-center gap-1.5 rounded-md border border-destructive/40 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/5 disabled:opacity-50">
                {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />} {t('detail.retire')}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">{t('detail.retireHint')}</p>
            <button type="button" onClick={() => setConfirmRetire(true)} className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground">
              <Trash2 className="h-3 w-3" /> {t('detail.retire')}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
