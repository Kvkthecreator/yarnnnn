'use client';

/**
 * MandateCard — L3 component for /workspace/context/_shared/MANDATE.md.
 *
 * Surface-agnostic. Renders parsed MandateData at three densities:
 *   full    — /workspace page
 *   compact — context overlay
 *   headline — cockpit face (future)
 *
 * See docs/design/WORKSPACE-COMPONENTS.md for the full catalog.
 */

import { useEffect, useState } from 'react';
import { Compass, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api/client';
import { parse, type MandateData } from '@/lib/content-shapes/mandate';
import { cn } from '@/lib/utils';

export type MandateVariant = 'full' | 'compact' | 'headline';

interface MandateCardProps {
  variant?: MandateVariant;
  /** Called when the operator clicks an edit CTA. Receives a seeded prompt. */
  onEdit?: (prompt: string) => void;
  className?: string;
}

const EDIT_PROMPT = "I want to revise my mandate. Show me the current Primary Action declaration and help me sharpen it — success criteria and boundary conditions too.";
const SETUP_PROMPT = "Help me author my mandate — the Primary Action I'm running, my success criteria, and the boundary conditions I want to enforce.";

export function MandateCard({ variant = 'full', onEdit, className }: MandateCardProps) {
  const [data, setData] = useState<MandateData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const file = await api.workspace.getFile('/workspace/context/_shared/MANDATE.md');
        if (!cancelled) setData(parse(file.content ?? ''));
      } catch {
        if (!cancelled) setData({ primaryAction: null, successCriteria: [], boundaryCount: 0, isEmpty: true });
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (variant === 'headline') {
    if (loading) return <span className="text-xs text-muted-foreground/40">Loading…</span>;
    return (
      <p className={cn('text-sm truncate', className)}>
        {data?.primaryAction ?? <span className="text-muted-foreground/50 italic">Mandate not set</span>}
      </p>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center gap-1.5">
          <Compass className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Mandate</h3>
        </div>
        {loading ? (
          <p className="text-xs text-muted-foreground/40">Loading…</p>
        ) : data?.isEmpty ? (
          <p className="text-xs text-muted-foreground/60">
            Not yet set.{' '}
            {onEdit && (
              <button type="button" onClick={() => onEdit(SETUP_PROMPT)}
                className="font-medium underline underline-offset-4 hover:no-underline">
                Set up in chat
              </button>
            )}
          </p>
        ) : (
          <p className="text-sm leading-snug line-clamp-2">{data?.primaryAction}</p>
        )}
      </div>
    );
  }

  // full
  return (
    <div className={cn('space-y-3', className)}>
      <div>
        <p className="text-sm font-semibold">Mandate</p>
        <p className="text-xs text-muted-foreground mt-0.5">What this workspace is running toward.</p>
      </div>

      {loading ? (
        <div className="h-10 rounded-md bg-muted/30 animate-pulse" />
      ) : data?.isEmpty ? (
        <div className="rounded-lg border border-dashed border-border/60 px-4 py-4 text-center space-y-2">
          <p className="text-sm text-muted-foreground">No mandate declared yet.</p>
          <p className="text-xs text-muted-foreground/60">
            The mandate is the single goal this workspace is running toward — your Primary Action, success criteria, and guardrails.
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
          <p className="text-sm leading-relaxed">{data?.primaryAction}</p>

          {(data?.successCriteria.length ?? 0) > 0 && (
            <div className="space-y-1">
              <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Success criteria</p>
              <ul className="space-y-0.5">
                {data!.successCriteria.map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className="mt-1 h-1 w-1 rounded-full bg-muted-foreground/40 shrink-0" />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(data?.boundaryCount ?? 0) > 0 && (
            <p className="text-[11px] text-muted-foreground/60">
              {data!.boundaryCount} boundary condition{data!.boundaryCount !== 1 ? 's' : ''} declared
            </p>
          )}

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
