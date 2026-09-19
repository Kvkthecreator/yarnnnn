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
 * system has lying around (ADR-658 §2). The member's question is *"what work do
 * I have, and is it being done?"* — so:
 *
 *   work       what standing work do I have, and is it running?   (ADR-658 — the app's reason)
 *   needs-you  what is waiting on me?                             (kept — the ADR-637 attention cursor)
 *   note       what did we decide?                                (kept — a rendered .md)
 *
 *   threads — DELETED (ADR-658 §2). A list of chat conversations answered
 *             nothing a member asks, and it read `chat_sessions`, so a
 *             first-time member opened to an empty band.
 *   files   — NOT carried. The supervisor owns no folder of work.
 *   recent  — NOT carried. "What moved" is the timeline's job (Notifications).
 *
 * ⭐ `work` satisfies the growth rule rather than bypassing it: no existing
 * kind shows the work that runs on its own, and nothing else in the product
 * lets a member create it by direct manipulation.
 *
 * ⚠️ NO LAYOUT PROPS, EVER. A section declares `kind` and `title`. The moment
 * one takes `columns` or `align` this is a page builder — the feature race the
 * app-seam analysis says we lose.
 */

import { AlertTriangle, Link2, MessageSquare, Plus } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { StandingRow, lowerFirst } from '@/components/standing/StandingRow';
import type { StandingStart, StandingSummary } from '@/lib/api/client';
import { formatRelativeTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';

export interface SupervisorNeed {
  lane_id: string;
  title: string;
  excerpt: string;
  at?: string | null;
}

export interface SupervisorNote {
  path: string;
  content: string;
}

export interface SupervisorStateData {
  needs_you: SupervisorNeed[];
  note: SupervisorNote | null;
}

/**
 * The `work` band's material and verbs — the standing roster read from its
 * ONE route (`api.standing.list`) plus the starts (ADR-658 D7). The verbs act
 * on DECLARATIONS (create · pause · run · retire · open), never on beings.
 */
export interface WorkBand {
  /** null = not read yet (or unreadable — `failed` says which). */
  rows: StandingSummary[] | null;
  failed: boolean;
  starts: StandingStart[];
  busy: string | null;
  notes: Record<string, string>;
  onRunNow: (row: StandingSummary) => void;
  onTogglePause: (row: StandingSummary) => void;
  onOpen: (row: StandingSummary) => void;
  onNew: (start: StandingStart | null) => void;
  onOpenReach: () => void;
}

/** The kinds this client can draw. */
export const SUPERVISOR_SECTION_KINDS = ['work', 'needs-you', 'note'] as const;
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
  return (
    <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2">
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600 dark:text-amber-500" />
      <div className="text-[12px] text-foreground/80">
        This app asks for a <span className="font-medium">{kind || 'nameless'}</span>{' '}
        section, which this workspace cannot show yet.
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
  const connectorStarts = work.starts.filter((s) => s.kind === 'connector');

  if (work.failed) {
    return <SectionEmpty>Couldn&apos;t read your standing work just now.</SectionEmpty>;
  }
  if (work.rows === null) {
    return <SectionEmpty>Loading…</SectionEmpty>;
  }

  if (work.rows.length === 0) {
    // ⭐ THE HIGHEST-LEVERAGE SCREEN IN THE APP (ADR-658 D7). Not "No items":
    // the next step, pre-shaped from what the member has already connected.
    // With nothing connected, the step is Reach — the door that makes a
    // connection — and the web-page start is still offered.
    return (
      <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5">
        <p className="text-sm text-foreground">Nothing runs on its own yet.</p>
        <p className="mt-1 text-xs text-muted-foreground">
          {connectorStarts.length > 0
            ? 'Pick a start below. It runs on a schedule and keeps one file current.'
            : 'Connect Slack, Notion or GitHub in Reach to start from what they read, or start from a web page.'}
        </p>
        <ul className="mt-3 space-y-2">
          {work.starts.map((s) => (
            <li key={`${s.kind}-${s.connector ?? 'url'}`}>
              <button
                type="button"
                onClick={() => work.onNew(s)}
                className="flex w-full items-start gap-3 rounded-md border border-border/70 bg-background px-3 py-2.5 text-left hover:bg-muted/40"
              >
                <Link2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="min-w-0 flex-1">
                  <span className="block text-[13px] text-foreground">{s.title}</span>
                  <span className="block text-[12px] text-muted-foreground">
                    {s.kind === 'connector' ? `${s.name} · reads ${lowerFirst(s.reads ?? 'what you chose')}` : 'Name a page. Its summary stays current.'}
                  </span>
                </span>
              </button>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => work.onNew(null)}
            className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground hover:bg-muted/40"
          >
            <Plus className="h-3.5 w-3.5" /> Set up from scratch
          </button>
          {connectorStarts.length === 0 && (
            <button
              type="button"
              onClick={work.onOpenReach}
              className="rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted/40 hover:text-foreground"
            >
              Open Reach
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Files kept current on a schedule. Open one to see its runs and instructions.
        </p>
        <button
          type="button"
          onClick={() => work.onNew(null)}
          className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1.5 text-xs text-foreground hover:bg-muted/40"
        >
          <Plus className="h-3.5 w-3.5" /> New standing work
        </button>
      </div>
      <ul className="space-y-3">
        {work.rows.map((row) => (
          <StandingRow
            key={row.topic}
            row={row}
            busy={work.busy === row.topic}
            note={work.notes[row.topic]}
            onRunNow={work.onRunNow}
            onTogglePause={work.onTogglePause}
            onOpen={work.onOpen}
          />
        ))}
      </ul>
    </div>
  );
}

/** `needs-you` — *what is waiting on me?* */
function NeedsYouSection({
  rows, onOpenLane,
}: { rows: SupervisorNeed[] | null; onOpenLane: (id: string) => void }) {
  if (rows === null) {
    return <SectionEmpty>Loading…</SectionEmpty>;
  }
  if (rows.length === 0) {
    // ⭐ Not an empty state — the RESTING state. "Nothing is waiting on you" is
    // a complete, reassuring sentence; "No items" says the same thing and reads
    // like a failure (APP-BUILDER-UX §4.1).
    return <SectionEmpty>Nothing is waiting on you.</SectionEmpty>;
  }
  return (
    <div className="rounded-md border border-border/60">
      {rows.map((r) => (
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
  );
}

/** `note` — *what did we decide?* */
function NoteSection({ note, loading }: { note: SupervisorNote | null; loading: boolean }) {
  if (loading) {
    return <SectionEmpty>Loading…</SectionEmpty>;
  }
  if (!note) {
    return <SectionEmpty>Nothing written down yet.</SectionEmpty>;
  }
  return (
    <div className="rounded-md border border-border/60 px-4 py-3">
      {/* `linkifySubstrate` stays FALSE — chat bubbles only, never file content. */}
      <MarkdownRenderer content={note.content} />
    </div>
  );
}

export function SupervisorSection({
  section, data, work, onOpenLane,
}: {
  section: SupervisorSectionDecl;
  /** null = the composed bands' read is still out; each band says so itself. */
  data: SupervisorStateData | null;
  work: WorkBand;
  onOpenLane: (id: string) => void;
}) {
  const kind = (section?.kind || '').trim();
  const body = (() => {
    switch (kind) {
      case 'work':
        return <WorkSection work={work} />;
      case 'needs-you':
        return <NeedsYouSection rows={data ? data.needs_you : null} onOpenLane={onOpenLane} />;
      case 'note':
        return <NoteSection note={data?.note ?? null} loading={data === null} />;
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
