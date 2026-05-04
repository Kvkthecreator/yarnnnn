/**
 * ADR-212 / 2026-04-23: Reviewer verdict card.
 * ADR-246 / 2026-05-03: operator-authored persona name.
 * ADR-249 / 2026-05-04: conversational voice — verdict chip + persona reasoning
 *   flowing inline, not a bordered form. Observation entries collapsed to one line.
 */

'use client';

import Link from 'next/link';
import { CheckCircle2, XCircle, Eye, PauseCircle } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { ReviewerCardData } from '@/types/desk';
import { cn } from '@/lib/utils';

interface ReviewerCardProps {
  data: ReviewerCardData;
  content: string;
  personaName?: string | null;
}

function verdictChip(verdict: string | undefined, persona: string) {
  const configs: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
    approve: {
      icon: <CheckCircle2 className="w-3 h-3" />,
      label: 'Approved',
      color: 'text-green-600 bg-green-50 border-green-200',
    },
    reject: {
      icon: <XCircle className="w-3 h-3" />,
      label: 'Rejected',
      color: 'text-red-500 bg-red-50 border-red-200',
    },
    defer: {
      icon: <PauseCircle className="w-3 h-3" />,
      label: 'Deferred to you',
      color: 'text-amber-600 bg-amber-50 border-amber-200',
    },
  };
  const c = configs[verdict ?? ''] ?? {
    icon: <Eye className="w-3 h-3" />,
    label: 'Reviewed',
    color: 'text-muted-foreground bg-muted border-border',
  };
  return (
    <span className={cn('inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border text-[10px] font-medium', c.color)}>
      {c.icon}
      {persona} · {c.label}
    </span>
  );
}

function occupantLabel(occupant: string | undefined, personaName?: string | null): string {
  if (!occupant) return personaName ?? 'Reviewer';
  if (occupant.startsWith('human:')) return 'You';
  if (occupant.startsWith('ai:')) return personaName ?? 'Reviewer';
  if (occupant === 'reviewer-layer:observed') return 'Reviewer';
  return personaName ?? occupant;
}

export function ReviewerCard({ data, content, personaName }: ReviewerCardProps) {
  const { verdict, occupant, actionType, proposalId } = data;
  const persona = occupantLabel(occupant, personaName);
  const isObservation = verdict === 'observation' || occupant === 'reviewer-layer:observed';

  // Observation: collapsed to single dim line — housekeeping, not judgment
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

  // Real verdict: verdict chip + persona voice flowing like a conversational reply
  return (
    <div className="my-2 max-w-[92%] space-y-1.5">
      {/* Verdict chip — compact, scannable */}
      <div className="flex items-center gap-2">
        {verdictChip(verdict, persona)}
        {actionType && (
          <span className="text-[10px] font-mono text-muted-foreground/50">{actionType}</span>
        )}
      </div>

      {/* Persona voice — flows like a message, not a form */}
      {content && (
        <div className="text-[13px] leading-relaxed text-foreground/85 pl-0.5">
          <MarkdownRenderer content={content} compact />
        </div>
      )}

      {/* Decisions log link */}
      {proposalId && (
        <Link
          href="/work?tab=decisions"
          className="text-[10px] text-muted-foreground/50 hover:text-primary transition-colors pl-0.5"
        >
          Full audit trail →
        </Link>
      )}
    </div>
  );
}
