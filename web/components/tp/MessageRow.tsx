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
import { CornerDownRight, Zap, Repeat } from 'lucide-react';
import type { TPMessage } from '@/types/desk';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { stripSnapshotMeta, stripOnboardingMeta } from '@/lib/content-shapes/snapshot';
import { MessageRenderer } from './MessageDispatch';
import { WorkspaceFileView } from '@/components/shared/WorkspaceFileView';
import { useReviewerPersona } from '@/lib/reviewer-persona';
import { InteractiveModal } from './InteractiveModal';
import { useNarrative } from '@/contexts/NarrativeContext';

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
// ---------------------------------------------------------------------------
// Workspace path extraction — generalised for any message role.
//
// Scans message content for /workspace/... paths that are actual files
// (end in an extension or known file names). Directories are excluded —
// WorkspaceFileView would 404 on them. Paths are deduplicated.
// ---------------------------------------------------------------------------

const WORKSPACE_PATH_RE = /\/workspace\/[^\s,;'")\]>]+/g;
const FILE_EXTENSION_RE = /\.[a-z]{2,5}$|\/_(run_log|domain|performance|risk|signals|operator_profile|tracker|feedback|deliverable)\.md$/;

function extractWorkspacePaths(content: string | undefined): string[] {
  if (!content) return [];
  const matches = content.match(WORKSPACE_PATH_RE) ?? [];
  // Keep only paths that look like files, not directories
  const files = matches
    .map(p => p.replace(/[.,;:)>\]]+$/, '').trim()) // strip trailing punctuation
    .filter(p => FILE_EXTENSION_RE.test(p));
  const seen = new Set<string>();
  return files.filter(f => seen.has(f) ? false : (seen.add(f), true));
}

function shortPathLabel(path: string): string {
  // "/workspace/operation/trading/_run_log.md" → "_run_log.md"
  return path.split('/').pop() ?? path;
}

function MaterialRow({ msg, isLoading, onMakeRecurring }: MaterialWrapperProps): JSX.Element {
  const { sendMessage } = useNarrative();
  // openFilePath: which file path is currently open in the overlay (null = closed)
  const [openFilePath, setOpenFilePath] = useState<string | null>(null);
  const reviewerPersonaName = useReviewerPersona();

  const recurrenceSlug = msg.narrative?.taskSlug;
  const showRecurrenceChip = !!recurrenceSlug && msg.role !== 'user';
  const showInlineFireHint =
    !recurrenceSlug &&
    msg.role === 'assistant' &&
    msg.narrative?.pulse === 'addressed' &&
    !!msg.narrative?.invocationId;
  const isInlineAction = !msg.narrative?.taskSlug;
  const showMakeRecurring =
    msg.role === 'assistant' &&
    isInlineAction &&
    !!msg.narrative?.invocationId &&
    !!onMakeRecurring &&
    !!msg.content?.trim();

  // Generalised workspace path extraction — works for any role.
  // Replaces the recurrence-only runLogPath/outputPath pattern.
  const workspacePaths = extractWorkspacePaths(msg.content);
  // Primary path for the recurrence chip (prefer _run_log.md)
  const primaryPath =
    workspacePaths.find(p => p.includes('_run_log')) ??
    workspacePaths[0] ??
    null;

  // Reviewer entries — ADR-258: Reviewer is a chat participant, not a gate announcement.
  // No section dividers for any verdict type. The persona label on the bubble is
  // sufficient identity. Observation entries render through MessageRenderer as
  // dim collapsed lines (ReviewerCard handles that internally).
  if (msg.role === 'reviewer') {
    return (
      <div className="max-w-[92%]">
        <MessageRenderer msg={msg} isLoading={isLoading} />
      </div>
    );
  }

  const chip =
    showRecurrenceChip ? (
      <button
        type="button"
        onClick={() => setOpenFilePath(p => p ? null : (primaryPath ?? null))}
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

      {/* Workspace file path chips — ADR-258: chip opens centered modal (not inline overlay) */}
      {workspacePaths.length > 0 && msg.role !== 'user' && (
        <div className="flex flex-wrap gap-1 mt-1.5 -mb-0.5">
          {workspacePaths.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setOpenFilePath(current => current === p ? null : p)}
              className="inline-flex items-center gap-1 text-[10px] font-mono px-1.5 py-0.5 rounded border border-border/60 text-muted-foreground/60 hover:text-foreground hover:border-border hover:bg-muted/30 transition-colors"
              title={p}
            >
              {shortPathLabel(p)}
            </button>
          ))}
        </div>
      )}

      {/* File modal — centered, same InteractiveModal pattern as proposals */}
      <InteractiveModal
        isOpen={!!openFilePath}
        onClose={() => setOpenFilePath(null)}
        title={openFilePath ? shortPathLabel(openFilePath) : ''}
        subtitle={openFilePath ?? undefined}
        widthClass="max-w-lg"
      >
        {openFilePath && (
          <WorkspaceFileView
            path={openFilePath}
            editPrompt={`I want to discuss the file at ${openFilePath}`}
            onEdit={(prompt) => { setOpenFilePath(null); sendMessage(prompt); }}
          />
        )}
      </InteractiveModal>

      {showMakeRecurring && (
        <div className="mt-1.5 -mb-0.5">
          <button
            type="button"
            onClick={() => onMakeRecurring!(msg.content)}
            className="inline-flex items-center gap-1 text-[10px] font-medium text-primary/70 hover:text-primary hover:bg-primary/5 px-1.5 py-0.5 rounded transition-colors"
            title="Run this on a schedule — chat with the system to set cadence + delivery"
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
 * ADR-272 (2026-05-14): two participants (operator + Reviewer) +
 * user-authored agents, with all orchestration-plumbing roles
 * (assistant / system_agent / system / external) labeled "system" —
 * ambient activity, not a peer participant.
 */
function roleDisplayLabel(role: TPMessage['role'], reviewerPersona?: string | null): string {
  switch (role) {
    case 'user': return 'You';
    case 'reviewer': return reviewerPersona ?? 'Freddie';
    case 'agent': return 'agent';
    // ADR-272: all orchestration-plumbing roles render as ambient "system"
    // activity. The "System Agent" entity label is retired at the cockpit
    // surface; the chat LLM identity persists as substrate, never user-facing.
    case 'assistant':
    case 'system_agent':
    case 'system':
    case 'external':
      return 'system';
    default: return role;
  }
}

/**
 * Routine weight — bubble-chrome row matching renderSystemActivity, with
 * routine-density treatment: smaller text, dimmed, single-line summary.
 * Operator reads routine entries as in-thread system messages alongside
 * conversation, not as background log. Weight controls density inside the
 * bubble, not whether the bubble exists.
 */
function RoutineRow({ msg, reviewerPersona }: { msg: TPMessage; reviewerPersona?: string | null }): JSX.Element {
  const summary =
    msg.narrative?.summary ??
    (msg.content?.split('\n', 1)[0]?.slice(0, 200) ?? '');
  return (
    <div className="text-[12px] rounded-2xl px-3 py-1.5 max-w-[92%] bg-muted/60 rounded-bl-md opacity-80">
      <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-0.5 uppercase">
        {roleDisplayLabel(msg.role, reviewerPersona)}
      </span>
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground flex-1">{summary}</span>
        <span className="text-[10px] text-muted-foreground/50 shrink-0 tabular-nums">
          {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
}

// HousekeepingRow deleted 2026-05-15 (ADR-277). The weight value
// 'housekeeping' was retired because its only emission path (mechanical-
// fire success in invocation_dispatcher.py) was deleted at source.
// Pre-ADR-277 the row rendered at opacity-50 as a paper-cover for the
// missing narrative_digest roll-up the ADR-260/261/262 cleanup deleted.

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
 * the appropriate per-weight wrapper (material / routine).
 * Material rows compose with MessageDispatch's renderer; routine rows
 * have their own minimal slim render (presentation collapse, not a full
 * role-shaped rendering).
 *
 * ADR-277: housekeeping weight retired. Pre-ADR-277 rows tagged
 * housekeeping flowed through HousekeepingRow (opacity-50 dim line);
 * those emissions were deleted at source in invocation_dispatcher.py.
 * Legacy session_messages rows still on-disk with weight='housekeeping'
 * fall through to RoutineRow via the default branch — read-side
 * tolerance for stored historical data.
 */
export function MessageRow({ msg, isLoading, onMakeRecurring }: MessageRowProps): JSX.Element {
  const reviewerPersona = useReviewerPersona();
  const weight = msg.narrative?.weight ?? 'material';
  if (weight === 'material') {
    return <MaterialRow msg={msg} isLoading={isLoading} onMakeRecurring={onMakeRecurring} />;
  }
  // routine + any legacy weight value (e.g. stored 'housekeeping' rows
  // from before ADR-277) → slim routine row
  return <RoutineRow msg={msg} reviewerPersona={reviewerPersona} />;
}
