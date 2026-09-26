'use client';

/**
 * StandingDetail — one piece of standing work, opened (ADR-658 D6), split
 * across the frame (ADR-670 D6).
 *
 * A work opened is the Supervisor's OBJECT level (`?supervisor.work=<topic>`).
 * It is not one whole-pane rendering any more: the frame's canvas holds the
 * object itself and its side holds its supervision, so the two halves render
 * in the two slots and share one state (`useStandingDetail`):
 *
 *   canvas (`StandingDetailCanvas`) — the object: which file it keeps and who
 *     looks after it, what is wrong with it, the work's own conversation
 *     (browser work, ADR-666 D4), and its instructions.
 *   side (`StandingDetailSide`) — its supervision: Run now · Pause/Resume and
 *     what the last act said, when it runs and when next, where its updates
 *     come from (or, for browser work, where it works), its runs, and Retire.
 *
 * There is no back bar: the locator strip is the spine (the crumb the surface
 * registers returns to the index, and on a phone the strip is a back-chip).
 *
 * Bounded to the declaration's OWN facts — which file it keeps, who looks after
 * it (derived), when it runs, where its updates come from, its instructions,
 * and its runs from the ledger. ADR-639 D4 deleted the strings pane's
 * parties/consumers/head-facts chrome; this is not that.
 *
 * The verbs act on the DECLARATION, never on a being: Run now · Pause/Resume ·
 * change the schedule (the composer's own field, refused by name when it
 * would break the work) · edit the instructions (as the FILE they are, through
 * the ordinary file door — never a second one) · Retire (the declaration goes
 * to Trash; the kept file and its instructions stay, with their history).
 *
 * ⭐ ADR-666 — THE RUNS ARE RUNS. Each one is a row from `runs` rendered by the
 * one `RunView`, merged with the live ledger (`useRuns`) so a run going now
 * shows its steps as they land, for every member. What a run read and wrote
 * are its steps.
 *
 * ⭐ BROWSER WORK (ADR-666 D1/D4) shows where it works (its sites) instead of
 * sources, and holds its conversation: Run now opens the run there and this
 * page performs it, in the member's own browser, while they watch. Only the
 * member whose browser it is may run it. `?supervisor.start=1` (the "Run it"
 * of `useOpenRun`) starts it here — ONE door starts a browser run.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { CalendarClock, FolderOpen, Globe, Loader2, Pause, Play, Trash2, Zap } from 'lucide-react';
import {
  api,
  type Run,
  type StandingDetailData,
  type StandingSource,
  type StandingStart,
} from '@/lib/api/client';
import { RunView } from '@/components/runs/RunView';
import { Conversation } from '@/components/supervisor/Conversation';
import { useRuns } from '@/lib/runs/useRuns';
import { useOpenRun } from '@/lib/runs/openRun';
import { browserHands } from '@/lib/shell/hands';
import { AddSource, MAX_SOURCES_PROSE, SourceRow, isStructured } from '@/components/supervisor/SourceList';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { Working } from '@/components/shared/Working';
import { StandingStateBadge, useStandingWords } from '@/components/standing/StandingRow';
import { useFeedback } from '@/contexts/FeedbackContext';
import { useSurfaceParam, useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { formatLedgerTime } from '@/lib/formatting';

/** ADR-660 — the presets hold catalog KEYS, not words: this table is evaluated
 *  at import, before any member's language is known. */
const PRESETS: Array<{ labelKey: string; cron: string }> = [
  { labelKey: 'preset.weekdays9', cron: '0 9 * * 1-5' },
  { labelKey: 'preset.daily9', cron: '0 9 * * *' },
  { labelKey: 'preset.monday9', cron: '0 9 * * 1' },
  { labelKey: 'preset.hourly', cron: '0 * * * *' },
];

const H3 = 'text-[13px] font-medium text-foreground/80';
const EMPTY = 'rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground';

/**
 * The ONE state of an opened piece of work — read once, acted on from both
 * halves. `topic` null = nothing open; the hook reads nothing.
 */
export function useStandingDetail({
  topic, starts, onChanged, onRetired,
}: {
  topic: string | null;
  /** What the surface already read (`api.standing.starts`) — never read twice. */
  starts: StandingStart[];
  /** The roster may have changed — the surface re-reads it. */
  onChanged: () => void;
  /** The work was retired — the surface returns to its index. */
  onRetired: () => void;
}) {
  const t = useTranslations('supervisor');
  const { runAction } = useFeedback();
  const { userId } = useSurfacePreferences();
  const param = useSurfaceParam('supervisor');
  const { describeSchedule } = useStandingWords();
  const { runs: ledger } = useRuns();
  const [detail, setDetail] = useState<StandingDetailData | null>(null);
  // ADR-666 D4 — the browser run this page is performing, and its conversation.
  const [activeRun, setActiveRun] = useState<string | null>(null);
  const [laneId, setLaneId] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  const [busy, setBusy] = useState(false);
  // A derive Run now in flight — band 2 says "Updating …" for exactly this,
  // never for a save or a pause (which also hold `busy`).
  const [runningNow, setRunningNow] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  // am.5 — what the sources' ADD control offers beside the starts; degrades to
  // empty rather than blocking the pane.
  const [folders, setFolders] = useState<Array<{ path: string; label: string }>>([]);

  const load = useCallback(async () => {
    if (!topic) return;
    try {
      const d = await api.standing.get(topic);
      setDetail(d);
      setLaneId((cur) => cur ?? d.lane_id ?? null);
      setMissing(false);
    } catch {
      setMissing(true);
    }
  }, [topic]);

  // A different piece of work opened: nothing of the last one carries over.
  useEffect(() => {
    setDetail(null);
    setMissing(false);
    setActiveRun(null);
    setLaneId(null);
    setNote(null);
    void load();
  }, [load]);

  // The live ledger moved for THIS work (a run started, a step landed, a run
  // ended) — the summary's last run and state follow. Keyed on what changed,
  // so an unrelated run elsewhere in the workspace costs nothing.
  const liveKey = topic
    ? (ledger ?? [])
      .filter((r) => r.topic === topic)
      .map((r) => `${r.id}:${r.state}:${r.steps.length}`)
      .join('|')
    : '';
  useEffect(() => {
    if (liveKey) void load();
  }, [liveKey, load]);

  useEffect(() => {
    if (!topic) return;
    let live = true;
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
  }, [topic]);

  const s = detail?.summary ?? null;
  const browser = s?.browser ?? null;
  const mineToRun = !browser || browser.member === userId;

  const settle = useCallback(() => {
    setBusy(false);
    void load();
    onChanged();
  }, [load, onChanged]);

  /** ADR-666 D4 — the ONE door that starts a browser run: this page must hold
   *  the browser (the extension, on), and it must be this member's. */
  async function startBrowserRun() {
    if (busy || !s || !browser) return;
    if (!mineToRun) {
      setNote(t('detail.notYours', { name: browser.member_name || s.topic }));
      return;
    }
    const hands = await browserHands();
    if (!hands.on) {
      setNote(t('detail.needsExtension'));
      return;
    }
    setBusy(true);
    try {
      const res = await api.standing.run(s.topic);
      if (res.browser && res.run_id && res.lane_id) {
        setLaneId(res.lane_id);
        setActiveRun(res.run_id);
        setNote(res.already ? t('detail.alreadyRunning') : t('detail.runStarted'));
      }
    } catch (e) {
      setNote(t('action.runFailed', { reason: e instanceof Error ? e.message : String(e) }));
    } finally {
      settle();
    }
  }

  // `?supervisor.start=1` — "Run it" lands here, so there is ONE door that
  // starts a browser run. Consumed once: the param is an act, not a state.
  const startRef = useRef<(() => Promise<void>) | null>(null);
  startRef.current = startBrowserRun;
  const startParam = param.get('start');
  const isBrowserWork = Boolean(browser);
  useEffect(() => {
    if (startParam !== '1' || !isBrowserWork) return;
    param.set({ start: null });
    void startRef.current?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startParam, isBrowserWork]);

  const runNow = async () => {
    if (busy || !s) return;
    if (browser) {
      await startBrowserRun();
      return;
    }
    setBusy(true);
    setRunningNow(true);
    try {
      const res = await runAction(() => api.standing.run(s.topic), { pending: t('action.runningPending', { topic: s.topic }) });
      // Worded here, never inline (the ADR-660 meter reads a JSX ternary as copy).
      const line = res.already
        ? t('detail.alreadyRunning')
        : res.no_change
        ? t('action.ranNoChange')
        : res.success
          ? t('action.ranUpdated')
          : res.error_reason === 'shape_violation'
            ? t('action.refusedShape', { detail: res.detail ?? t('action.refusedShapeFallback') })
            : res.error_reason === 'output_truncated'
              ? t('action.refusedTruncated')
              : res.error_reason === 'router_disabled'
                ? t('action.skippedRouterDisabled')
                : t('action.runFailed', { reason: res.error_reason ?? t('action.runFailedUnknown') });
      setNote(line);
    } catch (e) {
      setNote(t('action.runFailed', { reason: e instanceof Error ? e.message : String(e) }));
    } finally {
      setRunningNow(false);
      settle();
    }
  };

  const togglePause = async () => {
    if (busy || !s) return;
    setBusy(true);
    try {
      await runAction(() => api.standing.update(s.topic, { paused: !s.paused }), {
        success: s.paused ? t('action.resumed') : t('action.paused'),
        error: s.paused ? t('action.couldNotResume') : t('action.couldNotPause'),
      });
    } catch {
      /* reported; the reload restores the true state */
    } finally {
      settle();
    }
  };

  /** Each save answers whether it landed, so its editor knows to close. */
  const saveSchedule = async (cron: string): Promise<boolean> => {
    const next = cron.trim();
    if (!next || busy || !s) return false;
    setBusy(true);
    try {
      await runAction(() => api.standing.update(s.topic, { schedule: next }), {
        success: t('detail.scheduleChanged', { cadence: describeSchedule(next) }),
        error: t('detail.couldNotChangeSchedule'),
      });
      return true;
    } catch {
      return false;
    } finally {
      settle();
    }
  };

  const saveSites = async (draft: string): Promise<boolean> => {
    const sites = draft.split(/[\s,]+/).map((x) => x.trim()).filter(Boolean);
    if (busy || !s || sites.length === 0) return false;
    setBusy(true);
    try {
      await runAction(() => api.standing.update(s.topic, { browser_sites: sites }), {
        success: t('detail.sitesChanged'),
        error: t('detail.couldNotChangeSites'),
      });
      return true;
    } catch {
      return false; // refused by name; the reload restores the true state
    } finally {
      settle();
    }
  };

  const saveSources = async (draft: StandingSource[]): Promise<boolean> => {
    if (busy || !s || draft.length === 0) return false;
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
      return true;
    } catch {
      return false; // reported by name; the reload restores the true state
    } finally {
      settle();
    }
  };

  const saveText = async (text: string): Promise<boolean> => {
    if (busy || !s || !detail) return false;
    setBusy(true);
    try {
      await runAction(
        () => api.workspace.editFile(detail.contract_path, text, undefined, t('detail.editMessage', { topic: s.topic })),
        { success: t('detail.instructionsSaved'), error: t('detail.couldNotSaveInstructions') },
      );
      return true;
    } catch {
      return false;
    } finally {
      setBusy(false);
      void load();
    }
  };

  const retire = async (): Promise<boolean> => {
    if (busy || !s) return false;
    setBusy(true);
    try {
      await runAction(() => api.standing.retire(s.topic), {
        success: t('detail.retired', { target: s.target }),
        error: t('detail.couldNotRetire'),
      });
      onChanged();
      onRetired();
      return true;
    } catch {
      setBusy(false);
      return false;
    }
  };

  const runTurnSettled = () => {
    setActiveRun(null);
    void load();
    onChanged();
  };

  // The runs: this work's history (the detail's read) with the live ledger's
  // copy of any run it also holds — newer, since realtime keeps it current.
  const liveById = new Map((ledger ?? []).filter((r) => r.topic === topic).map((r) => [r.id, r]));
  const runs: Run[] = detail
    ? [
      ...Array.from(liveById.values()).filter((r) => !detail.runs.some((d) => d.id === r.id)),
      ...detail.runs.map((r) => liveById.get(r.id) ?? r),
    ].sort((a, b) => String(b.started_at ?? '').localeCompare(String(a.started_at ?? '')))
    : [];

  return {
    topic, detail, missing, busy, runningNow, note, laneId, activeRun, starts, folders, runs, mineToRun,
    reload: load, runNow, startBrowserRun, togglePause, saveSchedule, saveSites, saveSources, saveText, retire,
    runTurnSettled,
  };
}

export type StandingDetailState = ReturnType<typeof useStandingDetail>;

/**
 * The canvas half — the OBJECT: the kept file and who keeps it, what is wrong
 * with it, the work's own conversation, and its instructions.
 */
export function StandingDetailCanvas({ work }: { work: StandingDetailState }) {
  const t = useTranslations('supervisor');
  const { navigateToSurface, userId } = useSurfacePreferences();
  const { problemCopy, ownerLine } = useStandingWords();
  const [editingText, setEditingText] = useState(false);
  const [text, setText] = useState('');

  if (work.missing) return <div className={EMPTY}>{t('detail.gone')}</div>;
  const detail = work.detail;
  if (!detail) return <Working label={t('detail.loading')} fill />;

  const s = detail.summary;
  const kept = s.target_path ?? `/workspace/${s.topic}/${s.target}`;
  const browser = s.browser ?? null;

  return (
    <div className="space-y-5">
      <header className="min-w-0">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1">
          <button
            type="button"
            onClick={() => navigateToSurface('files', { path: kept })}
            className="flex min-w-0 items-center gap-1.5 text-[15px] font-semibold text-foreground hover:underline"
            title={t('detail.openInFiles')}
          >
            <FolderOpen className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate">{s.target || t('detail.noFileNamed')}</span>
          </button>
          <StandingStateBadge row={s} />
        </div>
        <p className="mt-0.5 text-xs text-muted-foreground">{ownerLine(s, userId)}</p>
        {s.problem != null && (
          <p className="mt-3 rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            {problemCopy(s.problem)}
          </p>
        )}
      </header>

      {browser && work.laneId && (
        <section className="space-y-2">
          <div>
            <h3 className={H3}>{t('detail.conversation')}</h3>
            <p className="text-[11px] text-muted-foreground">{t('detail.conversationHint')}</p>
          </div>
          <Conversation
            laneId={work.laneId}
            app={s.app || 'text'}
            startRunId={work.activeRun}
            onRunTurnSettled={work.runTurnSettled}
          />
        </section>
      )}

      <section className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className={H3}>{t('detail.instructions')}</h3>
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
              <button
                type="button"
                onClick={async () => { if (await work.saveText(text)) setEditingText(false); }}
                disabled={work.busy || !text.trim()}
                className="rounded-md bg-foreground px-3 py-1.5 text-xs text-background disabled:opacity-50"
              >
                {t('detail.save')}
              </button>
            </div>
          </div>
        ) : detail.contract ? (
          <div className="rounded-md border border-border/60 px-4 py-3">
            <MarkdownRenderer content={detail.contract} />
          </div>
        ) : (
          <div className={EMPTY}>{t('detail.instructionsEmpty')}</div>
        )}
      </section>
    </div>
  );
}

/**
 * The side half — its SUPERVISION: the verbs and what they said, the cadence,
 * where its updates come from, its runs, and Retire.
 */
export function StandingDetailSide({
  work, exceptRunId,
}: {
  work: StandingDetailState;
  /** The run the canvas is showing in full — one rendering per run on screen. */
  exceptRunId?: string | null;
}) {
  const t = useTranslations('supervisor');
  const { navigateToSurface, userId } = useSurfacePreferences();
  const { scheduleLine } = useStandingWords();
  const openRun = useOpenRun();
  const [editingSchedule, setEditingSchedule] = useState(false);
  const [cron, setCron] = useState('');
  const [editingSites, setEditingSites] = useState(false);
  const [sitesDraft, setSitesDraft] = useState('');
  const [editingSources, setEditingSources] = useState(false);
  const [draft, setDraft] = useState<StandingSource[]>([]);
  const [confirmRetire, setConfirmRetire] = useState(false);

  const detail = work.detail;
  if (!detail) return null;

  const s = detail.summary;
  const browser = s.browser ?? null;
  const busy = work.busy;
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
  const browserNote = !browser
    ? ''
    : work.mineToRun
      ? t('detail.browserYours')
      : t('detail.browserOf', { name: browser.member_name || s.topic });
  const runsEmpty = browser ? t('detail.runsEmptyBrowser') : t('detail.runsEmpty');
  const runs = work.runs.filter((r) => r.id !== exceptRunId);

  return (
    <div className="space-y-5">
      <section className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void work.runNow()}
            disabled={busy || s.problem != null}
            title={s.problem != null ? t('row.blockedTitle') : t('row.runNowTitle')}
            className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />} {t('detail.runNow')}
          </button>
          <button
            type="button"
            onClick={() => void work.togglePause()}
            disabled={busy}
            className="flex items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
          >
            {s.paused ? (<><Play className="h-3.5 w-3.5" /> {t('detail.resume')}</>) : (<><Pause className="h-3.5 w-3.5" /> {t('detail.pause')}</>)}
          </button>
        </div>
        {work.note && <p className="text-xs text-foreground">{work.note}</p>}
      </section>

      <dl className="space-y-3 text-xs">
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
                <button
                  type="button"
                  onClick={async () => { if (await work.saveSchedule(cron)) setEditingSchedule(false); }}
                  disabled={busy}
                  className="rounded border px-2 py-1 text-xs hover:bg-muted disabled:opacity-40"
                >
                  {t('detail.save')}
                </button>
                <button type="button" onClick={() => setEditingSchedule(false)} className="text-xs text-muted-foreground hover:text-foreground">{t('detail.cancel')}</button>
              </span>
            ) : (
              <span className="inline-flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1"><CalendarClock className="h-3 w-3" /> {scheduleLine(s.schedule, s.timezone)}</span>
                <button type="button" onClick={() => { setCron(currentCron); setEditingSchedule(true); }} className="text-[11px] text-muted-foreground underline hover:text-foreground">{t('detail.change')}</button>
              </span>
            )}
          </dd>
        </div>
        <div>
          <dt className="text-muted-foreground">{t('detail.next')}</dt>
          {/* ⚠️ A declaration with a problem will NOT run at its next scheduled
              time, so the field says what is true instead of a time to plan
              around. The paused state is said once, here — the badge on the
              canvas says it too, as the object's state. */}
          <dd className="mt-0.5 text-foreground">{nextLine}</dd>
        </div>
        {browser ? (
          <div>
            <div className="flex items-baseline justify-between gap-3">
              <dt className="text-muted-foreground">{t('detail.sitesLabel')}</dt>
              {!editingSites && (
                <button
                  type="button"
                  onClick={() => { setSitesDraft(browser.sites.join(', ')); setEditingSites(true); }}
                  className="text-[11px] text-muted-foreground underline hover:text-foreground"
                >
                  {t('detail.change')}
                </button>
              )}
            </div>
            <dd className="mt-1 text-foreground">
              {editingSites ? (
                <div className="space-y-2">
                  <input
                    value={sitesDraft}
                    onChange={(e) => setSitesDraft(e.target.value)}
                    placeholder={t('detail.sitesPlaceholder')}
                    className="w-full rounded-md border border-border bg-background px-3 py-1.5 text-xs"
                  />
                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={() => setEditingSites(false)} className="rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground">{t('detail.cancel')}</button>
                    <button
                      type="button"
                      onClick={async () => { if (await work.saveSites(sitesDraft)) setEditingSites(false); }}
                      disabled={busy || !sitesDraft.trim()}
                      className="rounded-md bg-foreground px-2.5 py-1 text-xs text-background disabled:opacity-40"
                    >
                      {t('detail.save')}
                    </button>
                  </div>
                </div>
              ) : (
                <ul className="flex flex-wrap gap-1.5">
                  {browser.sites.map((site) => (
                    <li key={site} className="inline-flex items-center gap-1 rounded-md border border-border/70 px-2 py-0.5 text-[11px]">
                      <Globe className="h-3 w-3 text-muted-foreground" /> {site}
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-2 text-[11px] text-muted-foreground">{browserNote}</p>
            </dd>
          </div>
        ) : (
          <div>
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
              {/* ⭐ EDITABLE (am.5). `sources` has always been PATCHable and
                  the server refuses an invalid set BY NAME. */}
              {editingSources ? (
                <div className="space-y-2">
                  {draft.length > 0 && (
                    <ul className="space-y-1.5">
                      {draft.map((src) => (
                        <SourceRow
                          key={src.id}
                          source={src}
                          starts={work.starts}
                          onRemove={() => setDraft((xs) => xs.filter((x) => x.id !== src.id))}
                        />
                      ))}
                    </ul>
                  )}
                  <AddSource
                    starts={work.starts}
                    existing={draft}
                    folders={work.folders}
                    disabled={draft.length >= maxSources}
                    onAdd={(x) => setDraft((xs) => [...xs, x])}
                  />
                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={() => setEditingSources(false)} className="rounded-md px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground">{t('detail.cancel')}</button>
                    <button
                      type="button"
                      onClick={async () => { if (await work.saveSources(draft)) setEditingSources(false); }}
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
                    <SourceRow key={src.id} source={src} starts={work.starts} />
                  ))}
                </ul>
              )}
            </dd>
          </div>
        )}
      </dl>

      <section className="space-y-2">
        <h3 className={H3}>{t('detail.runs')}</h3>
        {runs.length === 0 ? (
          <div className={EMPTY}>{runsEmpty}</div>
        ) : (
          <ul className="space-y-2">
            {runs.map((r) => (
              <li key={r.id}>
                <RunView
                  run={r}
                  viewerId={userId}
                  compact
                  onOpen={(run) => openRun(run)}
                  onRunIt={browser ? () => void work.startBrowserRun() : undefined}
                  onOpenFile={(path) => navigateToSurface('files', { path })}
                  onChanged={() => void work.reload()}
                />
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
              <button
                type="button"
                onClick={async () => { if (!(await work.retire())) setConfirmRetire(false); }}
                disabled={busy}
                className="inline-flex items-center gap-1.5 rounded-md border border-destructive/40 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/5 disabled:opacity-50"
              >
                {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Trash2 className="h-3 w-3" />} {t('detail.retire')}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">{t('detail.retireHint')}</p>
            <button type="button" onClick={() => setConfirmRetire(true)} className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground">
              <Trash2 className="h-3 w-3" /> {t('detail.retire')}
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
