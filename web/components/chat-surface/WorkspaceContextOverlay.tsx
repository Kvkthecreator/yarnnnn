'use client';

/**
 * WorkspaceContextOverlay — replaces SnapshotModal (ADR-215 Phase 6).
 *
 * The SnapshotModal had three tabs (Mandate / Review standard / Recent)
 * each with bespoke fetch + render logic (~612 LOC total). This component
 * replaces it with a single scrollable panel of `WorkspaceFileView` cards —
 * one component, one contract.
 *
 * Design change: no tabs. The three files stack vertically in one
 * scrollable view. The operator sees all of them in sequence without
 * clicking between tabs. "Recent" (proposals + runs) remains as a small
 * dedicated section since it queries non-file data.
 *
 * Contract invariants preserved from SnapshotModal:
 *   I1 — stay-in-chat: Close returns to typing. No page navigation.
 *   I2 — zero LLM at open. Pure substrate reads.
 *   I3 — Edit-in-chat buttons seed prompts; operator presses Send.
 *
 * `SnapshotLead` still controls which section is scrolled into view on open,
 * so YARNNN can direct attention: `<!-- snapshot: mandate -->` scrolls to
 * the mandate card, `<!-- snapshot: review -->` scrolls to principles, etc.
 */

import { useEffect, useRef, useState } from 'react';
import {
  X,
  Clock,
  Inbox,
  Activity,
} from 'lucide-react';
import { api } from '@/lib/api/client';
import { WorkspaceFileView } from '@/components/shared/WorkspaceFileView';
import { EditInChatButton } from '@/components/shared/EditInChatButton';
import { MandateCard } from '@/components/workspace-concepts/MandateCard';
import { PrinciplesCard } from '@/components/workspace-concepts/PrinciplesCard';
import { formatActionType, formatRelativeTimestamp } from '@/lib/content-shapes/decisions';
import type { Recurrence } from '@/types';
import type { SnapshotLead } from '@/lib/content-shapes/snapshot';

interface WorkspaceContextOverlayProps {
  open: boolean;
  /** Which section to scroll into view on open. If null, defaults to top. */
  lead: SnapshotLead | null;
  /** Optional one-liner YARNNN can pass explaining why it opened the overlay. */
  reason?: string | null;
  /** Tasks for the Recent section's task-run list. */
  tasks: Recurrence[];
  onClose: () => void;
  /** Seeds a chat prompt after closing. */
  onAskTP: (prompt: string) => void;
}

export function WorkspaceContextOverlay({
  open,
  lead,
  reason,
  tasks,
  onClose,
  onAskTP,
}: WorkspaceContextOverlayProps) {
  const mandateRef = useRef<HTMLDivElement>(null);
  const reviewRef = useRef<HTMLDivElement>(null);
  const recentRef = useRef<HTMLDivElement>(null);

  // Scroll the relevant section into view when lead changes or overlay opens.
  useEffect(() => {
    if (!open) return;
    const ref =
      lead === 'mandate' ? mandateRef :
      lead === 'review' ? reviewRef :
      lead === 'recent' ? recentRef :
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
            {/* Mandate — compact variant */}
            <div ref={mandateRef} className="px-5 py-5">
              <MandateCard variant="compact" onEdit={editAndClose} />
            </div>

            {/* Principles — compact variant */}
            <div ref={reviewRef} className="px-5 py-5">
              <PrinciplesCard variant="compact" onEdit={editAndClose} />
            </div>

            {/* Recent — proposals + runs + awareness note */}
            <div ref={recentRef} className="px-5 py-5">
              <RecentSection tasks={tasks} onAskTP={editAndClose} />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Recent section — proposals + task runs (not a file, kept separate)
// ---------------------------------------------------------------------------

function RecentSection({
  tasks,
  onAskTP,
}: {
  tasks: Recurrence[];
  onAskTP: (prompt: string) => void;
}) {
  const [pendingCount, setPendingCount] = useState(0);
  const [pendingTitles, setPendingTitles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await api.proposals.list('pending', 10);
        if (cancelled) return;
        const rows = res.proposals || [];
        setPendingCount(rows.length);
        setPendingTitles(rows.slice(0, 3).map((p) => formatActionType(p.action_type)));
      } catch { /* non-fatal */ }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const recentRuns = [...tasks]
    .filter((t) => t.last_run_at)
    .sort((a, b) => (b.last_run_at ?? '').localeCompare(a.last_run_at ?? ''))
    .slice(0, 3);

  return (
    <div className="space-y-4">
      {/* Section heading */}
      <div className="flex items-center gap-1.5">
        <Clock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Recent
        </h3>
      </div>

      {/* Pending proposals */}
      {!loading && pendingCount > 0 && (
        <div className="rounded-md border border-amber-200/60 bg-amber-50/50 px-3 py-2.5">
          <div className="flex items-center gap-2 text-xs">
            <Inbox className="h-3.5 w-3.5 text-amber-600" />
            <span className="font-medium text-amber-800">
              {pendingCount} {pendingCount === 1 ? 'proposal' : 'proposals'} awaiting you
            </span>
          </div>
          {pendingTitles.length > 0 && (
            <ul className="mt-1.5 space-y-0.5">
              {pendingTitles.map((t, i) => (
                <li key={i} className="truncate text-[11px] text-amber-700">· {t}</li>
              ))}
              {pendingCount > pendingTitles.length && (
                <li className="text-[11px] text-amber-600/70">· and {pendingCount - pendingTitles.length} more</li>
              )}
            </ul>
          )}
        </div>
      )}

      {/* Recent task runs */}
      {recentRuns.length > 0 ? (
        <ul className="space-y-1">
          {recentRuns.map((t) => (
            <li
              key={t.slug}
              className="flex items-center gap-2 rounded-md border border-border/60 bg-muted/10 px-3 py-2 text-xs"
            >
              <Activity className="h-3 w-3 text-muted-foreground shrink-0" />
              <span className="truncate font-medium">{t.title}</span>
              <span className="ml-auto text-[10px] text-muted-foreground/60 shrink-0">
                {formatRelativeTimestamp(t.last_run_at)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-muted-foreground/60 text-center py-2">
          No task runs yet.
        </p>
      )}

      {/* Awareness note (file view, compact) */}
      <WorkspaceFileView
        path="/workspace/memory/awareness.md"
        title="My note between sessions"
        tagline="YARNNN's carry-forward context from the last conversation."
        maxLines={8}
        editPrompt="What should I carry forward into the next session? Help me update my awareness note."
        onEdit={onAskTP}
      />

      {/* Bottom CTA */}
      <div className="flex justify-end pt-1">
        <EditInChatButton
          prompt={
            pendingCount > 0
              ? `I have ${pendingCount} pending ${pendingCount === 1 ? 'proposal' : 'proposals'}. Walk me through them so I can decide.`
              : "What should I look at right now?"
          }
          onOpenChatDraft={onAskTP}
        />
      </div>
    </div>
  );
}
