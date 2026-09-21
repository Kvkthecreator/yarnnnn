'use client';

/**
 * SupervisorSurface — the Supervisor app's pane (ADR-656 §7 → ADR-658).
 *
 * THE FIRST COMPOSED SURFACE IN YARNNN: its shape is DECLARED (the sections
 * below) rather than mirrored from one substrate concern. That is the register
 * ADR-435 declined to name and ADR-653 D3.a promoted, and this is its first
 * tenant.
 *
 * ⭐ WHAT IT IS FOR (ADR-658 §11): where a member creates, sees and manages the
 * work that runs on its own — a verb bound to a connected system, minded by an
 * agent the workspace derives. The `work` band is the cockpit; a row opens its
 * detail (D6); the empty state offers pre-shaped starts (D7); the door creates
 * (D4). Files shows files, Reach shows connections, Chat shows one
 * conversation, Notifications shows what already happened — nothing else shows
 * the work itself, which is why this is not the glorified redirect ADR-435
 * deleted the last composition for being.
 *
 * ⚠️ ONE READER PER LEDGER. The roster is `api.standing.list` (the same route
 * the Notifications mirror reads); the composed bands are `api.supervisor.state`.
 * The three reads are independent and each degrades to its own empty — one
 * unreadable band never blanks the surface.
 *
 * THE THREE BANDS (APP-BUILDER-UX §2.2, the part that survived the re-scope):
 *   1. what this is      — the name and the one-line claim
 *   2. who is minding it — the resident, named
 *   3. the work          — the declared sections
 */

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api, type StandingStart, type StandingSummary } from '@/lib/api/client';
import {
  SupervisorSection,
  type SupervisorStateData,
  type WorkBand,
} from '@/components/supervisor/SupervisorSection';
import { NewStandingWorkModal } from '@/components/supervisor/NewStandingWorkModal';
import { StandingDetail } from '@/components/supervisor/StandingDetail';
import { Working } from '@/components/shared/Working';
import { useFeedback } from '@/contexts/FeedbackContext';
import { useSurfaceParam, useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';

/**
 * The app's declared sections.
 *
 * ⚠️ DECLARED, not hardcoded rendering: the surface renders whatever this list
 * says, through the dispatch — which is the whole difference between a composed
 * surface and a bespoke one. A kind this client cannot draw renders the honest
 * amber miss rather than a blank.
 *
 * ⭐ Ordered by what a member manages first: the work itself, then what is
 * waiting on them, then the decisions note — reference, not a call to act.
 */
/** ADR-660 — the declaration holds catalog KEYS: this table is evaluated at
 *  import, before any member's language is known. The title is worded at
 *  render, so the DECLARED shape is unchanged. */
const SECTIONS: Array<{ kind: string; titleKey: string }> = [
  { kind: 'work', titleKey: 'sectionWork' },
  { kind: 'needs-you', titleKey: 'sectionNeedsYou' },
  { kind: 'note', titleKey: 'sectionNote' },
];

export function SupervisorSurface() {
  const t = useTranslations('supervisor');
  const [data, setData] = useState<SupervisorStateData | null>(null);
  const [failed, setFailed] = useState(false);
  const [rows, setRows] = useState<StandingSummary[] | null>(null);
  const [rosterFailed, setRosterFailed] = useState(false);
  const [starts, setStarts] = useState<StandingStart[]>([]);
  const [timezone, setTimezone] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [newOpen, setNewOpen] = useState(false);
  const [newStart, setNewStart] = useState<StandingStart | null>(null);
  const { navigateToSurface } = useSurfacePreferences();
  const { runAction } = useFeedback();
  const param = useSurfaceParam('supervisor');
  // The detail (ADR-658 D6) is a deep-linkable pane param, like every other
  // surface's: `?supervisor.work=<topic>`.
  const openTopic = param.get('work');

  const loadRoster = useCallback(async () => {
    try {
      const list = await api.standing.list();
      setRows(list);
      setRosterFailed(false);
      const tz = list.find((r) => r.timezone)?.timezone ?? null;
      if (tz) setTimezone(tz);
    } catch {
      setRows([]);
      setRosterFailed(true);
    }
  }, []);

  // ⚠️ THREE READS, EACH LANDING ON ITS OWN (driven 2026-09-19). A first cut
  // awaited them together, so a 23-second mentions read held the roster — and
  // even an opened detail — behind one spinner. "Every band degrades
  // independently" has a twin: every band ARRIVES independently.
  useEffect(() => {
    let cancelled = false;
    api.supervisor.state().then(
      (result) => {
        if (cancelled) return;
        // Defensive: a read path never trusts the served shape (house style).
        setData({
          needs_you: Array.isArray(result?.needs_you) ? result.needs_you : [],
          note: result?.note ?? null,
        });
      },
      () => { if (!cancelled) setFailed(true); },
    );
    api.standing.list().then(
      (list) => {
        if (cancelled) return;
        setRows(list);
        const tz = list.find((r) => r.timezone)?.timezone ?? null;
        if (tz) setTimezone(tz);
      },
      () => { if (!cancelled) { setRows([]); setRosterFailed(true); } },
    );
    api.standing.starts().then(
      (st) => { if (!cancelled) setStarts(Array.isArray(st) ? st : []); },
      () => { if (!cancelled) setStarts([]); },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  // Opening a mention is a navigation, never a mutation.
  const openLane = useCallback(
    (laneId: string) => {
      navigateToSurface('chat', { lane: laneId });
    },
    [navigateToSurface],
  );

  const runNow = useCallback(async (row: StandingSummary) => {
    if (busy) return;
    setBusy(row.topic);
    try {
      const res = await runAction(() => api.standing.run(row.topic), {
        pending: t('action.runningPending', { topic: row.topic }),
      });
      const line = res.no_change
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
      setNotes((n) => ({ ...n, [row.topic]: line }));
    } catch (e) {
      setNotes((n) => ({
        ...n,
        [row.topic]: t('action.runFailed', { reason: e instanceof Error ? e.message : String(e) }),
      }));
    } finally {
      setBusy(null);
      void loadRoster();
    }
  }, [busy, loadRoster, runAction, t]);

  const togglePause = useCallback(async (row: StandingSummary) => {
    if (busy) return;
    setBusy(row.topic);
    try {
      await runAction(() => api.standing.update(row.topic, { paused: !row.paused }), {
        success: row.paused ? t('action.resumed') : t('action.paused'),
        error: row.paused ? t('action.couldNotResume') : t('action.couldNotPause'),
      });
    } catch {
      /* reported; the reload below restores the true state */
    } finally {
      setBusy(null);
      void loadRoster();
    }
  }, [busy, loadRoster, runAction, t]);

  const work: WorkBand = {
    rows,
    failed: rosterFailed,
    starts,
    busy,
    notes,
    onRunNow: runNow,
    onTogglePause: togglePause,
    onOpen: (row) => param.set({ work: row.topic }),
    onNew: (start) => {
      setNewStart(start);
      setNewOpen(true);
    },
    onOpenReach: () => {
      navigateToSurface('reach');
    },
  };

  if (failed && rosterFailed) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
          {t('surface.unreadable')}
        </div>
      </div>
    );
  }
  // ADR-651 — the ONE way to say wait, self-bounding at 6s and 30s. Shown only
  // while NOTHING has arrived AND no piece of work is opened: the bands load
  // INDEPENDENTLY (ADR-658 D5), so a slow mentions read never holds the work
  // band — the app's reason — behind a spinner, and an opened detail reads
  // only its own route. A band whose read is still out says "Loading…" itself.
  if (!openTopic && !data && !failed && rows === null && !rosterFailed) return <Working label={t('surface.loading')} fill />;

  // null = the composed bands' read is still out (or failed); each band says so.
  const state: SupervisorStateData | null = data ?? (failed ? { needs_you: [], note: null } : null);

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      {/* Band 1 — the visible claim. */}
      <header className="border-b border-border/60 px-5 py-4">
        <h1 className="text-[15px] font-semibold text-foreground">{t('surface.title')}</h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          {t('surface.claim')}
        </p>
      </header>

      {/* Band 2 — who is minding it. Resting: calm, not absent. */}
      <div className="border-b border-border/60 bg-muted/20 px-5 py-2.5">
        <p className="text-[13px] text-foreground/80">{t('surface.minder')}</p>
      </div>

      {/* Band 3 — the declared sections, or one piece of work opened (D6). */}
      {openTopic ? (
        <StandingDetail
          topic={openTopic}
          onBack={() => param.set({ work: null })}
          onChanged={() => void loadRoster()}
        />
      ) : (
        <div className="flex-1 space-y-5 px-5 py-4">
          {SECTIONS.map((section) => (
            <SupervisorSection
              key={section.kind}
              section={{ kind: section.kind, title: t(`surface.${section.titleKey}`) }}
              data={state}
              work={work}
              onOpenLane={openLane}
            />
          ))}
        </div>
      )}

      <NewStandingWorkModal
        open={newOpen}
        start={newStart}
        starts={starts}
        timezone={timezone}
        onClose={() => setNewOpen(false)}
        onCreated={(created) => {
          setNewOpen(false);
          void loadRoster();
          param.set({ work: created.topic });
        }}
      />
    </div>
  );
}
