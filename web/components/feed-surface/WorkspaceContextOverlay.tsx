'use client';

/**
 * WorkspaceContextOverlay — Feed surface context primer.
 *
 * 2026-05-14 refactor: collapsed from 8 visual rows of overlapping activity
 * surfaces to 3 cohesive sections. Single operator question this modal
 * answers: **"what do I need to know right now to make sense of the next
 * chat turn?"** — a 5-second awareness primer, not a supervision or
 * forensic surface.
 *
 * Three sections (top → bottom):
 *
 *   1. **Mandate** — what the operation is trying to do.
 *      MandateCard variant=compact. Reads /workspace/constitution/MANDATE.md.
 *
 *   2. **Rules** — how the system judges + how much it acts on its own.
 *      PrinciplesCard variant=compact + AutonomyCard variant=compact.
 *      Reads /workspace/persona/principles.md + _autonomy.yaml.
 *
 *   3. **Pulse** — one-line "is the system alive?" + "what demands my
 *      attention right now?" + deep-links to canonical surfaces for
 *      anything richer.
 *
 * Out-of-scope on this surface (lives elsewhere by design):
 *   - Full upcoming-wakes schedule → /work?tab=schedule
 *   - Full execution history → /activity
 *   - Reviewer-loop supervision → Workspace Settings → System Agent → Activity (ADR-412 D5)
 *   - awareness.md free-form notes (vestigial — never updated past
 *     activation skeleton; substrate continuity is decisions.md +
 *     _performance.md + domain _run_log.md per ADR-261)
 *
 * Previous shape (ADR-215 Phase 6) stacked Mandate + Principles +
 * FreddieActivityPanel + RecentSection + awareness.md — 8 sub-blocks
 * with significant overlap between "Upcoming wakes" + "Recent runs" +
 * "Recent task runs" (three views of the same activity question).
 * The refactor collapses all activity to one compact Pulse strip
 * with deep-links out.
 *
 * SnapshotLead vocabulary updated: 'mandate' | 'rules' | 'pulse'.
 * Legacy 'review' → 'rules' and 'recent' → 'pulse' on read for
 * bookmark-safety on in-flight messages.
 *
 * Contract invariants preserved:
 *   I1 — stay-in-chat: Close returns to typing. No page navigation
 *        triggered by the modal itself; deep-links are explicit operator
 *        choice.
 *   I2 — zero LLM at open. Pure substrate reads.
 *   I3 — Edit-in-chat buttons seed prompts; operator presses Send.
 */

import { useEffect, useRef, useState } from 'react';
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { X, Activity, ArrowRight, Inbox } from 'lucide-react';
import { api } from '@/lib/api/client';
import { MandateCard } from '@/components/workspace-concepts/MandateCard';
import { PrinciplesCard } from '@/components/workspace-concepts/PrinciplesCard';
import { AutonomyCard } from '@/components/workspace-concepts/AutonomyCard';
import type { SnapshotLead } from '@/lib/content-shapes/snapshot';

interface WorkspaceContextOverlayProps {
  open: boolean;
  /** Which section to scroll into view on open. Null = top. */
  lead: SnapshotLead | null;
  /** Optional one-liner YARNNN can pass explaining why it opened the overlay. */
  reason?: string | null;
  onClose: () => void;
  /** Seeds a chat prompt after closing. */
  onAskTP: (prompt: string) => void;
}

export function WorkspaceContextOverlay({
  open,
  lead,
  reason,
  onClose,
  onAskTP,
}: WorkspaceContextOverlayProps) {
  const mandateRef = useRef<HTMLDivElement>(null);
  const rulesRef = useRef<HTMLDivElement>(null);
  const pulseRef = useRef<HTMLDivElement>(null);

  // Scroll the relevant section into view on open. Legacy lead values
  // ('review' / 'recent') are mapped to current vocabulary ('rules' /
  // 'pulse') by the snapshot.ts parser before they reach this component
  // — so we only branch on current values here.
  useEffect(() => {
    if (!open) return;
    const ref =
      lead === 'mandate' ? mandateRef :
      lead === 'rules' ? rulesRef :
      lead === 'pulse' ? pulseRef :
      null;
    if (ref?.current) {
      setTimeout(() => ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }
  }, [open, lead]);

  // Keyboard + body scroll lock.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  const editAndClose = (prompt: string) => { onClose(); onAskTP(prompt); };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/40 px-4 py-[8vh] backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label="Context"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <section
        className="w-full max-w-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-xl border border-border bg-background shadow-2xl">
          {/* Header */}
          <header className="flex items-center justify-between border-b border-border px-5 py-3">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
                Context
              </p>
              {reason && (
                <p className="mt-0.5 text-[11px] text-muted-foreground/70">{reason}</p>
              )}
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded p-1 text-muted-foreground/40 hover:bg-muted hover:text-muted-foreground"
              aria-label="Close"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </header>

          {/* Scrollable body — three stacked sections */}
          <div className="max-h-[75vh] overflow-y-auto divide-y divide-border/40">
            {/* 1. Mandate — what we're trying to do */}
            <div ref={mandateRef} className="px-5 py-5">
              <MandateCard variant="compact" onEdit={editAndClose} />
            </div>

            {/* 2. Rules — judgment framework + autonomy posture */}
            <div ref={rulesRef} className="px-5 py-5 space-y-4">
              <PrinciplesCard variant="compact" onEdit={editAndClose} />
              <AutonomyCard variant="compact" onOpen={() => editAndClose(
                'I want to review my autonomy posture and what each level means for how YARNNN acts.'
              )} />
            </div>

            {/* 3. Pulse — alive? attention-now? */}
            <div ref={pulseRef} className="px-5 py-5">
              <PulseSection onAskTP={editAndClose} />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pulse — collapsed activity primer
// ---------------------------------------------------------------------------
//
// Pre-2026-05-14 the modal had three overlapping activity surfaces (Upcoming
// wakes / Recent runs / Recent task runs). The lens-sharpening discipline
// canonized in WORKSPACE.md (Schedule vs /activity, Autonomy vs Activity tab)
// applies here: each surface answers one operator question, and the modal's
// question is "what do I need to know NOW", not "show me the full activity
// audit". The Pulse section is one cohesive paragraph + a few pointers out.
// ---------------------------------------------------------------------------

interface PulseData {
  liveness_line: string;       // "Last wake 59m ago" | "No wakes in 7d" | "Reviewer not configured"
  pending_count: number;
  pending_titles: string[];
  next_wake_slug: string | null;
  next_wake_relative: string | null;  // "in 22h" | null when no schedule
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const diffMs = Date.now() - new Date(iso).getTime();
  const future = diffMs < 0;
  const abs = Math.abs(diffMs);
  const m = Math.floor(abs / 60_000);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);
  const fmt =
    m < 1 ? 'just now' :
    m < 60 ? `${m}m` :
    h < 24 ? `${h}h` :
    `${d}d`;
  return future ? `in ${fmt}` : `${fmt} ago`;
}

function PulseSection({ onAskTP }: { onAskTP: (prompt: string) => void }) {
  const [data, setData] = useState<PulseData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [proposals, activity] = await Promise.allSettled([
          api.proposals.list('pending', 10),
          api.agents.reviewerActivity(),
        ]);

        const pendingRows = proposals.status === 'fulfilled' ? proposals.value.proposals || [] : [];
        const pendingTitles = pendingRows.slice(0, 3).map((p) => {
          // ADR-307: best-effort short label from the generic queue shape.
          const dc = (p.decision_context ?? {}) as Record<string, unknown>;
          if (p.family === 'substrate') {
            return (dc.message as string) || (dc.path as string) || p.primitive;
          }
          return (dc.expected_effect as string) || p.primitive.replace(/^platform_/, '');
        });

        let livenessLine = 'Reviewer not configured';
        let nextWakeSlug: string | null = null;
        let nextWakeRelative: string | null = null;

        if (activity.status === 'fulfilled') {
          const runs = activity.value.runs ?? [];
          const schedules = activity.value.schedules ?? [];
          if (runs.length > 0 && runs[0].created_at) {
            livenessLine = `Your agent last ran ${relativeTime(runs[0].created_at)} · ${runs.length} times in the last ${activity.value.window_days}d`;
          } else if (schedules.length > 0) {
            livenessLine = `Your agent hasn't run in the last ${activity.value.window_days}d`;
          }

          // Find the nearest upcoming wake (smallest future next_fires_at)
          const upcoming = schedules
            .filter(s => !s.paused && s.next_fires_at)
            .sort((a, b) => (a.next_fires_at ?? '').localeCompare(b.next_fires_at ?? ''));
          if (upcoming.length > 0 && upcoming[0].next_fires_at) {
            nextWakeSlug = upcoming[0].slug;
            nextWakeRelative = relativeTime(upcoming[0].next_fires_at);
          }
        }

        if (cancelled) return;
        setData({
          liveness_line: livenessLine,
          pending_count: pendingRows.length,
          pending_titles: pendingTitles,
          next_wake_slug: nextWakeSlug,
          next_wake_relative: nextWakeRelative,
        });
      } catch {
        if (!cancelled) {
          setData({
            liveness_line: 'Status unavailable',
            pending_count: 0,
            pending_titles: [],
            next_wake_slug: null,
            next_wake_relative: null,
          });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading || !data) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5 text-muted-foreground" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Pulse</h3>
        </div>
        <div className="h-12 rounded bg-muted/20 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5">
        <Activity className="h-3.5 w-3.5 text-muted-foreground" />
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Pulse</h3>
      </div>

      {/* Liveness line + next-wake hint */}
      <div className="text-xs text-foreground space-y-1">
        <p>{data.liveness_line}.</p>
        {data.next_wake_slug && data.next_wake_relative && (
          <p className="text-muted-foreground">
            Next up: <code className="text-[11px] font-mono">{data.next_wake_slug}</code>
            <span className="ml-1.5 tabular-nums text-muted-foreground/70">{data.next_wake_relative}</span>
          </p>
        )}
      </div>

      {/* Pending proposals — only render when there are any */}
      {data.pending_count > 0 && (
        <div className="rounded-md border border-amber-200/60 bg-amber-50/50 px-3 py-2.5">
          <div className="flex items-center gap-2 text-xs">
            <Inbox className="h-3.5 w-3.5 text-amber-600" />
            <span className="font-medium text-amber-800">
              {data.pending_count} {data.pending_count === 1 ? 'proposal' : 'proposals'} awaiting you
            </span>
          </div>
          {data.pending_titles.length > 0 && (
            <ul className="mt-1.5 space-y-0.5">
              {data.pending_titles.map((t, i) => (
                <li key={i} className="truncate text-[11px] text-amber-700">· {t}</li>
              ))}
              {data.pending_count > data.pending_titles.length && (
                <li className="text-[11px] text-amber-600/70">
                  · and {data.pending_count - data.pending_titles.length} more
                </li>
              )}
            </ul>
          )}
          <div className="mt-2">
            <button
              type="button"
              onClick={() => onAskTP(
                `I have ${data.pending_count} pending ${data.pending_count === 1 ? 'proposal' : 'proposals'}. Walk me through them so I can decide.`
              )}
              className="text-[11px] font-medium text-amber-800 hover:text-amber-900 hover:underline underline-offset-4"
            >
              Walk me through them →
            </button>
          </div>
        </div>
      )}

      {/* Deep-links to canonical surfaces */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 pt-1 text-[11px] text-muted-foreground/60">
        <SurfaceLink
          to="workspace-settings"
          params={{ pane: 'activity' }}
          className="inline-flex items-center gap-0.5 hover:text-foreground hover:underline underline-offset-4"
        >
          Freddie activity <ArrowRight className="h-3 w-3" />
        </SurfaceLink>
        <span className="text-muted-foreground/30">·</span>
        <SurfaceLink
          to="recurrence"
          className="inline-flex items-center gap-0.5 hover:text-foreground hover:underline underline-offset-4"
        >
          Full schedule <ArrowRight className="h-3 w-3" />
        </SurfaceLink>
        <span className="text-muted-foreground/30">·</span>
        <SurfaceLink
          to="recurrence"
          params={{ pane: 'activity' }}
          className="inline-flex items-center gap-0.5 hover:text-foreground hover:underline underline-offset-4"
        >
          Execution log <ArrowRight className="h-3 w-3" />
        </SurfaceLink>
      </div>
    </div>
  );
}
