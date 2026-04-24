'use client';

/**
 * SnapshotModal — /chat overlay for mid-conversation awareness (ADR-215 Phase 6).
 *
 * Briefing archetype in its purest form (ADR-198 §3). The overlay is *of*
 * the conversation — Close returns the operator to typing with enriched
 * awareness. Three tabs, all pure reads, rendered in place:
 *
 *   [Target]  Mandate          → /workspace/context/_shared/MANDATE.md
 *   [Scale]   Review standard  → /workspace/review/principles.md
 *                                + tail of /workspace/review/decisions.md
 *   [Clock]   Recent           → pending proposals count + last 3 task runs
 *                                + latest /workspace/memory/awareness.md snippet
 *
 * Contract invariants (canonical in docs/design/SURFACE-CONTRACTS.md):
 *   I1  — stay-in-chat: no "Open on Files" links per row, no stat cards
 *         that ship elsewhere. Close returns to typing.
 *   I2  — zero LLM at modal open. 3 HTTP GETs + 2 SELECTs. No summarization,
 *         no reasoning, no cross-referencing commentary.
 *   I3  — at most one <EditInChatButton> per tab seeding a tab-contextual
 *         prompt. Seed closes the modal; operator owns pressing Send.
 *
 * ADR-215 supersedes the prior four-tab WorkspaceStateView
 * (Readiness / Attention / Last session / Activity) — design substrate
 * collapsed to answer one question per tab instead of four.
 */

import { useEffect, useState } from 'react';
import {
  X,
  Target,
  Scale,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  PauseCircle,
  Eye,
  Sparkles,
  Inbox,
  Activity,
} from 'lucide-react';
import { api, APIError } from '@/lib/api/client';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { EditInChatButton } from '@/components/shared/EditInChatButton';
import {
  parseDecisions,
  formatActionType,
  formatRelativeTimestamp,
  identityLabel,
  type ReviewerDecision,
} from '@/lib/reviewer-decisions';
import { cn } from '@/lib/utils';
import type { Task } from '@/types';
import type { SnapshotLead } from '@/lib/snapshot-meta';

interface SnapshotModalProps {
  open: boolean;
  /** Which tab to open on first mount. If null, defaults to `mandate`. */
  lead: SnapshotLead | null;
  /** Optional one-liner YARNNN can pass to explain why it opened the overlay. */
  reason?: string | null;
  /** Tasks for the Recent tab's task-run list. */
  tasks: Task[];
  onClose: () => void;
  /** Seeds a chat prompt after closing. Invoked by per-tab EditInChatButton. */
  onAskTP: (prompt: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function SnapshotModal({
  open,
  lead,
  reason,
  tasks,
  onClose,
  onAskTP,
}: SnapshotModalProps) {
  const initialLead = lead ?? 'mandate';
  const [activeTab, setActiveTab] = useState<SnapshotLead>(initialLead);

  useEffect(() => {
    if (lead) setActiveTab(lead);
  }, [lead]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-foreground/40 px-4 py-[8vh] backdrop-blur-sm animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-label="Snapshot"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <section
        className="w-full max-w-2xl animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-xl border border-border bg-background shadow-2xl">
          <header className="flex items-start justify-between border-b border-border px-5 py-3">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
                Snapshot
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

          <nav className="flex gap-1 border-b border-border px-3 pt-2">
            <TabButton
              active={activeTab === 'mandate'}
              icon={Target}
              label="Mandate"
              onClick={() => setActiveTab('mandate')}
            />
            <TabButton
              active={activeTab === 'review'}
              icon={Scale}
              label="Review standard"
              onClick={() => setActiveTab('review')}
            />
            <TabButton
              active={activeTab === 'recent'}
              icon={Clock}
              label="Recent"
              onClick={() => setActiveTab('recent')}
            />
          </nav>

          <div className="max-h-[70vh] overflow-y-auto">
            {activeTab === 'mandate' && (
              <MandateTab onAskTP={(p) => { onClose(); onAskTP(p); }} />
            )}
            {activeTab === 'review' && (
              <ReviewStandardTab onAskTP={(p) => { onClose(); onAskTP(p); }} />
            )}
            {activeTab === 'recent' && (
              <RecentTab tasks={tasks} onAskTP={(p) => { onClose(); onAskTP(p); }} />
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

// =============================================================================
// Tab nav button
// =============================================================================

function TabButton({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1.5 rounded-t-md px-3 py-1.5 text-xs font-medium',
        active
          ? 'bg-foreground text-background'
          : 'text-muted-foreground hover:text-foreground',
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </button>
  );
}

// =============================================================================
// Tab: Mandate
// =============================================================================

function MandateTab({ onAskTP }: { onAskTP: (p: string) => void }) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const file = await api.workspace.getFile('/workspace/context/_shared/MANDATE.md');
        if (!cancelled) setContent(file.content ?? '');
      } catch (err) {
        if (!cancelled) {
          // ADR-198 §3 Briefing invariant: 404 is empty state, not error chrome.
          if (err instanceof APIError && err.status === 404) setContent('');
          else setContent('');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <TabLoading />;
  }

  if (!content || !content.trim()) {
    return (
      <TabEmpty
        icon={Target}
        title="Mandate not yet declared"
        body={
          <>
            Your mandate is your Primary-Action declaration — the external
            write you&apos;re trying to move value with (submit an order, list a
            product, ship a campaign) plus success criteria and guardrails.
            YARNNN uses it as the gate for creating tasks.
          </>
        }
        editPrompt="Help me author my mandate — the Primary Action I'm running, my success criteria, and the boundary conditions."
        editLabel="Author in chat"
        onAskTP={onAskTP}
      />
    );
  }

  return (
    <div className="space-y-4 px-5 py-4">
      <p className="text-xs text-muted-foreground/70">
        Your Primary-Action declaration — what you&apos;ve committed to. YARNNN
        gates task creation on this.
      </p>
      <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
        <MarkdownRenderer content={content} />
      </div>
      <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
        <EditInChatButton
          prompt="I want to revise my mandate. Show me the current declaration and help me sharpen it."
          onOpenChatDraft={onAskTP}
        />
      </div>
    </div>
  );
}

// =============================================================================
// Tab: Review standard
// =============================================================================

function ReviewStandardTab({ onAskTP }: { onAskTP: (p: string) => void }) {
  const [principles, setPrinciples] = useState<string | null>(null);
  const [decisions, setDecisions] = useState<ReviewerDecision[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [principlesResult, decisionsResult] = await Promise.allSettled([
        api.workspace.getFile('/workspace/review/principles.md'),
        api.workspace.getFile('/workspace/review/decisions.md'),
      ]);
      if (cancelled) return;
      if (principlesResult.status === 'fulfilled') {
        setPrinciples(principlesResult.value.content ?? '');
      } else {
        setPrinciples('');
      }
      if (decisionsResult.status === 'fulfilled') {
        const parsed = parseDecisions(decisionsResult.value.content ?? '');
        setDecisions(parsed.slice(0, 3));
      } else {
        setDecisions([]);
      }
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <TabLoading />;
  }

  const principlesEmpty = !principles || !principles.trim();

  return (
    <div className="space-y-5 px-5 py-4">
      <p className="text-xs text-muted-foreground/70">
        How judgment happens around here — the Reviewer&apos;s current rules
        and the three most recent verdicts.
      </p>

      {/* Principles */}
      <section>
        <h3 className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          Principles
        </h3>
        {principlesEmpty ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-5 text-center text-xs text-muted-foreground">
            No review principles declared yet.
          </div>
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert text-sm">
            <MarkdownRenderer content={principles!} compact />
          </div>
        )}
      </section>

      {/* Recent verdicts */}
      <section>
        <h3 className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          Recent verdicts
        </h3>
        {decisions.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-4 text-center text-xs text-muted-foreground">
            No verdicts recorded yet.
          </div>
        ) : (
          <ul className="space-y-2">
            {decisions.map((d, i) => (
              <VerdictRow key={`${d.timestamp ?? ''}-${i}`} decision={d} />
            ))}
          </ul>
        )}
      </section>

      <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
        <EditInChatButton
          prompt="I want to evolve my Reviewer's principles. Walk me through the current principles and help me decide what to change."
          onOpenChatDraft={onAskTP}
        />
      </div>
    </div>
  );
}

function VerdictRow({ decision }: { decision: ReviewerDecision }) {
  const Icon =
    decision.decision === 'approve' ? CheckCircle2 :
    decision.decision === 'reject' ? XCircle :
    decision.decision === 'defer' ? PauseCircle :
    Eye;
  const iconColor =
    decision.decision === 'approve' ? 'text-green-600' :
    decision.decision === 'reject' ? 'text-red-600' :
    decision.decision === 'defer' ? 'text-amber-600' :
    'text-muted-foreground';
  return (
    <li className="rounded-md border border-border/60 bg-muted/10 px-3 py-2">
      <div className="flex items-center gap-2 text-[11px]">
        <Icon className={cn('h-3 w-3', iconColor)} />
        <span className="font-medium">
          {decision.decision
            ? decision.decision.charAt(0).toUpperCase() + decision.decision.slice(1)
            : 'Observed'}
        </span>
        <span className="text-muted-foreground/50">·</span>
        <span className="text-muted-foreground">{identityLabel(decision.identity)}</span>
        {decision.actionType && (
          <>
            <span className="text-muted-foreground/50">·</span>
            <span className="truncate text-muted-foreground">{formatActionType(decision.actionType)}</span>
          </>
        )}
        <span className="ml-auto text-muted-foreground/50">
          {formatRelativeTimestamp(decision.timestamp)}
        </span>
      </div>
      {decision.reasoning && (
        <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
          {decision.reasoning}
        </p>
      )}
    </li>
  );
}

// =============================================================================
// Tab: Recent
// =============================================================================

function RecentTab({
  tasks,
  onAskTP,
}: {
  tasks: Task[];
  onAskTP: (p: string) => void;
}) {
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [pendingTitles, setPendingTitles] = useState<string[]>([]);
  const [awareness, setAwareness] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [proposalsResult, awarenessResult] = await Promise.allSettled([
        api.proposals.list('pending', 10),
        api.workspace.getFile('/workspace/memory/awareness.md'),
      ]);
      if (cancelled) return;
      if (proposalsResult.status === 'fulfilled') {
        const rows = proposalsResult.value.proposals || [];
        setPendingCount(rows.length);
        setPendingTitles(rows.slice(0, 3).map((p) => formatActionType(p.action_type)));
      }
      if (awarenessResult.status === 'fulfilled') {
        setAwareness(awarenessResult.value.content ?? '');
      } else {
        setAwareness('');
      }
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return <TabLoading />;
  }

  // Recent task runs — derive from tasks prop (last 3 with last_run_at).
  const recentRuns = [...tasks]
    .filter((t) => t.last_run_at)
    .sort((a, b) => (b.last_run_at ?? '').localeCompare(a.last_run_at ?? ''))
    .slice(0, 3);

  const awarenessTrimmed = (awareness ?? '').trim();
  const awarenessEmpty = awarenessTrimmed.length === 0;

  return (
    <div className="space-y-5 px-5 py-4">
      <p className="text-xs text-muted-foreground/70">
        What&apos;s unresolved right now.
      </p>

      {/* Pending proposals */}
      <section>
        <h3 className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          Awaiting you
        </h3>
        {pendingCount === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-4 text-center text-xs text-muted-foreground">
            No pending proposals.
          </div>
        ) : (
          <div className="rounded-md border border-border/60 bg-muted/10 px-3 py-2.5">
            <div className="flex items-center gap-2 text-xs">
              <Inbox className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="font-medium">
                {pendingCount} {pendingCount === 1 ? 'proposal' : 'proposals'} awaiting you
              </span>
            </div>
            {pendingTitles.length > 0 && (
              <ul className="mt-1.5 space-y-0.5">
                {pendingTitles.map((t, i) => (
                  <li key={i} className="truncate text-[11px] text-muted-foreground">
                    · {t}
                  </li>
                ))}
                {pendingCount > pendingTitles.length && (
                  <li className="text-[11px] text-muted-foreground/70">
                    · and {pendingCount - pendingTitles.length} more
                  </li>
                )}
              </ul>
            )}
          </div>
        )}
      </section>

      {/* Recent runs */}
      <section>
        <h3 className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          Recent runs
        </h3>
        {recentRuns.length === 0 ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-4 text-center text-xs text-muted-foreground">
            No task runs yet.
          </div>
        ) : (
          <ul className="space-y-1">
            {recentRuns.map((t) => (
              <li
                key={t.slug}
                className="flex items-center gap-2 rounded-md border border-border/60 bg-muted/10 px-3 py-2 text-xs"
              >
                <Activity className="h-3 w-3 text-muted-foreground" />
                <span className="truncate font-medium">{t.title}</span>
                <span className="ml-auto text-[10px] text-muted-foreground/70">
                  {formatRelativeTimestamp(t.last_run_at)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Awareness note */}
      <section>
        <h3 className="mb-2 text-[10px] font-medium uppercase tracking-wide text-muted-foreground/60">
          My note between sessions
        </h3>
        {awarenessEmpty ? (
          <div className="rounded-md border border-dashed border-border/60 bg-muted/10 px-4 py-4 text-center text-xs text-muted-foreground">
            No cross-session note yet.
          </div>
        ) : (
          <div className="rounded-md border border-border/60 bg-muted/10 px-3 py-2.5">
            <div className="prose prose-sm max-w-none dark:prose-invert text-[12px] leading-relaxed">
              <MarkdownRenderer content={tailMarkdown(awarenessTrimmed, 8)} compact />
            </div>
          </div>
        )}
      </section>

      <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
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

// =============================================================================
// Shared helpers
// =============================================================================

function TabLoading() {
  return (
    <div className="flex items-center justify-center py-10">
      <Loader2 className="h-4 w-4 animate-spin text-muted-foreground/40" />
    </div>
  );
}

function TabEmpty({
  icon: Icon,
  title,
  body,
  editPrompt,
  editLabel: _editLabel,
  onAskTP,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: React.ReactNode;
  editPrompt: string;
  editLabel?: string;
  onAskTP: (p: string) => void;
}) {
  return (
    <div className="space-y-4 px-6 py-10 text-center">
      <Sparkles className="mx-auto h-6 w-6 text-muted-foreground/20" />
      <div>
        <h3 className="mb-1 text-sm font-medium text-foreground">{title}</h3>
        <p className="mx-auto max-w-md text-xs text-muted-foreground leading-relaxed">{body}</p>
      </div>
      <div className="flex justify-center">
        <EditInChatButton prompt={editPrompt} onOpenChatDraft={onAskTP} />
      </div>
    </div>
  );
}

/**
 * Tail of a markdown string — returns the last N lines (trimmed). Keeps
 * the snapshot short; the full content lives in the file on Files tab.
 */
function tailMarkdown(content: string, lines: number): string {
  const allLines = content.split('\n');
  if (allLines.length <= lines) return content;
  return allLines.slice(-lines).join('\n');
}
