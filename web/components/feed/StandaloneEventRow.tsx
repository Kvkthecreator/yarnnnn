/**
 * StandaloneEventRow — Feed timeline event row for rows without an
 * invocation_id (ADR-289).
 *
 * Covers: pre-ADR-289 legacy rows lacking invocation_id, the rare
 * `_emit_system_narrative` operator-relevant events (balance exhausted,
 * spend ceiling, capability transitions, Reviewer exception), and
 * future event classes that don't belong to a cycle (e.g. workspace-
 * scoped notifications).
 *
 * Compact typed-row treatment — NOT a chat bubble. The Feed surface
 * does not borrow chat grammar for operations activity (ADR-289 D1).
 *
 * Inline proposal chip support preserved when the row carries a
 * proposalId in its narrative envelope (ADR-258 D2).
 */

'use client';

import { AlertCircle, FileText, Zap, Info } from 'lucide-react';
import type { TPMessage } from '@/types/desk';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { InlineProposalChipById } from '@/components/tp/ProposalCard';
import { stripSnapshotMeta, stripOnboardingMeta } from '@/lib/content-shapes/snapshot';

interface StandaloneEventRowProps {
  message: TPMessage;
}

function iconForRole(role: TPMessage['role']) {
  if (role === 'reviewer') return Info;
  if (role === 'system_agent' || role === 'assistant') return Zap;
  if (role === 'external') return FileText;
  if (role === 'system') return Info;
  return AlertCircle;
}

function labelForRole(role: TPMessage['role']): string {
  if (role === 'user') return 'You';
  if (role === 'reviewer') return 'Reviewer';
  if (role === 'agent') return 'agent';
  // Orchestration-plumbing roles all render as "system" per ADR-272.
  return 'system';
}

export function StandaloneEventRow({ message }: StandaloneEventRowProps) {
  const Icon = iconForRole(message.role);
  const label = labelForRole(message.role);
  const time = message.timestamp.toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  const content = stripOnboardingMeta(stripSnapshotMeta(message.content));
  const proposalId = message.narrative?.proposalId;

  return (
    <div className="flex items-start gap-2 px-2 py-1 my-0.5 text-[12px]">
      <Icon className="w-3 h-3 mt-0.5 shrink-0 text-muted-foreground/60" />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 mb-0.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
            {label}
          </span>
          <span className="text-[10px] text-muted-foreground/50 tabular-nums">
            {time}
          </span>
        </div>
        <div className="text-foreground/80">
          <MarkdownRenderer content={content} compact />
        </div>
        {proposalId && (
          <div className="mt-1">
            <InlineProposalChipById proposalId={proposalId} />
          </div>
        )}
      </div>
    </div>
  );
}
