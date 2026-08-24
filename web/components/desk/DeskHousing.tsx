'use client';

/**
 * DeskHousing — the shared desk chrome (ADR-569 D6, the ADR-518 housing move).
 *
 * A desk app (Radar's watched folder, Strings' maintained file) is a rail of
 * subjects · a center lifecycle pane · a bound colleague lane, on the
 * authoring width ladder. The chrome is identical across desks; only the
 * vocabulary and the center's content differ — so the chrome extracts into
 * ONE parameterized component with an app door per desk (`StudioSurface`'s
 * move, ADR-518), and folding two desks into one later stays a door change
 * (ADR-565 D8 held open, deliberately cheap).
 *
 * What the housing owns:
 *   - the pane container + `usePaneLadder` (docs/design/PANES.md — width rides
 *     the desk's own container, never the viewport):
 *       full/condensed → three columns;
 *       two-pane       → the rail folds (the app renders a header switcher);
 *       single-pane    → one pane + a Desk/{colleague} tab bar;
 *   - the bound lane: find-or-create keyed on `artifact_path` with the app's
 *     own slug (`create_lane(app=…)` — the resident resolves SERVER-side from
 *     the app's registration, ADR-562 D3; `lane_meta.app` selects the desk
 *     posture, ADR-567 D4), mounted through `LanePanel`'s named
 *     `LaneMountSlots` only — never a forked panel;
 *   - WHO the member reads (ADR-562 D5): the app's name for its resident,
 *     else the colleague's own name, else the engine label — read back from
 *     the wire, never asserted here;
 *   - the refine-in-chat seed mechanism (jumps to the lane pane on phones).
 *
 * What stays in each desk app: the subject param + state machine, the rail's
 * rows, the center pane's sections, the attach gesture, and every operator
 * word. The housing renders structure; the app renders meaning.
 */

import {
  useCallback, useEffect, useMemo, useState, type ReactNode,
} from 'react';
import { Loader2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { usePaneLadder } from '@/lib/shell/pane-layout';
import { LanePanel } from '@/components/chat-surface/LanePanel';

// Lane env shapes come from the client, never hand-copied (the drift seam
// the 567 first cut reopened).
type LanesEnv = Awaited<ReturnType<typeof api.lanes.list>>;
type LaneRow = LanesEnv['lanes'][number];

/** What the housing hands its render slots. */
export interface DeskContext {
  /** The workbench-width ladder read on the desk's own container. */
  wb: ReturnType<typeof usePaneLadder>[1];
  /** Three-column rung → the rail renders as its own column; below it the
   *  app folds the roster into a header switcher. */
  showRailColumn: boolean;
  /** null = not yet known; false = lanes off for this workspace. */
  lanesEnabled: boolean | null;
  /** Seed the colleague's composer (jumps to the lane pane on phones). */
  seedChat: (text: string) => void;
  /** single-pane only: which pane the tab bar shows. */
  setActivePane: (pane: 'desk' | 'lane') => void;
}

export interface DeskHousingProps {
  /** The app slug the lane binds under (`create_lane(app=…)`) — also the
   *  ADR-562 D5 speaker-label lookup key. */
  app: string;
  /** The selected subject (the desk's identity param), or null for the
   *  front door. */
  subject: string | null;
  /** The bound artifact leaf for the current subject (`{root}/report.md`,
   *  `{folder}/{target-leaf}`), or null when no subject. */
  artifactPath: string | null;
  /** Gate for lane creation: false while the desk's state is still unknown
   *  (idle/loading), so a lane is never created for a subject that may not
   *  resolve. */
  laneReady: boolean;
  /** The lane's display name for a fresh create ("Watch: {topic}"). */
  laneName: string;
  /** The colleague's tab label on the single-pane rung ("Researcher"). */
  laneTabLabel: string;
  /** Starter chips while the lane transcript is empty. */
  suggestions: string[];
  /** The lane's empty-state teaching, in the desk's own words. */
  laneEmptyState: ReactNode;
  /** Shown when the lane could not be opened. */
  laneFallbackLabel: string;
  /** A lane write landed — re-read everything the desk projects. */
  onLaneWrite?: (path: string) => void;
  /** The rail column (three-column rung only — fold is the app's concern). */
  renderRail: (ctx: DeskContext) => ReactNode;
  /** The center pane when no subject is selected (renders its own <main>). */
  renderFrontDoor: (ctx: DeskContext) => ReactNode;
  /** The center pane's content for the selected subject. */
  children: (ctx: DeskContext) => ReactNode;
  /** Always-mounted extras (portal-based modals — the attach gesture). */
  overlay?: (ctx: DeskContext) => ReactNode;
}

export function DeskHousing({
  app,
  subject,
  artifactPath,
  laneReady,
  laneName,
  laneTabLabel,
  suggestions,
  laneEmptyState,
  laneFallbackLabel,
  onLaneWrite,
  renderRail,
  renderFrontDoor,
  children,
  overlay,
}: DeskHousingProps) {
  const [setWorkbenchNode, wb] = usePaneLadder();

  // single-pane: which pane the tab bar shows. Switching subject lands on the
  // desk pane (the selectTopic behavior, hoisted with the chrome).
  const [activePane, setActivePane] = useState<'desk' | 'lane'>('desk');
  useEffect(() => {
    setActivePane('desk');
  }, [subject]);
  // Composer seed for the refine-in-chat gestures (LaneMountSlots contract).
  const [seed, setSeed] = useState<{ text: string; nonce: number } | null>(null);

  // ── The bound lane (find-or-create; the binding contract is ADR-567 D4:
  //    create_lane(app={app}, artifact_path={subject's leaf})) ──────────────
  const [lanesEnabled, setLanesEnabled] = useState<boolean | null>(null);
  const [lanes, setLanes] = useState<LaneRow[]>([]);
  const [agents, setAgents] = useState<LanesEnv['agents']>([]);
  const [apps, setApps] = useState<NonNullable<LanesEnv['apps']>>([]);
  // ADR-602 — the BEINGS roster. `agents` is the HIRE roster (empty since
  // ADR-599), so a resident's name was never found there and this housing
  // addressed the ENGINE instead of Keeper/Editor.
  const [beings, setBeings] = useState<NonNullable<LanesEnv['beings']>>([]);
  const [models, setModels] = useState<LanesEnv['models']>([]);
  // The NAMING table (every engine, retired included). `models` is the CHOOSER
  // and drops retired rows, so a bound lane pinned to one would name itself by
  // its RAW ID (ADR-559 D2 — one dict, two audiences).
  const [modelNames, setModelNames] = useState<Record<string, string>>({});

  const refreshLanes = useCallback(async () => {
    try {
      const res = await api.lanes.list(true);
      setLanesEnabled(res.enabled);
      setLanes(res.lanes);
      setAgents(res.agents ?? []);
      setApps(res.apps ?? []);
      setBeings(res.beings ?? []);
      setModels(res.models ?? []);
      setModelNames(res.model_names ?? {});
    } catch {
      setLanesEnabled(false);
    }
  }, []);

  useEffect(() => {
    void refreshLanes();
  }, [refreshLanes]);

  const boundLane = useMemo(() => {
    if (!artifactPath) return null;
    return (
      lanes.find((l) => l.status === 'active' && l.artifact_path === artifactPath) ??
      null
    );
  }, [lanes, artifactPath]);

  const [creatingLane, setCreatingLane] = useState(false);
  useEffect(() => {
    if (!artifactPath || !subject || !lanesEnabled || boundLane || creatingLane) return;
    if (!laneReady) return;
    setCreatingLane(true);
    api.lanes
      .create({
        name: laneName.slice(0, 60),
        // ADR-562 D3/ADR-567 D4 — the surface names WHICH APP is asking; the
        // resident resolves server-side from the app's own registration, and
        // lane_meta.app selects the desk posture.
        app,
        artifact_path: artifactPath,
      })
      .then(() => refreshLanes())
      .catch(() => { /* the lane column states why below */ })
      .finally(() => setCreatingLane(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifactPath, subject, lanesEnabled, boundLane, laneReady]);

  const modelLabel = useMemo(() => {
    if (!boundLane) return '';
    return (
      modelNames[boundLane.model] ??
      models.find((m) => m.id === boundLane.model)?.label ??
      boundLane.model
    );
  }, [boundLane, models, modelNames]);

  // ADR-562 D5 — WHO the member reads: the app's name for its resident
  // (served from the app's own registration), else the colleague's own name,
  // else the engine label. Read back from the wire, never asserted here.
  const speakerLabel = useMemo(() => {
    // ADR-602 D7 — this housing KNOWS which app it is (the `app` prop), which
    // is a stronger fact than a lane stamp that may predate ADR-567.
    const slug = apps.find((a) => a.slug === app)?.resident || boundLane?.agent;
    if (slug) {
      const appName = apps.find((a) => a.slug === app)?.name;
      if (appName) return appName;
      const being = beings.find((b) => b.slug === slug)?.name;
      if (being) return being;
      const named = agents.find((a) => a.slug === slug)?.name;
      if (named) return named;
    }
    return modelLabel;
  }, [agents, apps, beings, boundLane, modelLabel, app]);

  const seedChat = useCallback((text: string) => {
    setSeed({ text, nonce: Date.now() });
    if (wb.singlePane) setActivePane('lane');
  }, [wb.singlePane]);

  // ── Layout flags ────────────────────────────────────────────────────────
  const showRailColumn = wb.threeColumn;
  const laneAvailable = !!subject && lanesEnabled === true;
  const showLaneColumn = laneAvailable && (!wb.singlePane || activePane === 'lane');
  const laneWidthClass = wb.fullLabels ? 'w-[400px]' : 'w-[360px]';

  const ctx: DeskContext = {
    wb,
    showRailColumn,
    lanesEnabled,
    seedChat,
    setActivePane,
  };

  // ── Render ──────────────────────────────────────────────────────────────
  return (
    <div
      ref={setWorkbenchNode}
      className="flex h-full min-h-0 flex-col bg-background text-foreground"
    >
      <div className="flex min-h-0 flex-1">
        {showRailColumn && renderRail(ctx)}

        {subject ? (
          <>
            {(!wb.singlePane || activePane === 'desk') && (
              <main className="min-h-0 min-w-0 flex-1 overflow-y-auto">
                {children(ctx)}
              </main>
            )}

            {/* ── The colleague — the lane the lifecycle runs through ── */}
            {showLaneColumn && (
              <aside
                className={`flex ${wb.singlePane ? 'min-w-0 flex-1' : `${laneWidthClass} shrink-0 border-l`} flex-col`}
              >
                {boundLane ? (
                  <LanePanel
                    key={boundLane.id}
                    laneId={boundLane.id}
                    laneName={boundLane.name}
                    modelLabel={modelLabel}
                    speakerLabel={speakerLabel}
                    onArtifactWrite={onLaneWrite}
                    artifactWrite="link"
                    composerSeed={seed}
                    suggestions={suggestions}
                    emptyState={laneEmptyState}
                  />
                ) : (
                  <div className="flex h-full items-center justify-center p-6 text-center text-xs text-muted-foreground">
                    {creatingLane || !laneReady
                      ? <Loader2 className="h-4 w-4 animate-spin" />
                      : laneFallbackLabel}
                  </div>
                )}
              </aside>
            )}
          </>
        ) : (
          renderFrontDoor(ctx)
        )}
      </div>

      {/* ── single-pane: the Desk/{colleague} tab bar ── */}
      {wb.singlePane && subject && lanesEnabled && (
        <nav className="flex shrink-0 border-t">
          {([['desk', 'Desk'], ['lane', laneTabLabel]] as const).map(([pane, label]) => (
            <button
              key={pane}
              type="button"
              onClick={() => setActivePane(pane)}
              className={`flex-1 py-2.5 text-center text-xs font-medium ${
                activePane === pane
                  ? 'border-t-2 border-foreground text-foreground'
                  : 'text-muted-foreground'
              }`}
            >
              {label}
            </button>
          ))}
        </nav>
      )}

      {overlay?.(ctx)}
    </div>
  );
}
