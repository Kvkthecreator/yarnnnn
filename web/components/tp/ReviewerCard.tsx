/**
 * ADR-212 / 2026-04-23: Reviewer verdict card for unified chat thread.
 * ADR-246 / 2026-05-03: surfaces operator-authored persona name from
 * /workspace/review/IDENTITY.md instead of generic "AI Reviewer" label.
 *
 * Renders a role='reviewer' session_messages row as an inline card showing
 * the verdict (approve/reject/defer/observation), the occupant who rendered
 * it (human:<uid>, ai:reviewer-sonnet-v1, reviewer-layer:observed, …), the
 * action it concerned, and a link to the Reviewer detail view for the full
 * audit trail. Content is the reviewer's reasoning — same text persisted to
 * decisions.md.
 *
 * Stream archetype (ADR-198 §3): chat stream is append-only; verdict cards
 * are historical entries, never mutated inline. The operator can click
 * through to the Reviewer detail view (`/agents?agent=reviewer`) for the
 * full decisions stream per ADR-214.
 *
 * ADR-215 Phase 5: deep-link points to `/agents?agent=reviewer` (ADR-214
 * canonical route). The prior `/review` path was retired by ADR-214.
 */

import Link from 'next/link';
import { CheckCircle2, XCircle, Eye, PauseCircle } from 'lucide-react';
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
      return <CheckCircle2 className="w-4 h-4 text-green-600" />;
    case 'reject':
      return <XCircle className="w-4 h-4 text-red-600" />;
    case 'defer':
      return <PauseCircle className="w-4 h-4 text-amber-600" />;
    case 'observation':
    default:
      return <Eye className="w-4 h-4 text-muted-foreground" />;
  }
}

function verdictLabel(verdict: string | undefined) {
  switch (verdict) {
    case 'approve':
      return 'Approved';
    case 'reject':
      return 'Rejected';
    case 'defer':
      return 'Deferred';
    case 'observation':
      return 'Observed';
    default:
      return 'Reviewer';
  }
}

/**
 * ADR-246 D2: when occupant is AI and operator has authored a persona name,
 * surface the persona name ("Simons") rather than the generic "AI Reviewer".
 * Human occupant always shows "You". Skeleton/missing persona falls back to
 * "your Reviewer" (warmer than bare "Reviewer").
 */
function occupantLabel(occupant: string | undefined, personaName?: string | null): string {
  if (!occupant) return personaName ?? 'your Reviewer';
  if (occupant.startsWith('human:')) return 'You';
  if (occupant.startsWith('ai:')) return personaName ?? 'your Reviewer';
  if (occupant === 'reviewer-layer:observed') return `${personaName ?? 'Reviewer'} (observing)`;
  return personaName ?? occupant;
}

export function ReviewerCard({ data, content, personaName }: ReviewerCardProps) {
  const { verdict, occupant, actionType, proposalId } = data;

  return (
    <div
      className={cn(
        'rounded-lg border border-border bg-muted/30 px-3 py-2.5 my-1',
        'animate-in fade-in slide-in-from-bottom-1 duration-150',
      )}
    >
      <div className="flex items-center gap-2 mb-1.5">
        {verdictIcon(verdict)}
        <span className="text-[11px] font-medium">{verdictLabel(verdict)}</span>
        <span className="text-[10px] text-muted-foreground">·</span>
        <span className="text-[10px] text-muted-foreground">{occupantLabel(occupant, personaName)}</span>
        {actionType && (
          <>
            <span className="text-[10px] text-muted-foreground">·</span>
            <span className="text-[10px] font-mono text-muted-foreground">{actionType}</span>
          </>
        )}
      </div>
      {content && (
        <div className="text-[12px] leading-relaxed">
          <MarkdownRenderer content={content} compact />
        </div>
      )}
      {proposalId && (
        <div className="mt-2">
          <Link
            href="/work?tab=decisions"
            className="text-[10px] text-primary hover:underline"
          >
            View decisions log →
          </Link>
        </div>
      )}
    </div>
  );
}
