'use client';

/**
 * MessageDispatch — chat message rendering grammar.
 *
 * Authored by ADR-237 (Round 2 of the ADR-236 frontend cockpit
 * coherence pass). Codifies the role-based dispatch table that was
 * previously inline inside ChatPanel.tsx::NarrativeMessage.
 *
 * Six message shapes, one per `TPMessage.role` (per
 * web/types/desk.ts:117):
 *
 *   user-bubble       — role: 'user'
 *   yarnnn-bubble     — role: 'assistant'
 *   system-event      — role: 'system'
 *   reviewer-verdict  — role: 'reviewer' (ADR-212 full-width card)
 *   agent-bubble      — role: 'agent'
 *   external-event    — role: 'external' (MCP / external write-back)
 *
 * Singular Implementation: this is THE dispatch path for material-weight
 * messages. The weight gate (material / routine / housekeeping) and
 * cross-cutting concerns (authorship chip, Make Recurring affordance)
 * live in MessageRow.tsx — the row wrapper composes around this
 * dispatcher.
 *
 * Inline affordances (InlineToolCall, ToolResultCard, NotificationCard,
 * InlineActionCard) are NOT role-shapes; they're content rendered
 * inside the assistant or user bubble. The dispatch threads their
 * payloads to the correct shape's renderer; their internals are out
 * of scope per ADR-237 D3.
 */

import { Loader2 } from 'lucide-react';
import type { TPMessage } from '@/types/desk';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { ReviewerCard } from './ReviewerCard';
import { MessageBlocks } from './InlineToolCall';
import { ToolResultList } from './ToolResultCard';
import { useReviewerPersona } from '@/lib/reviewer-persona';

// ---------------------------------------------------------------------------
// Onboarding/snapshot meta strippers — kept colocated with the assistant
// bubble renderer because they're presentation-layer text cleanup, not
// shape grammar. Imported by name from chat-surface modules to avoid
// duplication; see SnapshotModal / chat metadata helpers.
// ---------------------------------------------------------------------------

import { stripSnapshotMeta, stripOnboardingMeta } from '@/lib/content-shapes/snapshot';

// ---------------------------------------------------------------------------
// Shape resolution
// ---------------------------------------------------------------------------

export type MessageShape =
  | 'user-bubble'
  | 'yarnnn-bubble'
  | 'system-event'
  | 'reviewer-verdict'
  | 'agent-bubble'
  | 'external-event';

/**
 * Pure function — maps `TPMessage.role` to one of six rendering shapes.
 * Exhaustive over the role enum at web/types/desk.ts:117. New role
 * values require updating this function (TS will catch the omission
 * via the union exhaustiveness check on `r`).
 */
export function resolveMessageShape(msg: TPMessage): MessageShape {
  const r = msg.role;
  if (r === 'user') return 'user-bubble';
  if (r === 'assistant') return 'yarnnn-bubble';
  if (r === 'system') return 'system-event';
  if (r === 'reviewer') return 'reviewer-verdict';
  if (r === 'agent') return 'agent-bubble';
  if (r === 'external') return 'external-event';
  // Exhaustiveness guard — TS narrows `r` to never if all roles handled.
  // Runtime fallback for forward-compatibility if a new role surfaces
  // before MessageDispatch is updated.
  const _exhaustive: never = r;
  return 'yarnnn-bubble';
}

// ---------------------------------------------------------------------------
// Per-shape renderers — internal helpers, not exported.
//
// Each renderer is a small function that takes the message and the
// presentation flags it cares about, and emits the bubble/card content.
// Cross-cutting concerns (weight gating, authorship chip, Make Recurring)
// are handled by MessageRow which wraps the dispatcher's output.
// ---------------------------------------------------------------------------

interface RendererProps {
  msg: TPMessage;
  isLoading: boolean;
}

/**
 * Speech bubble for the operator's own messages. Right-aligned,
 * primary-tinted background. No markdown rendering — operator text
 * is shown verbatim.
 */
function renderUserBubble({ msg }: RendererProps): JSX.Element {
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-primary/10 ml-auto rounded-br-md">
      <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1 uppercase">
        You
      </span>
      <p className="whitespace-pre-wrap">{msg.content}</p>
      {msg.toolResults && msg.toolResults.length > 0 && (
        <ToolResultList results={msg.toolResults} compact />
      )}
    </div>
  );
}

/**
 * YARNNN's reply bubble. Left-aligned, muted background. Markdown-rendered
 * content with onboarding/snapshot meta stripped. Loading-state shimmer
 * when content is empty and isLoading is true. Tool-result list composes
 * below the content.
 */
function renderYarnnnBubble({ msg, isLoading }: RendererProps): JSX.Element {
  const showLoading = !msg.content && isLoading;
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-muted rounded-bl-md">
      <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1 font-brand text-[10px]">
        yarnnn
      </span>
      {msg.blocks && msg.blocks.length > 0 ? (
        <MessageBlocks blocks={msg.blocks} />
      ) : showLoading ? (
        <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
          <Loader2 className="w-3 h-3 animate-spin" />
          Thinking...
        </div>
      ) : (
        <>
          <MarkdownRenderer
            content={stripOnboardingMeta(stripSnapshotMeta(msg.content))}
            compact
          />
          {msg.toolResults && msg.toolResults.length > 0 && (
            <ToolResultList results={msg.toolResults} compact />
          )}
        </>
      )}
    </div>
  );
}

/**
 * Bubble shape for an Agent's authored output (msg.role === 'agent').
 * Left-aligned like YARNNN; label cites the agent's slug from
 * msg.authorAgentSlug for attribution.
 */
function renderAgentBubble({ msg }: RendererProps): JSX.Element {
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-muted rounded-bl-md">
      <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1 font-brand text-[10px]">
        {msg.authorAgentSlug ?? 'agent'}
      </span>
      <p className="whitespace-pre-wrap">{msg.content}</p>
      {msg.toolResults && msg.toolResults.length > 0 && (
        <ToolResultList results={msg.toolResults} compact />
      )}
    </div>
  );
}

/**
 * Reviewer verdict — full-width card per ADR-212. ReviewerCard owns
 * the visual treatment; this renderer just threads metadata + body.
 *
 * ADR-246 D2: component (not plain function) so useReviewerPersona()
 * can resolve the operator-authored persona name from IDENTITY.md.
 */
function ReviewerVerdictRenderer({ msg }: RendererProps): JSX.Element {
  const personaName = useReviewerPersona();
  return <ReviewerCard data={msg.reviewer ?? {}} content={msg.content} personaName={personaName} />;
}

/**
 * System event bubble — minimal styling, system label, plain text.
 * Heavy system content typically routes through msg.notification or
 * msg.system payloads which are handled by NotificationCard /
 * SystemCard at the row level; this renderer is the fallback for
 * a system-role narrative entry that didn't carry a structured
 * payload.
 */
function renderSystemEvent({ msg }: RendererProps): JSX.Element {
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-muted rounded-bl-md">
      <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1 font-brand text-[10px]">
        system
      </span>
      <p className="whitespace-pre-wrap">{msg.content}</p>
    </div>
  );
}

/**
 * External event bubble — MCP write-backs and other off-platform
 * contributions per ADR-169. Same chrome as system events; label
 * cites "external" for legibility.
 */
function renderExternalEvent({ msg }: RendererProps): JSX.Element {
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-muted rounded-bl-md">
      <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1 font-brand text-[10px]">
        external
      </span>
      <p className="whitespace-pre-wrap">{msg.content}</p>
      {msg.toolResults && msg.toolResults.length > 0 && (
        <ToolResultList results={msg.toolResults} compact />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Public dispatch component
// ---------------------------------------------------------------------------

export interface MessageRendererProps {
  msg: TPMessage;
  isLoading: boolean;
}

/**
 * Dispatch component — picks the right per-shape renderer for the
 * message's role and emits the bubble/card content. Wrap with
 * MessageRow.tsx to apply weight gating and cross-cutting concerns.
 */
export function MessageRenderer({ msg, isLoading }: MessageRendererProps): JSX.Element {
  const shape = resolveMessageShape(msg);
  const props: RendererProps = { msg, isLoading };
  switch (shape) {
    case 'user-bubble':
      return renderUserBubble(props);
    case 'yarnnn-bubble':
      return renderYarnnnBubble(props);
    case 'agent-bubble':
      return renderAgentBubble(props);
    case 'reviewer-verdict':
      return <ReviewerVerdictRenderer {...props} />;
    case 'system-event':
      return renderSystemEvent(props);
    case 'external-event':
      return renderExternalEvent(props);
  }
}
