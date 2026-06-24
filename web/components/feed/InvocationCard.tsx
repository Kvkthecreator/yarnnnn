/**
 * InvocationCard — Feed timeline group card (ADR-289).
 *
 * One card per `metadata.invocation_id` — every session_messages row
 * produced during one Reviewer cycle is rendered inside this card.
 * Per ADR-289 D6 the FE groups rows sharing invocation_id; per Option
 * B (operator question hoisted to its own marker), the card contains
 * the Reviewer verdict body + 0..N consequential System Agent action
 * narrations. The user's question — when this is an addressed cycle —
 * renders upstream as an OperatorEventMarker, not inside the card.
 *
 * Visual shape: NOT a chat bubble (ADR-289 D1). Typed operations event
 * with a header strip (pulse + persona + timestamp + summary count),
 * a body preview, and an expand/collapse for action details.
 *
 * Inline proposal chip support preserved on action rows carrying
 * proposalId per ADR-258 D2.
 */

'use client';

import { useState } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Clock,
  Zap,
  Bell,
  Repeat,
  MessageCircle,
} from 'lucide-react';
import type { NarrativePulse } from '@/types/desk';
import type { InvocationCardUnit } from '@/lib/feed-grouping';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { InlineProposalChipById } from '@/components/tp/ProposalCard';
import { stripSnapshotMeta, stripOnboardingMeta } from '@/lib/content-shapes/snapshot';
import { useReviewerPersona } from '@/lib/reviewer-persona';
import { cn } from '@/lib/utils';

interface InvocationCardProps {
  unit: InvocationCardUnit;
}

// Pulse → header label + icon mapping.
function pulseLabelIcon(pulse: NarrativePulse) {
  switch (pulse) {
    case 'periodic':
      return { label: 'scheduled', Icon: Repeat };
    case 'reactive':
      return { label: 'responded to a change', Icon: Zap };
    case 'addressed':
      return { label: 'you asked', Icon: MessageCircle };
    case 'heartbeat':
      return { label: 'routine check', Icon: Bell };
    default:
      return { label: 'ran', Icon: Clock };
  }
}

function narrationForAction(message: { role: string; content: string; narrative?: { proposalId?: string } }) {
  // The body text the BE emits already names the verb and substrate.
  // We just clean the snapshot meta wrappers and return.
  return stripOnboardingMeta(stripSnapshotMeta(message.content));
}

export function InvocationCard({ unit }: InvocationCardProps) {
  const personaName = useReviewerPersona();
  const [expanded, setExpanded] = useState(false);

  const time = unit.timestamp.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  const { label: pulseLabel, Icon: PulseIcon } = pulseLabelIcon(unit.pulse);
  const actionCount = unit.actions.length;
  const hasVerdict = !!unit.verdict;

  // Verdict body — Reviewer reasoning text. Strip envelope wrappers.
  const verdictBody = hasVerdict
    ? stripOnboardingMeta(stripSnapshotMeta(unit.verdict!.content))
    : '';

  // Summary line for collapsed view: "approved 1, fired 2 trackers, stood down"
  // — derived from verdict.reviewer.verdict + action count.
  const verdictTag = unit.verdict?.reviewer?.verdict;
  const collapsedHint =
    actionCount > 0
      ? `${actionCount} action${actionCount === 1 ? '' : 's'}`
      : 'no actions';

  return (
    <div className="my-1.5 rounded-md border border-border/60 bg-muted/30 overflow-hidden">
      {/* Header strip — clickable to toggle expansion */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 hover:bg-muted/50 transition-colors text-left"
        aria-expanded={expanded}
      >
        {expanded ? (
          <ChevronDown className="w-3 h-3 shrink-0 text-muted-foreground/60" />
        ) : (
          <ChevronRight className="w-3 h-3 shrink-0 text-muted-foreground/60" />
        )}
        <PulseIcon className="w-3 h-3 shrink-0 text-muted-foreground/70" />
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
          {personaName ?? 'Reviewer'} · {pulseLabel}
        </span>
        <span className="text-[10px] text-muted-foreground/50 tabular-nums">
          {time}
        </span>
        <span className="flex-1" />
        {verdictTag && (
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
            {verdictTag}
          </span>
        )}
        <span className="text-[10px] text-muted-foreground/50">
          {collapsedHint}
        </span>
      </button>

      {/* Verdict body — always shown when present (the operator-relevant
          reasoning), even when actions are collapsed. */}
      {hasVerdict && (
        <div className="px-2.5 py-1.5 border-t border-border/40 text-[13px] text-foreground/90">
          <MarkdownRenderer content={verdictBody} compact />
        </div>
      )}

      {/* Actions block — collapsible. */}
      {expanded && actionCount > 0 && (
        <div className="px-2.5 py-1.5 border-t border-border/40 bg-background/40">
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50 mb-1">
            {actionCount} action{actionCount === 1 ? '' : 's'}
          </div>
          <ul className="space-y-1">
            {unit.actions.map((action) => {
              const narration = narrationForAction(action);
              const proposalId = action.narrative?.proposalId;
              const actionTime = action.timestamp.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              });
              return (
                <li key={action.id} className="flex items-start gap-2 text-[12px]">
                  <span className="text-muted-foreground/40 mt-0.5">•</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-foreground/80">
                      <MarkdownRenderer content={narration} compact />
                    </div>
                    {proposalId && (
                      <div className="mt-0.5">
                        <InlineProposalChipById proposalId={proposalId} />
                      </div>
                    )}
                  </div>
                  <span className="text-[10px] text-muted-foreground/40 tabular-nums shrink-0">
                    {actionTime}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
