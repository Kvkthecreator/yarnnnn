'use client';

/**
 * MessageDispatch — Conversation surface bubble grammar (ADR-289 Phase 2 scope).
 *
 * Originally authored by ADR-237 (Round 2 of the ADR-236 frontend cockpit
 * coherence pass). Collapsed to four shapes by ADR-272 Phase 2 (2026-05-14).
 * **Scoped to the Conversation surface by ADR-289 D9** — the Feed surface
 * uses typed-event row components (InvocationCard, OperatorEventMarker,
 * StandaloneEventRow, DaySeparator), not bubbles.
 *
 * Four message shapes, mapping `TPMessage.role` to one of:
 *
 *   user-bubble      — role: 'user'        label: "You"         (operator)
 *   reviewer-bubble  — role: 'freddie'    label: persona name  (judgment seat)
 *   agent-bubble     — role: 'agent'       label: agent slug    (user-authored Agent)
 *   system-activity  — role: 'system_agent' | 'assistant' | 'system' | 'external'
 *                      label: "system" — orchestration plumbing narration
 *                      (System Agent's per-action narrations during an
 *                      addressed Reviewer cycle render here as compact rows
 *                      alongside the conversation; addressed-pulse only).
 *
 * The ADR-272 collapse: System Agent dissolved as a cockpit entity. The
 * orchestration LLM identity persists as substrate behind /feed but no
 * longer renders as a peer participant. All non-judgment / non-Agent
 * narration surfaces as ambient activity in a single shape, not three
 * separate ones (system-agent-bubble + system-bubble + system-event).
 *
 * ADR-289 D9 (softened interpretation post-Phase-2-impl): system-activity
 * shape is preserved on the Conversation surface for addressed-cycle
 * narrations (Reviewer-directed action callouts during the operator's
 * turn). Pure operations activity — autonomous wakes, mechanical
 * recurrences, orphan system events — is filtered out upstream by
 * ConversationPanel's `filterAddressedMessages` call and never reaches
 * this dispatcher.
 *
 * Singular Implementation: this is THE dispatch path for the Conversation
 * surface. Weight gating + cross-cutting concerns (authorship chip,
 * Make Recurring affordance) live in MessageRow.tsx — the row wrapper
 * composes around this dispatcher.
 */

import { Loader2 } from 'lucide-react';
import type { TPMessage, MessageBlock } from '@/types/desk';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { FreddieCard } from './FreddieCard';
import { MessageBlocks } from './InlineToolCall';
import { ToolResultList } from './ToolResultCard';
import { InlineProposalChipById } from './ProposalCard';
import { useFreddiePersona } from '@/lib/freddie-persona';

import { stripSnapshotMeta, stripOnboardingMeta } from '@/lib/content-shapes/snapshot';

// ---------------------------------------------------------------------------
// Shape resolution
// ---------------------------------------------------------------------------

export type MessageShape =
  | 'user-bubble'
  | 'reviewer-bubble'
  | 'agent-bubble'
  | 'system-activity';

/**
 * Pure function — maps `TPMessage.role` to one of four rendering shapes
 * per ADR-272.
 *
 * Roles that resolve to `system-activity` (ambient): 'system_agent',
 * 'assistant' (legacy pre-ADR-252), 'system' (scheduler / back-office),
 * 'external' (MCP write-backs per ADR-169). All collapse into a single
 * de-emphasised activity row — no peer-participant bubble shape, no
 * "System Agent" entity framing.
 */
export function resolveMessageShape(msg: TPMessage): MessageShape {
  const r = msg.role;
  if (r === 'user') return 'user-bubble';
  if (r === 'freddie') return 'reviewer-bubble';
  if (r === 'agent') return 'agent-bubble';
  // All orchestration-shaped roles collapse to ambient activity post-ADR-272.
  // r ∈ {'system_agent', 'assistant', 'system', 'external'}
  return 'system-activity';
}

// ---------------------------------------------------------------------------
// Per-shape renderers — internal helpers, not exported.
// ---------------------------------------------------------------------------

interface RendererProps {
  msg: TPMessage;
  isLoading: boolean;
}

/**
 * Speech bubble for the operator's own messages. Right-aligned,
 * primary-tinted background.
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
 * Bubble shape for a user-authored Agent's authored output
 * (msg.role === 'agent'). Left-aligned; persona label cites the agent's
 * slug from msg.authorAgentSlug.
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
 * Reviewer bubble — full-weight chat-participant shape per ADR-258 /
 * ADR-272. Reviewer is the only systemic judgment entity in the cockpit
 * post-ADR-272. Persona label resolved via useFreddiePersona() from
 * /workspace/persona/IDENTITY.md.
 */
function ReviewerBubbleRenderer({ msg }: RendererProps): JSX.Element {
  const personaName = useFreddiePersona();
  // ADR-399: the turn artifact — reasoning + tool entries in the order they
  // happened, live (SSE) and settled (reconstructed from tool_history).
  const process = (msg.blocks ?? [])
    .filter((b) => b.type === 'tool_call' || b.type === 'thinking')
    .map((b): import('./FreddieCard').FreddieProcessItem => {
      if (b.type === 'thinking') {
        return { kind: 'thinking', text: b.content };
      }
      const tb = b as Extract<MessageBlock, { type: 'tool_call' }>;
      return {
        kind: 'tool',
        name: tb.tool,
        detail: typeof tb.input?.summary === 'string' ? (tb.input.summary as string) : '',
        status: tb.status,
        result: tb.result?.data && typeof (tb.result.data as Record<string, unknown>).message === 'string'
          ? String((tb.result.data as Record<string, unknown>).message)
          : '',
      };
    });
  return (
    <FreddieCard
      data={msg.reviewer ?? {}}
      content={msg.content}
      personaName={personaName}
      process={process.length > 0 ? process : undefined}
    />
  );
}

/**
 * System-activity row — ADR-272 Phase 2.
 *
 * Renders narration from any orchestration-plumbing source: deterministic
 * dispatch (execution_router regex), Reviewer-directed action narration
 * (FireInvocation completed, WriteFile written, ProposeAction emitted),
 * mechanical recurrence completions, scheduler events, MCP write-backs.
 *
 * Same chrome as agent-bubble / user-bubble (rounded-2xl, bg-muted,
 * px-3 py-2 padding) so the operator reads system activity as in-thread
 * content alongside conversation, not as background log. Persona label
 * cues semantics: "system" identifies the source as ambient orchestration
 * (not a chat participant with standing intent), but the row itself
 * carries normal visual weight.
 *
 * If the narration carries a proposalId (e.g. Reviewer fired ProposeAction
 * during a heartbeat / cron-fired wake), the proposal chip renders inline
 * so the operator can tap-to-inspect-and-act directly from the feed.
 */
function renderSystemActivity({ msg, isLoading }: RendererProps): JSX.Element {
  const showLoading = !msg.content && isLoading;
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-muted rounded-bl-md">
      <span className="text-[9px] font-medium text-muted-foreground/50 tracking-wider block mb-1 uppercase">
        system
      </span>
      {msg.blocks && msg.blocks.length > 0 ? (
        <MessageBlocks blocks={msg.blocks} />
      ) : showLoading ? (
        <div className="flex items-center gap-1.5 text-muted-foreground text-xs">
          <Loader2 className="w-3 h-3 animate-spin" />
          Running…
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
          {msg.narrative?.proposalId && (
            <InlineProposalChipById proposalId={msg.narrative.proposalId} />
          )}
        </>
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
    case 'reviewer-bubble':
      return <ReviewerBubbleRenderer {...props} />;
    case 'agent-bubble':
      return renderAgentBubble(props);
    case 'system-activity':
      return renderSystemActivity(props);
  }
}
