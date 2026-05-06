'use client';

/**
 * PrinciplesCard — L3 component for /workspace/review/principles.md.
 *
 * Variants:
 *   full    — /workspace page (per-domain thresholds + reject conditions)
 *   compact — context overlay (key threshold per domain, one line each)
 *   headline — cockpit face (summary line)
 *
 * See docs/design/WORKSPACE-COMPONENTS.md.
 */

import { useEffect, useState } from 'react';
import { Scale, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api/client';
import { parse, type PrinciplesData } from '@/lib/content-shapes/principles';
import { cn } from '@/lib/utils';

export type PrinciplesVariant = 'full' | 'compact' | 'headline';

interface PrinciplesCardProps {
  variant?: PrinciplesVariant;
  onEdit?: (prompt: string) => void;
  className?: string;
}

const EDIT_PROMPT = "I want to evolve my Reviewer principles. Show me the current declaration and help me decide what to change — thresholds, reject conditions, domain coverage.";
const SETUP_PROMPT = "Help me author my Reviewer principles — the rules that govern what proposals get approved, rejected, or deferred.";

export function PrinciplesCard({ variant = 'full', onEdit, className }: PrinciplesCardProps) {
  const [data, setData] = useState<PrinciplesData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const file = await api.workspace.getFile('/workspace/review/principles.md');
        if (!cancelled) setData(parse(file.content ?? ''));
      } catch {
        if (!cancelled) setData({ domains: [], hasPrinciples: false, raw: '' });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (variant === 'headline') {
    if (loading || !data?.hasPrinciples) return null;
    const thresholds = data.domains.filter(d => d.autoApproveDisplay);
    return (
      <p className={cn('text-xs text-muted-foreground truncate', className)}>
        {thresholds.length > 0
          ? thresholds.map(d => `${d.name}: auto-approve below ${d.autoApproveDisplay}`).join(' · ')
          : `${data.domains.length} domain${data.domains.length !== 1 ? 's' : ''} declared`}
      </p>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center gap-1.5">
          <Scale className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Principles</h3>
        </div>
        {loading ? (
          <p className="text-xs text-muted-foreground/40">Loading…</p>
        ) : !data?.hasPrinciples ? (
          <p className="text-xs text-muted-foreground/60">
            No judgment framework declared.{' '}
            {onEdit && (
              <button type="button" onClick={() => onEdit(SETUP_PROMPT)}
                className="font-medium underline underline-offset-4 hover:no-underline">
                Set up in chat
              </button>
            )}
          </p>
        ) : (
          <ul className="space-y-0.5">
            {data.domains.map(d => (
              <li key={d.name} className="text-xs text-muted-foreground">
                <span className="capitalize font-medium">{d.name}</span>
                {d.autoApproveDisplay && <span className="text-muted-foreground/70"> · auto-approve below {d.autoApproveDisplay}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  // full
  return (
    <div className={cn('space-y-3', className)}>
      <div>
        <p className="text-sm font-semibold">Reviewer principles</p>
        <p className="text-xs text-muted-foreground mt-0.5">The judgment framework applied to every proposal.</p>
      </div>

      {loading ? (
        <div className="h-16 rounded-md bg-muted/30 animate-pulse" />
      ) : !data?.hasPrinciples ? (
        <div className="rounded-lg border border-dashed border-border/60 px-4 py-4 text-center space-y-2">
          <p className="text-sm text-muted-foreground">No principles declared yet.</p>
          <p className="text-xs text-muted-foreground/60">
            Principles define what gets approved, rejected, or deferred — without them, every proposal waits for manual review.
          </p>
          {onEdit && (
            <button type="button" onClick={() => onEdit(SETUP_PROMPT)}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors mt-1">
              Set up in chat <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {data.domains.map(d => (
            <div key={d.name} className="rounded-lg border border-border/60 bg-card px-3 py-2.5 space-y-1.5">
              <p className="text-xs font-semibold capitalize">{d.name}</p>
              {d.autoApproveDisplay && (
                <p className="text-xs text-muted-foreground">
                  Auto-approve below <span className="font-medium text-foreground">{d.autoApproveDisplay}</span>
                </p>
              )}
              {d.rejectConditions.length > 0 && (
                <div className="space-y-0.5">
                  <p className="text-[10px] text-muted-foreground/60 uppercase tracking-wide">Always reject</p>
                  {d.rejectConditions.slice(0, 3).map((c, i) => (
                    <p key={i} className="text-[11px] text-muted-foreground truncate">· {c}</p>
                  ))}
                  {d.rejectConditions.length > 3 && (
                    <p className="text-[11px] text-muted-foreground/50">· and {d.rejectConditions.length - 3} more</p>
                  )}
                </div>
              )}
            </div>
          ))}
          {onEdit && (
            <button type="button" onClick={() => onEdit(EDIT_PROMPT)}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors">
              Refine in chat <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}
