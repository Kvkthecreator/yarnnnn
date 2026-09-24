'use client';

/**
 * SupervisorSurface — the Supervisor app's pane (ADR-656 §7 → ADR-658).
 *
 * THE FIRST COMPOSED SURFACE IN YARNNN: its shape is DECLARED (the sections
 * below) rather than mirrored from one substrate concern. That is the register
 * ADR-435 declined to name and ADR-653 D3.a promoted, and this is its first
 * tenant.
 *
 * ⭐ WHAT IT IS FOR (ADR-658 §11 → ADR-667): where a member sets up, sees and
 * manages the work that keeps happening. Work is SET UP IN CONVERSATION — the
 * Supervisor's own agent, beside the cockpit (ADR-667 D1) — and the browser is
 * the prerequisite for setting up and running it, never for seeing it
 * (`BrowserGate`, D4). The cockpit reads by run state; a row opens its detail
 * (ADR-658 D6). Files shows files, Reach shows connections, Chat shows one
 * conversation, Notifications shows what already happened — nothing else shows
 * the work itself, which is why this is not the glorified redirect ADR-435
 * deleted the last composition for being.
 *
 * ⚠️ ONE READER PER LEDGER. The roster is `api.standing.list` (the same route
 * the Notifications mirror reads); the runs are `useRuns` (the one client store
 * of `GET /api/runs`, live — the tray reads the same store); the mentions are
 * `api.supervisor.state`. The reads are independent and each degrades to its
 * own empty — one unreadable band never blanks the surface.
 *
 * ⭐ ADR-666 D8 — THE COCKPIT READS BY RUN STATE: running · needs-you · work ·
 * recent. Starting browser work goes through the detail's one door
 * (`?supervisor.start=1`), because a browser run happens in the work's own
 * conversation, which lives there.
 *
 * THE THREE BANDS (APP-BUILDER-UX §2.2, the part that survived the re-scope):
 *   1. what this is      — the name and the one-line claim
 *   2. who is minding it — the resident, named
 *   3. the work          — the declared sections, beside the conversation
 */

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { api, type Run, type StandingStart, type StandingSummary } from '@/lib/api/client';
import {
  SupervisorSection,
  type RunsBand,
  type SupervisorStateData,
  type WorkBand,
} from '@/components/supervisor/SupervisorSection';
import { useRuns } from '@/lib/runs/useRuns';
import { MinderBand } from '@/components/supervisor/MinderBand';
import { BrowserGate } from '@/components/supervisor/BrowserGate';
import { Conversation } from '@/components/supervisor/Conversation';
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
 * ⭐ Ordered by what a member supervising asks first (ADR-666 D8): what is
 * happening, what needs them, what they have, what just happened.
 */
/** ADR-660 — the declaration holds catalog KEYS: this table is evaluated at
 *  import, before any member's language is known. The title is worded at
 *  render, so the DECLARED shape is unchanged. */
const SECTIONS: Array<{ kind: string; titleKey: string }> = [
  { kind: 'running', titleKey: 'sectionRunning' },
  { kind: 'needs-you', titleKey: 'sectionNeedsYou' },
  { kind: 'work', titleKey: 'sectionWork' },
  { kind: 'recent', titleKey: 'sectionRecent' },
];

export function SupervisorSurface() {
  const t = useTranslations('supervisor');
  const [data, setData] = useState<SupervisorStateData | null>(null);
  const [failed, setFailed] = useState(false);
  const [rows, setRows] = useState<StandingSummary[] | null>(null);
  const [rosterFailed, setRosterFailed] = useState(false);
  const [starts, setStarts] = useState<StandingStart[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const { navigateToSurface, userId } = useSurfacePreferences();
  const { runAction } = useFeedback();
  const { runs, failed: runsFailed, refresh: refreshRuns } = useRuns();
  const param = useSurfaceParam('supervisor');
  // The detail (ADR-658 D6) is a deep-linkable pane param, like every other
  // surface's: `?supervisor.work=<topic>`.
  const openTopic = param.get('work');

  const loadRoster = useCallback(async () => {
    try {
      const list = await api.standing.list();
      setRows(list);
      setRosterFailed(false);
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
        });
      },
      () => { if (!cancelled) setFailed(true); },
    );
    api.standing.list().then(
      (list) => {
        if (cancelled) return;
        setRows(list);
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
    // ADR-666 D4 — browser work runs in its own conversation, which lives in
    // its detail: the detail is the ONE door that starts it.
    if (row.browser) {
      param.set({ work: row.topic, start: row.browser.member === userId ? '1' : null });
      return;
    }
    setBusy(row.topic);
    try {
      const res = await runAction(() => api.standing.run(row.topic), {
        pending: t('action.runningPending', { topic: row.topic }),
      });
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
  }, [busy, loadRoster, param, runAction, t, userId]);

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
    busy,
    notes,
    viewerId: userId ?? null,
    onRunNow: runNow,
    onTogglePause: togglePause,
    onOpen: (row) => param.set({ work: row.topic }),
  };

  const runsBand: RunsBand = {
    runs,
    failed: runsFailed,
    viewerId: userId ?? null,
    onOpen: (run: Run) => { if (run.topic) param.set({ work: run.topic }); },
    onRunIt: (run: Run) => { if (run.topic) param.set({ work: run.topic, start: '1' }); },
    onOpenFile: (path: string) => navigateToSurface('files', { path }),
    onChanged: () => { void refreshRuns(); void loadRoster(); },
  };
  // ADR-667 D1 — the conversation opens on what this workspace can set up:
  // one suggestion per start the server derives, worded here so it speaks the
  // member's language (a start's served title does not).
  const suggestions = starts.map((st) =>
    st.kind === 'connector' ? t('conversation.suggestConnector', { name: st.name })
      : st.kind === 'browser' ? t('conversation.suggestBrowser')
      : st.kind === 'path' ? t('conversation.suggestPath')
      : t('conversation.suggestUrl'));

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
  const state: SupervisorStateData | null = data ?? (failed ? { needs_you: [] } : null);

  return (
    <div className="flex h-full flex-col overflow-y-auto lg:overflow-hidden">
      {/* Band 1 — the visible claim, and the door beside it.
          ⭐ The door was reachable ONLY from inside the work band, so it moved
          as the band's contents changed and vanished entirely while the roster
          read was out. The primary verb of a cockpit belongs in a fixed place;
          it is hidden on an opened detail, where the verbs are that piece of
          work's own. */}
      <header className="flex items-start justify-between gap-4 border-b border-border/60 px-5 py-4">
        <div className="min-w-0">
          <h1 className="text-[15px] font-semibold text-foreground">{t('surface.title')}</h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {t('surface.claim')}
          </p>
        </div>
      </header>

      {/* Band 2 — who is minding it, in its three ruled states (§4.1). It was a
          CONSTANT; a band that cannot change cannot be trusted. Derived from
          the roster this surface already holds — no fourth read. */}
      <MinderBand
        rows={rows}
        runs={runs}
        viewerId={userId ?? null}
        busyTopic={busy}
        onOpen={(topic) => param.set({ work: topic })}
        onRunIt={runsBand.onRunIt}
      />


      {/* Band 3 — one piece of work opened (D6), or the declared sections
          beside the Supervisor's conversation (ADR-667 D1). On a narrow
          screen the conversation comes first: it is where work begins. */}
      {openTopic ? (
        <div className="flex-1">
          <StandingDetail
            topic={openTopic}
            onBack={() => param.set({ work: null })}
            onChanged={() => void loadRoster()}
          />
        </div>
      ) : (
        <div className="flex flex-1 flex-col lg:min-h-0 lg:flex-row">
          <aside className="px-5 pt-4 lg:order-last lg:flex lg:w-[440px] lg:shrink-0 lg:flex-col lg:border-l lg:border-border/60 lg:p-4">
            <BrowserGate>
              <Conversation
                app="supervisor"
                suggestions={suggestions}
                emptyState={
                  <div className="space-y-1 text-center">
                    <p className="text-[13px] font-medium text-foreground">{t('conversation.emptyTitle')}</p>
                    <p className="text-xs text-muted-foreground">{t('conversation.emptyBody')}</p>
                  </div>
                }
                className="h-[520px] lg:h-full"
              />
            </BrowserGate>
          </aside>
          <div className="flex-1 space-y-5 px-5 py-4 lg:overflow-y-auto">
            {SECTIONS.map((section) => (
              <SupervisorSection
                key={section.kind}
                section={{ kind: section.kind, title: t(`surface.${section.titleKey}`) }}
                data={state}
                work={work}
                runs={runsBand}
                onOpenLane={openLane}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
