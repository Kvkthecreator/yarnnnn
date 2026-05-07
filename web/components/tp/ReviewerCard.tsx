'use client';

/**
 * ReviewerCard — renders Reviewer narrative entries as chat bubbles.
 *
 * Matches the System Agent bubble shape (rounded-2xl, label, markdown content)
 * but uses a rose tint to distinguish the Reviewer's voice. The persona name
 * (from IDENTITY.md) appears as the label instead of "System Agent".
 *
 * Verdict chips (approve/reject/defer) appear inline when present — compact,
 * scannable, not the dominant visual element.
 *
 * Observation entries (housekeeping) stay collapsed to a single dim line.
 */

import Link from 'next/link';
import { CheckCircle2, XCircle, PauseCircle, Eye } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { ReviewerCardData } from '@/types/desk';
import { cn } from '@/lib/utils';

interface ReviewerCardProps {
  data: ReviewerCardData;
  content: string;
  personaName?: string | null;
}

function occupantLabel(occupant: string | undefined, personaName?: string | null): string {
  if (!occupant) return personaName ?? 'Reviewer';
  if (occupant.startsWith('human:')) return 'You';
  if (occupant.startsWith('ai:')) return personaName ?? 'Reviewer';
  if (occupant === 'reviewer-layer:observed') return 'Reviewer';
  return personaName ?? occupant;
}

function verdictBadge(verdict: string | undefined, persona: string) {
  const configs: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
    approve: {
      icon: <CheckCircle2 className="w-3 h-3" />,
      label: 'Approved',
      color: 'text-green-600',
    },
    reject: {
      icon: <XCircle className="w-3 h-3" />,
      label: 'Rejected',
      color: 'text-red-500',
    },
    defer: {
      icon: <PauseCircle className="w-3 h-3" />,
      label: 'Deferred',
      color: 'text-amber-600',
    },
  };
  const c = configs[verdict ?? ''];
  if (!c) return null;
  return (
    <span className={cn('inline-flex items-center gap-1 text-[10px] font-medium mb-1', c.color)}>
      {c.icon}
      {c.label}
    </span>
  );
}

export function ReviewerCard({ data, content, personaName }: ReviewerCardProps) {
  const { verdict, occupant, actionType, proposalId } = data;
  const persona = occupantLabel(occupant, personaName);
  const isObservation = verdict === 'observation' || occupant === 'reviewer-layer:observed';

  // Observations: collapsed dim line — housekeeping weight
  if (isObservation) {
    return (
      <div className="flex items-center gap-1.5 px-1 py-0.5 my-0.5 opacity-35">
        <Eye className="w-3 h-3 text-muted-foreground shrink-0" />
        <span className="text-[10px] text-muted-foreground">
          {persona} observed{actionType ? ` · ${actionType}` : ''}
        </span>
      </div>
    );
  }

  // All other entries: bubble matching System Agent shape, rose-tinted
  return (
    <div className="text-[13px] rounded-2xl px-3 py-2 max-w-[92%] bg-rose-50/60 dark:bg-rose-950/20 rounded-bl-md border border-rose-100/60 dark:border-rose-900/30">
      {/* Label row: persona name + optional verdict badge */}
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[9px] font-medium text-rose-400/70 dark:text-rose-400/50 tracking-wider uppercase">
          {persona}
        </span>
        {verdictBadge(verdict, persona)}
        {actionType && verdict && verdict !== 'addressed' && verdict !== 'heartbeat' && (
          <span className="text-[10px] font-mono text-muted-foreground/40">{actionType}</span>
        )}
      </div>

      {/* Content */}
      {content && (
        <MarkdownRenderer content={content} compact />
      )}

      {/* Audit trail link for proposal verdicts */}
      {proposalId && (
        <Link
          href="/work?tab=decisions"
          className="text-[10px] text-muted-foreground/40 hover:text-rose-400 transition-colors mt-1 block"
        >
          Audit trail →
        </Link>
      )}
    </div>
  );
}
