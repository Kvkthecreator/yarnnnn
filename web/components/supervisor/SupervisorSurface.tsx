'use client';

/**
 * SupervisorSurface — the Supervisor app's pane (ADR-656 §7 → ADR-658 →
 * ADR-670 D6).
 *
 * THE FIRST COMPOSED SURFACE IN YARNNN: its shape is DECLARED (the sections
 * below) rather than mirrored from one substrate concern. That is the register
 * ADR-435 declined to name and ADR-653 D3.a promoted, and this is its first
 * tenant.
 *
 * ⭐ WHAT IT IS FOR (ADR-658 §11 → ADR-667): where a member sets up, sees and
 * manages the work that keeps happening. Work is SET UP IN CONVERSATION — the
 * Supervisor's own agent (ADR-667 D1) — and the browser is the prerequisite for
 * setting up and running it, never for seeing it (`BrowserGate`, D4). Files
 * shows files, Reach shows connections, Chat shows one conversation,
 * Notifications shows what already happened — nothing else shows the work
 * itself, which is why this is not the glorified redirect ADR-435 deleted the
 * last composition for being.
 *
 * THE THREE BANDS (APP-BUILDER-UX §2.2):
 *   1. what this is      — the name and the one-line claim (and the frame's doors)
 *   2. who is minding it — the resident, named (`MinderBand`)
 *   3. the work          — THE FRAME (ADR-670 D2): index · object · supervision
 *
 * ⭐ BAND 3 IS PANES' OWN MODEL, and ONE drill grammar (ADR-670 D6):
 *
 *   | level                        | rail (index)       | canvas (object)            | side (supervision)          |
 *   | index                        | Needs you + work   | the setup conversation     | running now · recently      |
 *   | `?supervisor.work=<topic>`   | unchanged          | that work                  | its verbs · sources · runs  |
 *   | `?supervisor.run=<id>`       | unchanged          | the run in full (Trace)    | unchanged                   |
 *
 * `rail` and `side` are chrome through `usePaneSlot`; the canvas never yields;
 * the ladder folds them (PANES §2) — the side becomes an overlay at two-pane,
 * and at single-pane the three are tabs of one screen. There is no `lg:`/`md:`
 * here: the surface measures its own container. Each level's crumb is set with
 * `useWindowCrumb`, so the locator strip is the spine and there is no back bar.
 *
 * ⚠️ ONE READER PER LEDGER, AND ONE RENDERING PER THING. The roster is
 * `api.standing.list` (the route the Notifications mirror reads); the runs are
 * `useRuns`; what waits on the member is `useNeedsYou` (ADR-670 D5) through the
 * strip every index mounts. The reads land independently — one unreadable band
 * never blanks the surface. A thing shows once per screen: a waiting run is in
 * Needs you (live, so never in recently), the run open in the canvas is left out
 * of every list beside it, and an opened work's runs replace the workspace's.
 */

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { PanelLeft, PanelRight } from 'lucide-react';
import { api, type Run, type StandingStart, type StandingSummary } from '@/lib/api/client';
import {
  SupervisorSection,
  sectionSlot,
  type RunsBand,
  type WorkBand,
} from '@/components/supervisor/SupervisorSection';
import { useRuns } from '@/lib/runs/useRuns';
import { useOpenRun } from '@/lib/runs/openRun';
import { MinderBand } from '@/components/supervisor/MinderBand';
import { BrowserGate } from '@/components/supervisor/BrowserGate';
import { Conversation } from '@/components/supervisor/Conversation';
import { RunTrace } from '@/components/supervisor/RunTrace';
import {
  StandingDetailCanvas,
  StandingDetailSide,
  useStandingDetail,
} from '@/components/supervisor/StandingDetail';
import { NeedsYouStrip } from '@/components/chat-surface/ChatIndexStrips';
import { useWindowCrumb } from '@/contexts/BreadcrumbContext';
import { slotIsColumn, usePaneLadder, usePaneSlot } from '@/lib/shell/pane-layout';
import { useSurfaceParam, useSurfacePreferences } from '@/lib/shell/useSurfacePreferences';
import { cn } from '@/lib/utils';

/**
 * The app's declared sections.
 *
 * ⚠️ DECLARED, not hardcoded rendering: the surface renders whatever this list
 * says, through the dispatch — which is the whole difference between a composed
 * surface and a bespoke one. A kind this client cannot draw renders the honest
 * amber miss rather than a blank. Which slot of the frame a kind lands in is
 * the kind's own (`sectionSlot`), never a prop of the declaration.
 *
 * ⭐ Ordered by what a member supervising asks first (ADR-666 D8): what is
 * happening, what they have, what just happened. *What needs them* is the one
 * needs-you strip (ADR-670 D5), not a section of this app's own.
 */
/** ADR-660 — the declaration holds catalog KEYS: this table is evaluated at
 *  import, before any member's language is known. The title is worded at
 *  render, so the DECLARED shape is unchanged. */
const SECTIONS: Array<{ kind: string; titleKey: string }> = [
  { kind: 'running', titleKey: 'sectionRunning' },
  { kind: 'work', titleKey: 'sectionWork' },
  { kind: 'recent', titleKey: 'sectionRecent' },
];

type NarrowPane = 'index' | 'object' | 'side';

/** The single-pane tab bar: CATALOG KEYS, worded at render. The object tab is
 *  named for what the canvas holds at this level. */
const OBJECT_TAB_KEY = { index: 'frame.tabSetup', work: 'frame.tabWork', run: 'frame.tabRun' } as const;

export function SupervisorSurface() {
  const t = useTranslations('supervisor');
  const [rows, setRows] = useState<StandingSummary[] | null>(null);
  const [rosterFailed, setRosterFailed] = useState(false);
  const [starts, setStarts] = useState<StandingStart[]>([]);
  const { navigateToSurface, userId } = useSurfacePreferences();
  const { runs, failed: runsFailed, refresh: refreshRuns } = useRuns();
  const openRun = useOpenRun();
  const param = useSurfaceParam('supervisor');
  // The drill grammar's two deeper levels (ADR-670 D6), each one deep-linkable
  // param: the OBJECT (`?supervisor.work=<topic>`) and the TRACE
  // (`?supervisor.run=<id>`).
  const openTopic = param.get('work');
  const runId = param.get('run');

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

  // ⚠️ THE READS LAND EACH ON THEIR OWN (driven 2026-09-19): awaited together,
  // one slow read held every band behind one spinner.
  useEffect(() => {
    let cancelled = false;
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

  // The opened work's ONE state, shared by its two halves (canvas and side).
  const work = useStandingDetail({
    topic: openTopic,
    starts,
    onChanged: () => void loadRoster(),
    onRetired: () => param.set({ work: null, run: null }),
  });

  // ── The frame (ADR-670 D2) — PANES' model, the shell's ladder ────────────
  const [setPaneNode, wb] = usePaneLadder();
  const rail = usePaneSlot('supervisor', 'rail', userId, wb, { defaultShown: true });
  // The side rests shown where it is a COLUMN and withdrawn where it would be
  // an OVERLAY — an overlay covers the canvas (PANES §5's moving default).
  const side = usePaneSlot('supervisor', 'side', userId, wb, { defaultShown: !wb.sideIsOverlay });
  const single = wb.singlePane;
  const railIsColumn = !single && rail.shown;
  const sideIsColumn = slotIsColumn(wb, side);
  const [narrowPane, setNarrowPane] = useState<NarrowPane>('object');
  // Opening a level shows it: on one screen, choosing a work or a run from the
  // index or the side lands on the thing chosen.
  useEffect(() => {
    setNarrowPane('object');
  }, [openTopic, runId]);

  // Escape withdraws the side while it is an OVERLAY (it covers the canvas, so
  // it is modal); a column is not, and Escape must not reach across and close it.
  useEffect(() => {
    if (!wb.sideIsOverlay || !side.shown) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') side.toggle();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [wb.sideIsOverlay, side]);

  // ── The crumb is the spine (ADR-670 D6) ──────────────────────────────────
  // The root crumb returns to the index (the strip fires the LEAF's act from
  // its root, and on a phone the leaf is the back-chip); a middle crumb returns
  // to its own level.
  const toIndex = () => param.set({ work: null, run: null, start: null });
  const workLabel = openTopic
    ? work.detail?.summary.target || rows?.find((r) => r.topic === openTopic)?.target || openTopic
    : null;
  useWindowCrumb('supervisor', [
    ...(workLabel
      ? [{ label: workLabel, onClick: runId ? () => param.set({ run: null }) : toIndex }]
      : []),
    ...(runId ? [{ label: t('frame.run'), onClick: toIndex }] : []),
  ]);

  const workBand: WorkBand = {
    rows,
    failed: rosterFailed,
    viewerId: userId ?? null,
    runs,
    openTopic,
    onOpen: (row) => param.set({ work: row.topic, run: null }),
  };

  const runsBand: RunsBand = {
    runs,
    failed: runsFailed,
    viewerId: userId ?? null,
    exceptRunId: runId,
    onOpen: (run: Run) => openRun(run),
    onRunIt: (run: Run) => openRun(run, { start: true }),
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

  // Worded here, never inline (the ADR-660 meter reads a JSX ternary as copy).
  const railDoorLabel = rail.shown ? t('frame.hideIndex') : t('frame.showIndex');
  const sideDoorLabel = side.shown ? t('frame.hideSide') : t('frame.showSide');
  const level = runId ? 'run' : openTopic ? 'work' : 'index';
  const tabs: Array<[NarrowPane, string]> = [
    ['index', t('frame.tabIndex')],
    ['object', t(OBJECT_TAB_KEY[level])],
    ['side', t('frame.tabSide')],
  ];
  const shows = (pane: NarrowPane) => !single || narrowPane === pane;

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Band 1 — the visible claim, and the frame's doors. A hidden slot must
          have a reachable door (PANES §3): both live here, outside the slots
          they hide, at every rung where the slot is a column or an overlay —
          and not at single-pane, where the bottom tab bar is the switcher. */}
      <header className="flex shrink-0 items-start justify-between gap-4 border-b border-border/60 px-5 py-4">
        <div className="min-w-0">
          <h1 className="text-[15px] font-semibold text-foreground">{t('surface.title')}</h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            {t('surface.claim')}
          </p>
        </div>
        {!single && (
          <div className="flex shrink-0 items-center gap-0.5">
            <button
              type="button"
              onClick={rail.toggle}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title={railDoorLabel}
              aria-label={railDoorLabel}
              aria-expanded={rail.shown}
            >
              <PanelLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={side.toggle}
              className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title={sideDoorLabel}
              aria-label={sideDoorLabel}
              aria-expanded={side.shown}
            >
              <PanelRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </header>

      {/* Band 2 — who is minding it, in its three ruled states (§4.1). Derived
          from the roster and the ledger this surface already holds. */}
      <MinderBand
        rows={rows}
        runs={runs}
        viewerId={userId ?? null}
        busyTopic={work.runningNow ? openTopic : null}
        onOpen={(topic) => param.set({ work: topic, run: null })}
        onRunIt={runsBand.onRunIt}
      />

      {/* Band 3 — the frame. */}
      <div ref={setPaneNode} className="relative flex min-h-0 flex-1">
        {/* RAIL — the index: what needs you (the one strip, ADR-670 D5) and
            the roster of work. Never the place a thing is read in full. */}
        {(single ? narrowPane === 'index' : rail.shown) && (
          <nav
            style={railIsColumn ? { width: rail.width } : undefined}
            aria-label={t('frame.tabIndex')}
            className={cn(
              'flex min-h-0 flex-col overflow-y-auto',
              single ? 'min-w-0 flex-1' : 'shrink-0 border-r border-border/60',
            )}
          >
            <NeedsYouStrip onOpenLane={(laneId) => navigateToSurface('chat', { lane: laneId })} />
            <div className="space-y-5 px-3 py-3">
              {SECTIONS.filter((s) => sectionSlot(s.kind) === 'rail').map((section) => (
                <SupervisorSection
                  key={section.kind}
                  section={{ kind: section.kind, title: t(`surface.${section.titleKey}`) }}
                  work={workBand}
                  runs={runsBand}
                />
              ))}
            </div>
          </nav>
        )}
        {railIsColumn && (
          <div
            onPointerDown={rail.startResize}
            role="separator"
            aria-orientation="vertical"
            className="w-1 shrink-0 cursor-col-resize bg-transparent transition-colors hover:bg-primary/20 active:bg-primary/30"
          />
        )}

        {/* CANVAS — the object; it never yields. Kept MOUNTED behind the other
            tabs at single-pane, so a conversation's streaming turn survives a
            look at the index. */}
        <div
          className={cn(
            'min-h-0 min-w-0 flex-1 flex-col overflow-y-auto px-5 py-4',
            shows('object') ? 'flex' : 'hidden',
          )}
        >
          {runId ? (
            <RunTrace runId={runId} known={work.runs} />
          ) : openTopic ? (
            <StandingDetailCanvas work={work} />
          ) : (
            <BrowserGate>
              <Conversation
                app="supervisor"
                // The agent sets work up and retires it here (ADR-667 D1):
                // the roster and the runs re-read when its turn settles, or
                // the index beside it shows work that no longer exists.
                onTurnSettled={() => { void loadRoster(); void refreshRuns(); }}
                suggestions={suggestions}
                emptyState={
                  <div className="space-y-1 text-center">
                    <p className="text-[13px] font-medium text-foreground">{t('conversation.emptyTitle')}</p>
                    <p className="text-xs text-muted-foreground">{t('conversation.emptyBody')}</p>
                  </div>
                }
                className="min-h-[420px] flex-1"
              />
            </BrowserGate>
          )}
        </div>

        {/* SIDE — the supervision: a COLUMN at the three-column rungs, an
            OVERLAY at two-pane (a scrim, Escape and the door dismiss it), a
            full pane behind the bottom tab at single-pane. */}
        {wb.sideIsOverlay && side.shown && (
          <div role="presentation" onClick={side.toggle} className="absolute inset-0 z-20 bg-black/20" />
        )}
        {sideIsColumn && (
          <div
            onPointerDown={side.startResize}
            role="separator"
            aria-orientation="vertical"
            className="w-1 shrink-0 cursor-col-resize bg-transparent transition-colors hover:bg-primary/20 active:bg-primary/30"
          />
        )}
        {(single ? narrowPane === 'side' : side.shown) && (
          <aside
            style={sideIsColumn ? { width: side.width } : undefined}
            aria-label={t('frame.tabSide')}
            className={cn(
              'flex min-h-0 flex-col overflow-y-auto bg-background px-4 py-4',
              single
                ? 'min-w-0 flex-1'
                : wb.sideIsOverlay
                  ? 'absolute inset-y-0 right-0 z-30 w-[min(24rem,85%)] border-l border-border shadow-xl'
                  : 'shrink-0 border-l border-border/60',
            )}
          >
            {openTopic ? (
              <StandingDetailSide work={work} exceptRunId={runId} />
            ) : (
              <div className="space-y-5">
                {SECTIONS.filter((s) => sectionSlot(s.kind) === 'side').map((section) => (
                  <SupervisorSection
                    key={section.kind}
                    section={{ kind: section.kind, title: t(`surface.${section.titleKey}`) }}
                    work={workBand}
                    runs={runsBand}
                  />
                ))}
              </div>
            )}
          </aside>
        )}
      </div>

      {/* Single-pane: one screen, three tabs (PANES §2's last rung). */}
      {single && (
        <nav className="flex shrink-0 border-t border-border">
          {tabs.map(([pane, label]) => (
            <button
              key={pane}
              type="button"
              aria-current={narrowPane === pane ? 'page' : undefined}
              onClick={() => setNarrowPane(pane)}
              className={cn(
                'min-h-[44px] flex-1 py-2 text-xs font-medium transition-colors',
                narrowPane === pane
                  ? 'border-t-2 border-foreground text-foreground'
                  : 'border-t-2 border-transparent text-muted-foreground',
              )}
            >
              {label}
            </button>
          ))}
        </nav>
      )}
    </div>
  );
}
