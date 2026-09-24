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
 *
 * ⭐ ADR-666 — THE RUNS ARE RUNS. Each one is a row from `runs` rendered by the
 * one `RunView`, merged with the live ledger (`useRuns`) so a run going now
 * shows its steps as they land, for every member. What a run read and wrote
 * are its steps — the "made from" line ADR-659 D2 derived by a time window is
 * now on the run itself.
 *
 * ⭐ BROWSER WORK (ADR-666 D1/D4) shows where it works (its sites) instead of
 * sources, and holds its conversation: Run now opens the run there and this
 * page performs it, in the member's own browser, while they watch. Only the
 * member whose browser it is may run it. `?supervisor.start=1` (the cockpit's
 * and the tray's "Run it") starts it here — ONE door starts a browser run.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { ArrowLeft, CalendarClock, FolderOpen, Globe, Loader2, Pause, Play, Trash2, Zap } from 'lucide-react';
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
import { browserHands } from '@/lib/shell/hands';
import { AddSource, MAX_SOURCES_PROSE, SourceRow, isStructured } from '@/components/supervisor/SourceList';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { Working } from '@/components/shared/Working';
import { useStandingWords } from '@/components/standing/StandingRow';
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

export function StandingDetail({
  topic, onBack, onChanged,
}: {
  topic: string;
  onBack: () => void;
  onChanged: () => void;
}) {
  const t = useTranslations('supervisor');
  const { runAction } = useFeedback();
  const { navigateToSurface, userId } = useSurfacePreferences();
  const param = useSurfaceParam('supervisor');
  const { problemCopy, describeSchedule, ownerLine, scheduleLine } = useStandingWords();
  const { runs: ledger } = useRuns();
  const [detail, setDetail] = useState<StandingDetailData | null>(null);
  // ADR-666 D4 — the browser run this page is performing, and its conversation.
  const [activeRun, setActiveRun] = useState<string | null>(null);
  const [laneId, setLaneId] = useState<string | null>(null);
  const [editingSites, setEditingSites] = useState(false);
  const [sitesDraft, setSitesDraft] = useState('');
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
      setLaneId((cur) => cur ?? d.lane_id ?? null);
      setMissing(false);
    } catch {
      setMissing(true);
    }
  }, [topic]);

  useEffect(() => { void load(); }, [load]);

  // The live ledger moved for THIS work (a run started, a step landed, a run
  // ended) — the summary's last run and state follow. Keyed on what changed,
  // so an unrelated run elsewhere in the workspace costs nothing.
  const liveKey = (ledger ?? [])
    .filter((r) => r.topic === topic)
    .map((r) => `${r.id}:${r.state}:${r.steps.length}`)
    .join('|');
  useEffect(() => {
    if (liveKey) void load();
  }, [liveKey, load]);

  // `?supervisor.start=1` — the cockpit's and the tray's "Run it" land here,
  // so there is ONE door that starts a browser run. Consumed once: the param
  // is an act, not a state. Declared above the early returns (hooks never
  // follow a conditional return); the door itself is `startBrowserRun`.
  const startRef = useRef<(() => Promise<void>) | null>(null);
  const startParam = param.get('start');
  const isBrowserWork = Boolean(detail?.summary.browser);
  useEffect(() => {
    if (startParam !== '1' || !isBrowserWork) return;
    param.set({ start: null });
    void startRef.current?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [startParam, isBrowserWork]);

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
  const browser = s.browser ?? null;
  const mineToRun = !browser || browser.member === userId;
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
    if (browser) {
      await startBrowserRun();
      return;
    }
    setBusy(true);
    try {
      const res = await runAction(() => api.standing.run(s.topic), { pending: t('action.runningPending', { topic: s.topic }) });
      setNote(
        res.already
          ? t('detail.alreadyRunning')
          : res.no_change
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

  /** ADR-666 D4 — the ONE door that starts a browser run: this page must hold
   *  the browser (the extension, on), and it must be this member's. */
  async function startBrowserRun() {
    if (busy || !browser) return;
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
      setBusy(false);
      void load();
      onChanged();
    }
  }
  startRef.current = startBrowserRun;

  const saveSites = async () => {
    const sites = sitesDraft.split(/[\s,]+/).map((x) => x.trim()).filter(Boolean);
    if (busy || sites.length === 0) return;
    setBusy(true);
    try {
      await runAction(() => api.standing.update(s.topic, { browser_sites: sites }), {
        success: t('detail.sitesChanged'),
        error: t('detail.couldNotChangeSites'),
      });
      setEditingSites(false);
    } catch {
      /* refused by name; the reload restores the true state */
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

  // Worded here, never inline: a multi-line ternary in JSX reads to the ADR-660
  // meter as literal copy even when every branch is a `t()` call.
  const browserNote = !browser
    ? ''
    : mineToRun
      ? t('detail.browserYours')
      : t('detail.browserOf', { name: browser.member_name || s.topic });

  // The runs: this work's history (the detail's read) with the live ledger's
  // copy of any run it also holds — newer, since realtime keeps it current.
  const liveById = new Map((ledger ?? []).filter((r) => r.topic === s.topic).map((r) => [r.id, r]));
  const runs: Run[] = [
    ...Array.from(liveById.values()).filter((r) => !detail.runs.some((d) => d.id === r.id)),
    ...detail.runs.map((r) => liveById.get(r.id) ?? r),
  ].sort((a, b) => String(b.started_at ?? '').localeCompare(String(a.started_at ?? '')));

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
              {ownerLine(s, userId)}
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
          {browser ? (
            <div className="sm:col-span-2">
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
                        onClick={() => void saveSites()}
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
          )}
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

      {browser && laneId && (
        <section className="space-y-2">
          <div>
            <h3 className="text-[13px] font-medium text-foreground/80">{t('detail.conversation')}</h3>
            <p className="text-[11px] text-muted-foreground">{t('detail.conversationHint')}</p>
          </div>
          <Conversation
            laneId={laneId}
            app={s.app || 'text'}
            startRunId={activeRun}
            onRunTurnSettled={() => { setActiveRun(null); void load(); onChanged(); }}
          />
        </section>
      )}

      <section className="space-y-2">
        <h3 className="text-[13px] font-medium text-foreground/80">{t('detail.runs')}</h3>
        {runs.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            {browser ? t('detail.runsEmptyBrowser') : t('detail.runsEmpty')}
          </div>
        ) : (
          <ul className="space-y-2">
            {runs.map((r) => (
              <li key={r.id}>
                <RunView
                  run={r}
                  viewerId={userId}
                  compact
                  onRunIt={browser ? () => void startBrowserRun() : undefined}
                  onOpenFile={(path) => navigateToSurface('files', { path })}
                  onChanged={() => void load()}
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
