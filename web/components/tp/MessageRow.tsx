'use client';

/**
 * MessageRow — chat message row-level wrapper (ADR-237).
 *
 * Composes around MessageDispatch's per-shape renderer to apply
 * cross-cutting concerns that are independent of role:
 *
 *   - **Weight gating** (material / routine / housekeeping) per
 *     ADR-219. Material renders the full bubble/card via MessageRenderer;
 *     routine renders as a slim non-interactive label+summary row;
 *     housekeeping renders as a dim one-liner.
 *
 *   - **Authorship attribution chip** per ADR-205 F1 / ADR-219:
 *       - taskSlug set + role !== 'user' → "from {slug}", linked to
 *         /work?task={slug} (recurrence-fired output)
 *       - taskSlug unset + role === 'assistant' + addressed pulse
 *         + invocationId → "ran inline" (chat-fired invocation)
 *
 *   - **Run-on-schedule affordance** — small button below assistant
 *     material messages whose invocation fired inline (no recurrence
 *     slug attached, but `narrative.invocationId` is set, indicating
 *     real production). Per ADR-236 Item 8.2 (2026-04-30) the
 *     graduation attaches to the assistant **output**, not the user
 *     ask — once the operator likes what came out, "run this on a
 *     schedule" is the right verbalization. Wired via the
 *     onMakeRecurring callback (the prop name is preserved for
 *     stability; the surface label says "Run this on a schedule").
 *
 * The row wrapper is the canonical extension point for future cross-
 * cutting concerns (autonomy badges, surface-aware variants, etc.).
 * Per-role components stay focused on rendering content; the row
 * decides what wraps that content.
 */

import { useState, type ReactNode } from 'react';
import { CornerDownRight, Zap, Repeat, X } from 'lucide-react';
import type { TPMessage } from '@/types/desk';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { stripSnapshotMeta, stripOnboardingMeta } from '@/lib/content-shapes/snapshot';
import { MessageRenderer } from './MessageDispatch';
import { WorkspaceFileView } from '@/components/shared/WorkspaceFileView';
import { useReviewerPersona } from '@/lib/reviewer-persona';
import { useTP } from '@/contexts/TPContext';

// ---------------------------------------------------------------------------
// Per-weight wrappers
// ---------------------------------------------------------------------------

interface MaterialWrapperProps {
  msg: TPMessage;
  isLoading: boolean;
  onMakeRecurring?: (messageContent: string) => void;
}

/**
 * Material weight — full bubble/card rendering. Wraps the dispatched
 * shape with the authorship chip (above) and Make Recurring affordance
 * (below) per ADR-237 D2.
 *
 * Reviewer verdicts (role === 'reviewer') skip the chip stack — the
 * ReviewerCard owns its own chrome per ADR-212. The dispatcher emits
 * a ReviewerCard regardless; we suppress the chip stack only for the
 * reviewer shape.
 */
function MaterialRow({ msg, isLoading, onMakeRecurring }: MaterialWrapperProps): JSX.Element {
  const { sendMessage } = useTP();
  const [fileViewOpen, setFileViewOpen] = useState(false);
  const reviewerPersonaName = useReviewerPersona();

  const recurrenceSlug = msg.narrative?.taskSlug;
  const showRecurrenceChip = !!recurrenceSlug && msg.role !== 'user';
  const showInlineFireHint =
    !recurrenceSlug &&
    msg.role === 'assistant' &&
    msg.narrative?.pulse === 'addressed' &&
    !!msg.narrative?.invocationId;
  const isInlineAction = !msg.narrative?.taskSlug;
  // ADR-236 Item 8.2 (2026-04-30): graduation moves from user ask to
  // assistant output — once the output is useful, "run on a schedule".
  const showMakeRecurring =
    msg.role === 'assistant' &&
    isInlineAction &&
    !!msg.narrative?.invocationId &&
    !!onMakeRecurring &&
    !!msg.content?.trim();

  // Extract the run log path from the dispatcher's narrative body.
  // Dispatcher writes "Output at {dir}.\nRun log at {file}.\n..." as the
  // first lines. The run log is a real file (_run_log.md); the output path
  // is a directory which would 404 on getFile. Use run log as the
  // primary view — it's the most informative single file per invocation.
  const runLogPath = (() => {
    if (!recurrenceSlug) return null;
    const match = msg.content?.match(/Run log at ([^\n.]+)/);
    const raw = match?.[1]?.trim();
    return raw?.startsWith('/workspace') ? raw : null;
  })();
  // Also extract the output directory for the fallback label.
  const outputPath = (() => {
    if (!recurrenceSlug) return null;
    const match = msg.content?.match(/Output at ([^\n.]+)/);
    const raw = match?.[1]?.trim();
    return raw?.startsWith('/workspace') ? raw : null;
  })();
  // Prefer run log (actual file); fall back to output dir for labelling.
  const fileViewPath = runLogPath ?? outputPath;

  // Reviewer verdicts render with a labeled section break above — visually
  // separating the Reviewer's voice from YARNNN's narration. The divider
  // makes it clear a different party is speaking (ADR-249: three-party model).
  if (msg.role === 'reviewer') {
    const isObservation = msg.reviewer?.verdict === 'observation';
    if (isObservation) {
      // Observations don't need the full divider — they're housekeeping
      return (
        <div className="max-w-[92%]">
          <MessageRenderer msg={msg} isLoading={isLoading} />
        </div>
      );
    }
    return (
      <div className="pt-2">
        {/* Section break: persona name labels the judgment character speaking */}
        <div className="flex items-center gap-2 mb-2 px-0.5">
          <div className="h-px flex-1 bg-border/40" />
          <span className="text-[9px] font-semibold tracking-widest text-muted-foreground/40 uppercase select-none">
            {reviewerPersonaName ?? 'Reviewer'}
          </span>
          <div className="h-px flex-1 bg-border/40" />
        </div>
        <div className="max-w-[92%]">
          <MessageRenderer msg={msg} isLoading={isLoading} />
        </div>
      </div>
    );
  }

  const chip =
    showRecurrenceChip ? (
      // Chip opens an inline WorkspaceFileView panel — no navigation.
      // Universal kernel pattern: WorkspaceFileView renders any path.
      <button
        type="button"
        onClick={() => setFileViewOpen(v => !v)}
        className="inline-flex items-center gap-1 text-[10px] font-medium text-muted-foreground/60 hover:text-foreground hover:bg-foreground/5 px-1.5 py-0.5 -mx-0.5 -mt-0.5 mb-1 rounded transition-colors"
        title={`From recurrence: ${recurrenceSlug} — view output inline`}
      >
        <CornerDownRight className="w-2.5 h-2.5" />
        <span className="font-mono">{recurrenceSlug}</span>
      </button>
    ) : showInlineFireHint ? (
      <span
        className="inline-flex items-center gap-1 text-[10px] font-medium text-primary/60 px-1.5 py-0.5 -mx-0.5 -mt-0.5 mb-1 rounded"
        title="Inline action — fired immediately on ask"
      >
        <Zap className="w-2.5 h-2.5" />
        <span>ran inline</span>
      </span>
    ) : null;

  return (
    <div className="flex flex-col">
      {chip}
      <MessageRenderer msg={msg} isLoading={isLoading} />

      {/* Inline run log view — opens when operator clicks the recurrence chip.
          Renders the _run_log.md file in-place with WorkspaceFileView.
          No navigation. No redirect. Operator stays in chat. */}
      {fileViewOpen && fileViewPath && (
        <div className="mt-2 rounded-lg border border-border bg-background p-3 relative max-w-[92%] shadow-sm">
          <button
            type="button"
            onClick={() => setFileViewOpen(false)}
            className="absolute top-2 right-2 p-1 text-muted-foreground/40 hover:text-muted-foreground rounded"
            aria-label="Close"
          >
            <X className="h-3.5 w-3.5" />
          </button>
          <WorkspaceFileView
            path={fileViewPath}
            title={recurrenceSlug ?? undefined}
            tagline={outputPath ? `Output: ${outputPath}` : undefined}
            editPrompt={`I want to talk about the latest run of ${recurrenceSlug} — what did it do and what should we do next?`}
            onEdit={(prompt) => { setFileViewOpen(false); sendMessage(prompt); }}
          />
        </div>
      )}

      {/* Fallback: no path extractable from message body */}
      {fileViewOpen && !fileViewPath && (
        <div className="mt-2 rounded-lg border border-border bg-muted/10 p-3 max-w-[92%] text-xs text-muted-foreground">
          Run log path not found in this message.{' '}
          <button
            type="button"
            onClick={() => { setFileViewOpen(false); sendMessage(`Tell me about the latest run of ${recurrenceSlug}.`); }}
            className="underline underline-offset-4 hover:no-underline"
          >
            Ask YARNNN instead
          </button>
        </div>
      )}

      {showMakeRecurring && (
        <div className="mt-1.5 -mb-0.5">
          <button
            type="button"
            onClick={() => onMakeRecurring!(msg.content)}
            className="inline-flex items-center gap-1 text-[10px] font-medium text-primary/70 hover:text-primary hover:bg-primary/5 px-1.5 py-0.5 rounded transition-colors"
            title="Run this on a schedule — chat with YARNNN to set cadence + delivery"
          >
            <Repeat className="w-2.5 h-2.5" />
            Run this on a schedule
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * Maps raw DB role → canonical operator-facing display label per ADR-247 +
 * FOUNDATIONS v7.0 three-party narrative model.
 *
 * Three primary parties: operator ("You"), YARNNN system ("YARNNN"),
 * Reviewer (operator-authored persona name — caller must resolve and pass).
 * Secondary roles (agent, system, external) keep their technical names.
 */
function roleDisplayLabel(role: TPMessage['role'], reviewerPersona?: string | null): string {
  switch (role) {
    case 'user': return 'You';
    case 'assistant': return 'system';
    case 'reviewer': return reviewerPersona ?? 'Reviewer';
    case 'agent': return 'agent';
    case 'system': return 'system';
    case 'external': return 'external';
    default: return role;
  }
}

/**
 * Routine weight — slim non-interactive row. Label + summary + timestamp.
 * No expand toggle — routine entries are ambient log signal, not actionable
 * content the operator needs to drill into.
 */
function RoutineRow({ msg, reviewerPersona }: { msg: TPMessage; reviewerPersona?: string | null }): JSX.Element {
  const summary =
    msg.narrative?.summary ??
    (msg.content?.split('\n', 1)[0]?.slice(0, 160) ?? '');
  return (
    <div className="flex items-center gap-2 max-w-[92%] py-0.5 opacity-60">
      <span className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground/60 shrink-0">
        {roleDisplayLabel(msg.role, reviewerPersona)}
      </span>
      <span className="text-[12px] text-muted-foreground truncate flex-1">{summary}</span>
      <span className="text-[10px] text-muted-foreground/40 shrink-0 tabular-nums">
        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  );
}

/**
 * Housekeeping weight — dim one-liner. The narrative_digest system_card
 * (rendered via the material path when its containing message has
 * weight=material) is the curated surface for housekeeping clusters;
 * individual housekeeping rows still render here in case the digest
 * hasn't run yet, but they're visually de-emphasized.
 */
function HousekeepingRow({ msg, reviewerPersona }: { msg: TPMessage; reviewerPersona?: string | null }): JSX.Element {
  const summary =
    msg.narrative?.summary ??
    (msg.content?.split('\n', 1)[0]?.slice(0, 160) ?? '');
  return (
    <div className="text-[11px] flex items-center gap-2 max-w-[92%] py-0.5 opacity-50 hover:opacity-90 transition-opacity">
      <span className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground/50">
        {roleDisplayLabel(msg.role, reviewerPersona)}
      </span>
      <span className="text-muted-foreground truncate flex-1">{summary}</span>
      <span className="text-[10px] text-muted-foreground/40 shrink-0 tabular-nums">
        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public row component
// ---------------------------------------------------------------------------

export interface MessageRowProps {
  msg: TPMessage;
  isLoading: boolean;
  onMakeRecurring?: (messageContent: string) => void;
}

/**
 * Top-level row wrapper. Reads `msg.narrative.weight` and delegates to
 * the appropriate per-weight wrapper (material / routine / housekeeping).
 * Material rows compose with MessageDispatch's renderer; routine and
 * housekeeping have their own minimal renders that don't go through
 * the dispatch table (they're presentation collapses, not full
 * role-shaped renderings).
 */
export function MessageRow({ msg, isLoading, onMakeRecurring }: MessageRowProps): JSX.Element {
  const reviewerPersona = useReviewerPersona();
  const weight = msg.narrative?.weight ?? 'material';
  if (weight === 'material') {
    return <MaterialRow msg={msg} isLoading={isLoading} onMakeRecurring={onMakeRecurring} />;
  }
  if (weight === 'routine') {
    return <RoutineRow msg={msg} reviewerPersona={reviewerPersona} />;
  }
  return <HousekeepingRow msg={msg} reviewerPersona={reviewerPersona} />;
}
