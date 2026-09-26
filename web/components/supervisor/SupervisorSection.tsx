'use client';

/**
 * SupervisorSection — the component vocabulary, dispatched by kind (ADR-656 §7
 * → ADR-658 D5 → ADR-670 D6).
 *
 * ⭐ THE DATA-DRIVEN RENDERING PATH. YARNNN had exactly one — a string-`kind` →
 * component table with an honest amber miss — and it died as COLLATERAL in
 * `e18e178`, six weeks after ADR-435 explicitly preserved it, by no ruling of
 * its own (ADR-653 §1.3). This is that path, rebuilt for the surface that needs
 * it: one whose shape is DECLARED rather than mirrored.
 *
 * ⚠️ THE VOCABULARY IS DERIVED FROM WHAT A MEMBER ASKS, not from what the
 * system has lying around (ADR-658 §2). A member supervising asks *what is
 * happening, what do I have, what just happened* — so the cockpit reads by RUN
 * STATE (ADR-666 D8):
 *
 *   running    what is happening now        runs: queued · running
 *   work       what standing work I have    the roster (ADR-658)
 *   recent     what just happened           runs: done · failed · stopped
 *
 *   needs-you — DELETED (ADR-670 D5): *what is waiting on me* has ONE reader,
 *               `useNeedsYou`, rendered by the shared strip every index mounts.
 *               A band of the Supervisor's own was a third derivation that
 *               never showed a pending decision.
 *   note      — DELETED (ADR-666 D8): `DECISIONS.md` had no writer.
 *   threads   — DELETED (ADR-658 §2): a list of conversations answered nothing.
 *
 * ⭐ WHERE A KIND RENDERS IS THE KIND'S, NEVER THE DECLARATION'S (ADR-670 D6).
 * Band 3 is the frame — index · object · supervision — and each kind knows
 * which of those it is: `work` is the INDEX (the rail), `running` and `recent`
 * are SUPERVISION (the side). `SECTION_SLOT` says so once. A declaration still
 * carries only `kind` and `title`.
 *
 * `running` and `recent` read the run ledger through ONE store (`useRuns`);
 * they are not the timeline — the timeline is every act, these are the work.
 *
 * ⭐ `work` satisfies the growth rule rather than bypassing it: no existing
 * kind shows the work that runs on its own. `running` / `recent` satisfy it
 * the same way: nothing else shows a run while it happens.
 *
 * ⚠️ NO LAYOUT PROPS, EVER. A section declares `kind` and `title`. The moment
 * one takes `columns` or `align` this is a page builder — the feature race the
 * app-seam analysis says we lose.
 */

import { useTranslations } from 'next-intl';
import { AlertTriangle } from 'lucide-react';
import { RunView } from '@/components/runs/RunView';
import { StandingRow } from '@/components/standing/StandingRow';
import { isLiveRun, type Run, type StandingSummary } from '@/lib/api/client';

/**
 * The run bands' material and verbs (ADR-666 D8) — the ledger read from its
 * ONE store (`useRuns`). The verbs open (the run's Trace), start (the one door
 * that runs a browser run), and — inside `RunView` — stop.
 */
export interface RunsBand {
  /** null = not read yet (or unreadable — `failed` says which). */
  runs: Run[] | null;
  failed: boolean;
  viewerId: string | null;
  /** The run the canvas shows in full — one rendering per run on screen. */
  exceptRunId: string | null;
  onOpen: (run: Run) => void;
  onRunIt: (run: Run) => void;
  onOpenFile: (path: string) => void;
  onChanged: () => void;
}

/** How many ended runs `recent` shows. */
const RECENT_CAP = 8;

/**
 * The `work` band's material — the standing roster read from its ONE route
 * (`api.standing.list`), each row's state brought current by the live ledger.
 * It is the INDEX: a row opens its work; the verbs live on the opened work's
 * side, and creating one is the conversation's (ADR-667 D1).
 */
export interface WorkBand {
  /** null = not read yet (or unreadable — `failed` says which). */
  rows: StandingSummary[] | null;
  failed: boolean;
  viewerId: string | null;
  /** The live ledger (`useRuns`) — a row's going/due state follows it. */
  runs: Run[] | null;
  /** The work that is open, marked in the index. */
  openTopic: string | null;
  onOpen: (row: StandingSummary) => void;
}

/** The kinds this client can draw. */
export const SUPERVISOR_SECTION_KINDS = ['running', 'work', 'recent'] as const;
export type SupervisorSectionKind = (typeof SUPERVISOR_SECTION_KINDS)[number];

/** Which slot of the frame each kind is (ADR-670 D6). A kind this client cannot
 *  draw renders its honest miss in the side. */
export function sectionSlot(kind: string): 'rail' | 'side' {
  return kind === 'work' ? 'rail' : 'side';
}

export interface SupervisorSectionDecl {
  kind: string;
  title?: string;
}

/**
 * The roster row brought current: the served `live_run` is a snapshot from the
 * roster read, the ledger is live. A run of this work going or due in the
 * ledger is the row's live run; one the ledger has seen END is not.
 */
function withLedger(row: StandingSummary, runs: Run[] | null): StandingSummary {
  if (!runs) return row;
  const live = runs.find((r) => r.topic === row.topic && isLiveRun(r)) ?? null;
  const ended = row.live_run != null && runs.some((r) => r.id === row.live_run!.id && !isLiveRun(r));
  return { ...row, live_run: live ?? (ended ? null : row.live_run ?? null) };
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

/** `work` — *what standing work do I have, and how does it stand?* The index
 *  (ADR-670 D6): one line per piece of work, the shared row's `index` form. */
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
      <div className="rounded-lg border border-dashed border-border/60 bg-muted/10 px-4 py-6 text-center">
        <p className="text-[13px] font-semibold text-foreground">{t('workEmptyTitle')}</p>
        <p className="mt-1 text-xs text-muted-foreground">{t('workEmptyConversation')}</p>
      </div>
    );
  }

  return (
    <ul className="-mx-3">
      {work.rows.map((row) => (
        <StandingRow
          key={row.topic}
          variant="index"
          row={withLedger(row, work.runs)}
          selected={work.openTopic === row.topic}
          viewerId={work.viewerId}
          onOpen={work.onOpen}
        />
      ))}
    </ul>
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
  const going = band.runs.filter(
    (r) => (r.state === 'queued' || r.state === 'running') && r.id !== band.exceptRunId,
  );
  // ⭐ The RESTING state, not an empty one — "nothing is running" is a
  // complete sentence a member can stop reading at (APP-BUILDER-UX §4.1).
  if (going.length === 0) return <SectionEmpty>{t('runningEmpty')}</SectionEmpty>;
  return <RunList runs={going} band={band} />;
}

/** `recent` — *what just happened?* Ended runs, newest first. A run due on the
 *  viewer is live, so it is never here — it is in the index's Needs you. */
function RecentSection({ band }: { band: RunsBand }) {
  const t = useTranslations('supervisor.section');
  if (band.runs === null) {
    return <SectionEmpty>{band.failed ? t('runsUnreadable') : t('loading')}</SectionEmpty>;
  }
  const ended = band.runs
    .filter((r) => !isLiveRun(r) && r.id !== band.exceptRunId)
    .slice(0, RECENT_CAP);
  if (ended.length === 0) return <SectionEmpty>{t('recentEmpty')}</SectionEmpty>;
  return <RunList runs={ended} band={band} />;
}

export function SupervisorSection({
  section, work, runs,
}: {
  section: SupervisorSectionDecl;
  work: WorkBand;
  runs: RunsBand;
}) {
  const kind = (section?.kind || '').trim();
  const body = (() => {
    switch (kind) {
      case 'running':
        return <RunningSection band={runs} />;
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
