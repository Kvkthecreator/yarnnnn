/**
 * ADR-212 / 2026-04-23: Reviewer verdict card for unified chat thread.
 * ADR-246 / 2026-05-03: operator-authored persona name from IDENTITY.md.
 * ADR-249 / 2026-05-04: visual separation from YARNNN — distinct identity,
 *   summary-first with collapsed reasoning, demoted observation entries.
 *
 * Three visual tiers:
 *   1. observation (reviewer-layer:observed) — single dim line, no expansion
 *   2. real verdict (approve/reject/defer) — verdict chip + one-line summary
 *      + collapsed "Full reasoning" disclosure
 *   3. approve specifically — green left border to signal action completed
 */

'use client';

import { useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, XCircle, Eye, PauseCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import type { ReviewerCardData } from '@/types/desk';
import { cn } from '@/lib/utils';

interface ReviewerCardProps {
  data: ReviewerCardData;
  content: string;
  /** ADR-246: operator-authored persona name from /workspace/review/IDENTITY.md */
  personaName?: string | null;
}

function verdictIcon(verdict: string | undefined) {
  switch (verdict) {
    case 'approve':
      return <CheckCircle2 className="w-3.5 h-3.5 text-green-600 shrink-0" />;
    case 'reject':
      return <XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />;
    case 'defer':
      return <PauseCircle className="w-3.5 h-3.5 text-amber-500 shrink-0" />;
    case 'observation':
    default:
      return <Eye className="w-3 h-3 text-muted-foreground/50 shrink-0" />;
  }
}

function verdictLabel(verdict: string | undefined) {
  switch (verdict) {
    case 'approve': return 'Approved';
    case 'reject':  return 'Rejected';
    case 'defer':   return 'Deferred';
    case 'observation': return 'Observed';
    default: return 'Reviewed';
  }
}

function borderColor(verdict: string | undefined) {
  switch (verdict) {
    case 'approve': return 'border-l-green-500';
    case 'reject':  return 'border-l-red-400';
    case 'defer':   return 'border-l-amber-400';
    default:        return 'border-l-border';
  }
}

function occupantLabel(occupant: string | undefined, personaName?: string | null): string {
  if (!occupant) return personaName ?? 'Reviewer';
  if (occupant.startsWith('human:')) return 'You';
  if (occupant.startsWith('ai:')) return personaName ?? 'Reviewer';
  if (occupant === 'reviewer-layer:observed') return 'Reviewer';
  return personaName ?? occupant;
}

/** Extract first substantive sentence for the summary line. */
function extractSummary(content: string): string {
  if (!content) return '';
  // Strip markdown headers, bold markers, leading whitespace
  const cleaned = content
    .replace(/^#+\s+/gm, '')
    .replace(/\*\*/g, '')
    .replace(/\n+/g, ' ')
    .trim();
  // First sentence — stop at period/exclamation/question or 160 chars
  const match = cleaned.match(/^(.{20,160}?[.!?])(?:\s|$)/);
  if (match) return match[1];
  return cleaned.slice(0, 140) + (cleaned.length > 140 ? '…' : '');
}

export function ReviewerCard({ data, content, personaName }: ReviewerCardProps) {
  const { verdict, occupant, actionType, proposalId } = data;
  const [expanded, setExpanded] = useState(false);

  const isObservation = verdict === 'observation' || occupant === 'reviewer-layer:observed';
  const persona = occupantLabel(occupant, personaName);
  const summary = extractSummary(content);

  // Tier 1: observation — single dim line, no expansion
  if (isObservation) {
    return (
      <div className="flex items-center gap-1.5 px-1 py-0.5 my-0.5 opacity-40">
        <Eye className="w-3 h-3 text-muted-foreground shrink-0" />
        <span className="text-[10px] text-muted-foreground">
          {persona} observed
          {actionType ? ` · ${actionType}` : ''}
        </span>
      </div>
    );
  }

  // Tier 2 + 3: real verdict
  return (
    <div
      className={cn(
        'rounded-r-lg border border-l-2 border-border bg-background',
        'px-3 py-2 my-1.5 max-w-[94%]',
        'animate-in fade-in slide-in-from-bottom-1 duration-150',
        borderColor(verdict),
      )}
    >
      {/* Header row: persona name (distinct from YARNNN) */}
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[9px] font-semibold text-muted-foreground/60 uppercase tracking-widest">
          {persona}
        </span>
        <span className="text-muted-foreground/30 text-[9px]">·</span>
        {verdictIcon(verdict)}
        <span className="text-[11px] font-semibold text-foreground">{verdictLabel(verdict)}</span>
        {actionType && (
          <>
            <span className="text-muted-foreground/30 text-[9px]">·</span>
            <span className="text-[10px] font-mono text-muted-foreground/60">{actionType}</span>
          </>
        )}
      </div>

      {/* Summary — always visible */}
      {summary && (
        <p className="text-[12px] text-foreground/80 leading-relaxed mb-1.5">
          {summary}
        </p>
      )}

      {/* Expand/collapse full reasoning */}
      {content && content.length > summary.length + 10 && (
        <button
          onClick={() => setExpanded(e => !e)}
          className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors mb-1"
        >
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? 'Hide reasoning' : 'Full reasoning'}
        </button>
      )}

      {expanded && content && (
        <div className="text-[11px] leading-relaxed text-muted-foreground border-t border-border/50 pt-2 mt-1">
          <MarkdownRenderer content={content} compact />
        </div>
      )}

      {/* Footer: decisions log link */}
      {proposalId && (
        <div className="mt-1.5 pt-1.5 border-t border-border/40">
          <Link
            href="/work?tab=decisions"
            className="text-[10px] text-primary/70 hover:text-primary transition-colors"
          >
            View decisions log →
          </Link>
        </div>
      )}
    </div>
  );
}
