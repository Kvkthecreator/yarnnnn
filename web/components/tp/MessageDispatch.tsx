'use client';

/**
 * MessageDispatch — chat message rendering grammar.
 *
 * Authored by ADR-237 (Round 2 of the ADR-236 frontend cockpit
 * coherence pass). Codifies the role-based dispatch table that was
 * previously inline inside FeedPanel.tsx::NarrativeMessage.
 *
 * Seven message shapes, one per `TPMessage.role` (per
 * web/types/desk.ts:117). ADR-252 D4 adds system_agent:
 *
 *   user-bubble         — role: 'user'         label: "You"
 *   system-agent-bubble — role: 'system_agent' label: "System Agent"  (ADR-252: execution narration)
 *   system-bubble       — role: 'assistant'    label: "System Agent"  (legacy pre-ADR-252 rows)
 *   system-event        — role: 'system'       label: "background"    (scheduler / back-office)
 *   reviewer-verdict    — role: 'reviewer'     label: persona name    (ADR-258 uniform muted bubble)
 *   agent-bubble        — role: 'agent'        label: agent slug
 *   external-event      — role: 'external'     label: "external"      (MCP / write-back)
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
  | 'system-agent-bubble'
  | 'system-bubble'
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
  if (r === 'system_agent') return 'system-agent-bubble';  // ADR-252 D4
  if (r === 'assistant') return 'system-bubble';           // legacy pre-ADR-252
  if (r === 'system') return 'system-event';
  if (r === 'reviewer') return 'reviewer-verdict';
  if (r === 'agent') return 'agent-bubble';
  if (r === 'external') return 'external-event';
  // Exhaustiveness guard — TS narrows `r` to never if all roles handled.
  // Runtime fallback for forward-compatibility if a new role surfaces
  // before MessageDispatch is updated.
  const _exhaustive: never = r;
  return 'system-bubble';
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
 * System Agent execution narration bubble (role: 'system_agent') — ADR-252 D4.
 * Visually similar to system-bubble but labeled "System Agent". Brief,
 * narration-only content — no judgment, no Reviewer-style assessments.
 * Left-aligned, muted background, slightly de-emphasised vs Reviewer card.
 */
function renderSystemAgentBubble({ msg, isLoading }: RendererProps): JSX.Element {
  const showLoading = !msg.content && isLoading;
  // ADR-258 (revised): System Agent is a participant in the conversation —
  // full chat-bubble visual weight, matching Reviewer/Operator. Same shape
  // as the system bubble (bg-muted, rounded-2xl, persona label) so the
  // operator reads three participants exchanging messages, not background log.
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-muted rounded-bl-md">
      <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1 uppercase">
        System Agent
      </span>
      {showLoading ? (
        <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
          <Loader2 className="w-3 h-3 animate-spin" />
          Running...
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
 * System reply bubble (role: 'assistant'). Legacy pre-ADR-252 rows.
 * Left-aligned, muted background. Labeled "System Agent" for visual
 * consistency — historical rows now render with the same label.
 */
function renderSystemBubble({ msg, isLoading }: RendererProps): JSX.Element {
  const showLoading = !msg.content && isLoading;
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-muted rounded-bl-md">
      <span className="text-[9px] font-medium text-muted-foreground/40 tracking-wider block mb-1 uppercase">
        System Agent
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
 * Reviewer bubble — ADR-258. Reviewer is a chat participant; same
 * bubble shape as other participants, differentiated by persona label.
 * useReviewerPersona() resolves the operator-authored persona name.
 */
function ReviewerBubbleRenderer({ msg }: RendererProps): JSX.Element {
  const personaName = useReviewerPersona();
  return (
    <ReviewerCard
      data={msg.reviewer ?? {}}
      content={msg.content}
      personaName={personaName}
    />
  );
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
    <div className="text-[12px] rounded-lg px-2.5 py-1.5 max-w-[92%] bg-muted/40 border border-border/30">
      <span className="text-[9px] font-mono text-muted-foreground/40 block mb-0.5">
        background:
      </span>
      <p className="whitespace-pre-wrap text-muted-foreground/60">{msg.content}</p>
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
    case 'system-agent-bubble':       // ADR-252 D4: new role='system_agent' rows
      return renderSystemAgentBubble(props);
    case 'system-bubble':             // legacy role='assistant' historical rows
      return renderSystemBubble(props);
    case 'agent-bubble':
      return renderAgentBubble(props);
    case 'reviewer-verdict':
      return <ReviewerBubbleRenderer {...props} />;
    case 'system-event':
      return renderSystemEvent(props);
    case 'external-event':
      return renderExternalEvent(props);
  }
}
