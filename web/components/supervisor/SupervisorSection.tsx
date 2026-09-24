'use client';

/**
 * SupervisorSection — the component vocabulary, dispatched by kind (ADR-656 §7
 * → ADR-658 D5).
 *
 * ⭐ THE DATA-DRIVEN RENDERING PATH. YARNNN had exactly one — a string-`kind` →
 * component table with an honest amber miss — and it died as COLLATERAL in
 * `e18e178`, six weeks after ADR-435 explicitly preserved it, by no ruling of
 * its own (ADR-653 §1.3). This is that path, rebuilt for the surface that needs
 * it: one whose shape is DECLARED rather than mirrored.
 *
 * ⚠️ THE VOCABULARY IS DERIVED FROM WHAT A MEMBER ASKS, not from what the
 * system has lying around (ADR-658 §2). A member supervising asks, in order,
 * *what is happening, what needs me, what do I have, what just happened* — so
 * the cockpit reads by RUN STATE (ADR-666 D8):
 *
 *   running    what is happening now        runs: queued · running
 *   needs-you  what is waiting on me        runs due on me, recent failures, mentions
 *   work       what standing work I have    the roster (ADR-658)
 *   recent     what just happened           runs: done · failed · stopped
 *
 *   note    — DELETED (ADR-666 D8): `DECISIONS.md` had no writer and no
 *             workspace held one; the band rendered its empty forever.
 *   threads — DELETED (ADR-658 §2): a list of conversations answered nothing.
 *
 * `running` and `recent` read the run ledger through ONE store (`useRuns`);
 * they are not the timeline — the timeline is every act, these are the work.
 *
 * ⭐ `work` satisfies the growth rule rather than bypassing it: no existing
 * kind shows the work that runs on its own, and nothing else in the product
 * lets a member create it by direct manipulation. `running` / `recent` satisfy
 * it the same way: nothing else shows a run while it happens.
 *
 * ⚠️ NO LAYOUT PROPS, EVER. A section declares `kind` and `title`. The moment
 * one takes `columns` or `align` this is a page builder — the feature race the
 * app-seam analysis says we lose.
 */

import { useTranslations } from 'next-intl';
import { AlertTriangle, MessageSquare } from 'lucide-react';
import { RunView } from '@/components/runs/RunView';
import { StandingRow } from '@/components/standing/StandingRow';
import { isLiveRun, type Run, type StandingSummary } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';

export interface SupervisorNeed {
  lane_id: string;
  title: string;
  excerpt: string;
  at?: string | null;
}

export interface SupervisorStateData {
  needs_you: SupervisorNeed[];
}

/**
 * The run bands' material and verbs (ADR-666 D8) — the ledger read from its
 * ONE store (`useRuns`). The verbs start (through the detail's one door),
 * open, and — inside `RunView` — stop.
 */
export interface RunsBand {
  /** null = not read yet (or unreadable — `failed` says which). */
  runs: Run[] | null;
  failed: boolean;
  viewerId: string | null;
  onOpen: (run: Run) => void;
  onRunIt: (run: Run) => void;
  onOpenFile: (path: string) => void;
  onChanged: () => void;
}

/** How long a failed run of declared work stays in needs-you. */
const FAILURE_WINDOW_MS = 3 * 24 * 3600 * 1000;
/** How many ended runs `recent` shows. */
const RECENT_CAP = 8;

/**
 * Which runs need the member — derived, never stored (DP29), ADR-667 D6:
 *   - every run WAITING ON THE VIEWER (due browser work waits for its own
 *     member; another member's due run is theirs — the tray's rule, one
 *     predicate for both),
 *   - the newest ended run of a piece of declared work, when it FAILED within
 *     the window — a failure is the WORK's, so every member sees it; the
 *     newest only, so a failure a later run fixed is gone.
 */
export function runsNeedingYou(runs: Run[], viewerId: string | null): Run[] {
  const waiting = runs.filter((r) => r.state === 'waiting' && r.user_id === viewerId);
  const newestEnded = new Map<string, Run>();
  for (const r of runs) {
    if (!r.topic || isLiveRun(r)) continue;
    if (!newestEnded.has(r.topic)) newestEnded.set(r.topic, r);
  }
  const now = Date.now();
  const failures = Array.from(newestEnded.values()).filter(
    (r) => r.state === 'failed'
      && now - new Date(r.ended_at ?? r.started_at ?? 0).getTime() < FAILURE_WINDOW_MS,
  );
  return [...waiting, ...failures];
}

/**
 * The `work` band's material and verbs — the standing roster read from its
 * ONE route (`api.standing.list`). The verbs act on DECLARATIONS (pause · run ·
 * open), never on beings; creating one is the conversation's (ADR-667 D1).
 */
export interface WorkBand {
  /** null = not read yet (or unreadable — `failed` says which). */
  rows: StandingSummary[] | null;
  failed: boolean;
  busy: string | null;
  notes: Record<string, string>;
  viewerId: string | null;
  onRunNow: (row: StandingSummary) => void;
  onTogglePause: (row: StandingSummary) => void;
  onOpen: (row: StandingSummary) => void;
}

/** The kinds this client can draw. */
export const SUPERVISOR_SECTION_KINDS = ['running', 'needs-you', 'work', 'recent'] as const;
export type SupervisorSectionKind = (typeof SUPERVISOR_SECTION_KINDS)[number];

export interface SupervisorSectionDecl {
  kind: string;
  title?: string;
}

/**
 * The honest miss — the amber box `dispatchComponent` used to render.
 *
 * ⭐ Silence is the failure mode it prevents. A section we cannot draw must SAY
 * so: a blank band is indistinguishable from a band with nothing in it, and a
 * member cannot tell a limit from an emptiness.
 */
function SectionMiss({ kind }: { kind: string }) {
  const t = useTranslations('supervisor.section');
  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
      <div className="text-[12px] text-foreground/80">
        {t('miss', { kind: kind || t('missNameless') })}
      </div>
    </div>
  );
}

/** The shared empty idiom. An empty band is a STATE, never error chrome (ADR-198 §3). */
function SectionEmpty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
      {children}
    </div>
  );
}

function Row({
  onOpen, icon, title, sub, at, accent,
}: {
  onOpen: () => void;
  icon: React.ReactNode;
  title: string;
  sub?: string;
  at?: string | null;
  accent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        'flex w-full items-center gap-3 border-b border-border/60 px-3 py-2 text-left last:border-b-0',
        'hover:bg-muted/40 focus-visible:bg-muted/40 focus-visible:outline-none',
      )}
    >
      <span className={cn('shrink-0', accent ? 'text-amber-600 dark:text-amber-500' : 'text-muted-foreground')}>
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[13px] text-foreground">{title}</span>
        {sub ? (
          <span className="block truncate text-[12px] text-muted-foreground">{sub}</span>
        ) : null}
      </span>
      {at ? (
        <span className="shrink-0 text-[11px] text-muted-foreground">{formatRelativeTime(at)}</span>
      ) : null}
    </button>
  );
}

/** `work` — *what standing work do I have, and is it running?* (ADR-658 D5) */
function WorkSection({ work }: { work: WorkBand }) {
  const t = useTranslations('supervisor.section');

  if (work.failed) {
    return <SectionEmpty>{t('workUnreadable')}</SectionEmpty>;
  }
  if (work.rows === null) {
    return <SectionEmpty>{t('loading')}</SectionEmpty>;
  }

  if (work.rows.length === 0) {
    // ⭐ THE EMPTY STATE NAMES THE NEXT STEP, AND NOTHING ELSE (VOICE §2 —
    // title ≤ 4 words + one sentence). The next step is the conversation
    // beside it (ADR-667 D1): work is set up by saying what keeps happening.
    return (
      <div className="rounded-lg border border-dashed border-border/60 bg-muted/10 px-5 py-8 text-center">
        <p className="text-[15px] font-semibold text-foreground">{t('workEmptyTitle')}</p>
        <p className="mx-auto mt-1 max-w-sm text-[13px] text-muted-foreground">{t('workEmptyConversation')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-muted-foreground">
        {t('workIntro')}
      </p>
      <ul className="space-y-2.5">
        {work.rows.map((row) => (
          <StandingRow
            key={row.topic}
            row={row}
            busy={work.busy === row.topic}
            note={work.notes[row.topic]}
            viewerId={work.viewerId}
            onRunNow={work.onRunNow}
            onTogglePause={work.onTogglePause}
            onOpen={work.onOpen}
          />
        ))}
      </ul>
    </div>
  );
}

function RunList({ runs, band }: { runs: Run[]; band: RunsBand }) {
  return (
    <ul className="space-y-2">
      {runs.map((r) => (
        <li key={r.id}>
          <RunView
            run={r}
            viewerId={band.viewerId}
            compact
            onOpen={band.onOpen}
            onRunIt={band.onRunIt}
            onOpenFile={band.onOpenFile}
            onChanged={band.onChanged}
          />
        </li>
      ))}
    </ul>
  );
}

/** `running` — *what is happening now?* (ADR-666 D8) */
function RunningSection({ band }: { band: RunsBand }) {
  const t = useTranslations('supervisor.section');
  if (band.runs === null) {
    return <SectionEmpty>{band.failed ? t('runsUnreadable') : t('loading')}</SectionEmpty>;
  }
  const going = band.runs.filter((r) => r.state === 'queued' || r.state === 'running');
  // ⭐ The RESTING state, not an empty one — "nothing is running" is a
  // complete sentence a member can stop reading at (APP-BUILDER-UX §4.1).
  if (going.length === 0) return <SectionEmpty>{t('runningEmpty')}</SectionEmpty>;
  return <RunList runs={going} band={band} />;
}

/** `needs-you` — *what is waiting on me?* Runs due and failed (ADR-666 D8),
 *  and mentions (the ADR-637 attention cursor). */
function NeedsYouSection({
  rows, band, onOpenLane,
}: { rows: SupervisorNeed[] | null; band: RunsBand; onOpenLane: (id: string) => void }) {
  const t = useTranslations('supervisor.section');
  const needing = band.runs ? runsNeedingYou(band.runs, band.viewerId) : [];
  if (rows === null && band.runs === null) {
    return <SectionEmpty>{t('loading')}</SectionEmpty>;
  }
  if (needing.length === 0 && (rows ?? []).length === 0) {
    // ⭐ Not an empty state — the RESTING state. "Nothing is waiting on you" is
    // a complete, reassuring sentence; "No items" says the same thing and reads
    // like a failure (APP-BUILDER-UX §4.1).
    return <SectionEmpty>{t('needsYouEmpty')}</SectionEmpty>;
  }
  return (
    <div className="space-y-2">
      {needing.length > 0 && <RunList runs={needing} band={band} />}
      {(rows ?? []).length > 0 && (
        <div className="rounded-md border border-border/60">
          {(rows ?? []).map((r) => (
            <Row
              key={`${r.lane_id}-${r.at}`}
              accent
              icon={<MessageSquare className="h-3.5 w-3.5" />}
              title={r.title}
              sub={r.excerpt}
              at={r.at}
              onOpen={() => onOpenLane(r.lane_id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/** `recent` — *what just happened?* Ended runs, newest first, less the ones
 *  already raised in needs-you (one run, one place on the screen). */
function RecentSection({ band }: { band: RunsBand }) {
  const t = useTranslations('supervisor.section');
  if (band.runs === null) {
    return <SectionEmpty>{band.failed ? t('runsUnreadable') : t('loading')}</SectionEmpty>;
  }
  const raised = new Set(runsNeedingYou(band.runs, band.viewerId).map((r) => r.id));
  const ended = band.runs.filter((r) => !isLiveRun(r) && !raised.has(r.id)).slice(0, RECENT_CAP);
  if (ended.length === 0) return <SectionEmpty>{t('recentEmpty')}</SectionEmpty>;
  return <RunList runs={ended} band={band} />;
}

export function SupervisorSection({
  section, data, work, runs, onOpenLane,
}: {
  section: SupervisorSectionDecl;
  /** null = the composed band's read is still out; each band says so itself. */
  data: SupervisorStateData | null;
  work: WorkBand;
  runs: RunsBand;
  onOpenLane: (id: string) => void;
}) {
  const kind = (section?.kind || '').trim();
  const body = (() => {
    switch (kind) {
      case 'running':
        return <RunningSection band={runs} />;
      case 'needs-you':
        return <NeedsYouSection rows={data ? data.needs_you : null} band={runs} onOpenLane={onOpenLane} />;
      case 'work':
        return <WorkSection work={work} />;
      case 'recent':
        return <RecentSection band={runs} />;
      default:
        return <SectionMiss kind={kind} />;
    }
  })();

  return (
    <section className="space-y-2">
      {section.title ? (
        <h3 className="text-[13px] font-medium text-foreground/80">{section.title}</h3>
      ) : null}
      {body}
    </section>
  );
}
