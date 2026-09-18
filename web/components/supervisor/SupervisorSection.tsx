'use client';

/**
 * SupervisorSection — the component vocabulary, dispatched by kind (ADR-656 §7).
 *
 * ⭐ THE DATA-DRIVEN RENDERING PATH. YARNNN had exactly one — a string-`kind` →
 * component table with an honest amber miss — and it died as COLLATERAL in
 * `e18e178`, six weeks after ADR-435 explicitly preserved it, by no ruling of
 * its own (ADR-653 §1.3). This is that path, rebuilt for the surface that needs
 * it: one whose shape is DECLARED rather than mirrored.
 *
 * ⚠️ THE VOCABULARY IS DERIVED FROM WHAT THE APP MUST ANSWER, not inherited.
 * ADR-653's first cut (`files` · `recent` · `needs-you` · `note`) was designed
 * for a MEMBER app over a FOLDER. The supervisor's material is WORK IN FLIGHT,
 * so two of those four survive by meaning and two are deliberately NOT carried:
 *
 *   needs-you  what is waiting on me?   (kept — the ADR-637 attention cursor)
 *   threads    what is underway?        (NEW — and the reason this app exists)
 *   note       what did we decide?      (kept — a rendered .md)
 *
 *   files   — NOT carried. The supervisor owns no folder of work; a file list
 *             of its own notes answers nothing a member asks.
 *   recent  — NOT carried. "What moved" is the timeline's job (Notifications).
 *             Duplicating it here is exactly the "glorified redirect" ADR-435
 *             deleted the last composition for being.
 *
 * ⭐ `threads` is the one NEW kind, and it satisfies the growth rule rather
 * than bypassing it: a kind is added when a real app needs it and cannot be
 * served, and no existing kind shows work in flight.
 *
 * ⚠️ NO LAYOUT PROPS, EVER. A section declares `kind` and `title`. The moment
 * one takes `columns` or `align` this is a page builder — the feature race the
 * app-seam analysis says we lose.
 */

import { AlertTriangle, Compass, MessageSquare } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { formatRelativeTime } from '@/lib/formatting';
import { cn } from '@/lib/utils';

export interface SupervisorNeed {
  lane_id: string;
  title: string;
  excerpt: string;
  at?: string | null;
}

export interface SupervisorThread {
  lane_id: string;
  title: string;
  app: string;
  agent: string;
  at?: string | null;
}

export interface SupervisorNote {
  path: string;
  content: string;
}

export interface SupervisorStateData {
  needs_you: SupervisorNeed[];
  threads: SupervisorThread[];
  note: SupervisorNote | null;
}

/** The kinds this client can draw. */
export const SUPERVISOR_SECTION_KINDS = ['needs-you', 'threads', 'note'] as const;
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

/** `needs-you` — *what is waiting on me?* */
function NeedsYouSection({
  rows, onOpenLane,
}: { rows: SupervisorNeed[]; onOpenLane: (id: string) => void }) {
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

/** `threads` — *what is underway?* */
function ThreadsSection({
  rows, onOpenLane,
}: { rows: SupervisorThread[]; onOpenLane: (id: string) => void }) {
  if (rows.length === 0) {
    return <SectionEmpty>Nothing is underway yet. Conversations you start show up here.</SectionEmpty>;
  }
  return (
    <div className="rounded-md border border-border/60">
      {rows.map((r) => (
        <Row
          key={r.lane_id}
          icon={<Compass className="h-3.5 w-3.5" />}
          title={r.title}
          // ⚠️ An empty `app` means the thread belongs to nothing — the gap
          // routing fills (ADR-656 §4). Say so plainly rather than hiding it:
          // a member who can see what is unplaced can place it.
          sub={r.app ? `${r.app}${r.agent ? ` · ${r.agent}` : ''}` : 'not filed yet'}
          at={r.at}
          onOpen={() => onOpenLane(r.lane_id)}
        />
      ))}
    </div>
  );
}

/** `note` — *what did we decide?* */
function NoteSection({ note }: { note: SupervisorNote | null }) {
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
  section, data, onOpenLane,
}: {
  section: SupervisorSectionDecl;
  data: SupervisorStateData;
  onOpenLane: (id: string) => void;
}) {
  const kind = (section?.kind || '').trim();
  const body = (() => {
    switch (kind) {
      case 'needs-you':
        return <NeedsYouSection rows={data.needs_you} onOpenLane={onOpenLane} />;
      case 'threads':
        return <ThreadsSection rows={data.threads} onOpenLane={onOpenLane} />;
      case 'note':
        return <NoteSection note={data.note} />;
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
