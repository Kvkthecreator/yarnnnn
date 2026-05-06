'use client';

/**
 * IdentityBrandCard — L3 component for IDENTITY.md + BRAND.md.
 *
 * Merged because both are operator-authored prose with no structured
 * schema, identical empty states, and always co-located on the same
 * surfaces. See docs/design/WORKSPACE-COMPONENTS.md.
 *
 * Variants:
 *   full    — /workspace page
 *   compact — context overlay (summary line)
 */

import { useEffect, useState } from 'react';
import { User, ArrowRight } from 'lucide-react';
import { api } from '@/lib/api/client';
import { parse as parseIdentity, type IdentityData } from '@/lib/content-shapes/identity';
import { parse as parseBrand, type BrandData } from '@/lib/content-shapes/brand';
import { cn } from '@/lib/utils';

export type IdentityBrandVariant = 'full' | 'compact';

interface IdentityBrandCardProps {
  variant?: IdentityBrandVariant;
  onEdit?: (prompt: string) => void;
  className?: string;
}

const IDENTITY_PROMPT = "Help me author my identity file — who I am as an operator, my domain, and how agents should represent me.";
const BRAND_PROMPT = "Help me define my brand voice — the tone, style, and conventions I want all produced content to follow.";

export function IdentityBrandCard({ variant = 'full', onEdit, className }: IdentityBrandCardProps) {
  const [identity, setIdentity] = useState<IdentityData | null>(null);
  const [brand, setBrand] = useState<BrandData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const [id, br] = await Promise.allSettled([
        api.workspace.getFile('/workspace/context/_shared/IDENTITY.md'),
        api.workspace.getFile('/workspace/context/_shared/BRAND.md'),
      ]);
      if (cancelled) return;
      setIdentity(id.status === 'fulfilled' ? parseIdentity(id.value.content ?? '') : { excerpt: null, isEmpty: true });
      setBrand(br.status === 'fulfilled' ? parseBrand(br.value.content ?? '') : { excerpt: null, isEmpty: true });
      setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const bothEmpty = identity?.isEmpty && brand?.isEmpty;

  if (variant === 'compact') {
    return (
      <div className={cn('space-y-1.5', className)}>
        <div className="flex items-center gap-1.5">
          <User className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Identity & Brand</h3>
        </div>
        {loading ? (
          <p className="text-xs text-muted-foreground/40">Loading…</p>
        ) : bothEmpty ? (
          <p className="text-xs text-muted-foreground/60">Not yet set.</p>
        ) : (
          <p className="text-xs text-muted-foreground">
            Identity: <span className={identity?.isEmpty ? 'italic text-muted-foreground/50' : 'font-medium text-foreground'}>
              {identity?.isEmpty ? 'not set' : 'authored'}
            </span>
            {' · '}
            Brand: <span className={brand?.isEmpty ? 'italic text-muted-foreground/50' : 'font-medium text-foreground'}>
              {brand?.isEmpty ? 'not set' : 'authored'}
            </span>
          </p>
        )}
      </div>
    );
  }

  // full
  return (
    <div className={cn('space-y-3', className)}>
      <div>
        <p className="text-sm font-semibold">Identity & Brand</p>
        <p className="text-xs text-muted-foreground mt-0.5">How the system understands you and how output should sound.</p>
      </div>

      {loading ? (
        <div className="h-12 rounded-md bg-muted/30 animate-pulse" />
      ) : bothEmpty ? (
        <div className="rounded-lg border border-dashed border-border/60 px-4 py-4 text-center space-y-2">
          <p className="text-sm text-muted-foreground">Not yet set up.</p>
          <p className="text-xs text-muted-foreground/60">
            Identity tells agents who you are. Brand tells them how output should sound.
          </p>
          {onEdit && (
            <button type="button" onClick={() => onEdit(IDENTITY_PROMPT)}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors mt-1">
              Set up in chat <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          {/* Identity */}
          <div className="rounded-lg border border-border/60 bg-card px-3 py-2.5">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide mb-1">Identity</p>
            {identity?.isEmpty ? (
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground/60 italic">Not yet authored</p>
                {onEdit && (
                  <button type="button" onClick={() => onEdit(IDENTITY_PROMPT)}
                    className="text-xs text-primary hover:text-primary/80 transition-colors">
                    Set up →
                  </button>
                )}
              </div>
            ) : (
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs text-muted-foreground line-clamp-2">{identity?.excerpt}</p>
                {onEdit && (
                  <button type="button" onClick={() => onEdit(IDENTITY_PROMPT)}
                    className="shrink-0 text-xs text-primary hover:text-primary/80 transition-colors">
                    Refine →
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Brand */}
          <div className="rounded-lg border border-border/60 bg-card px-3 py-2.5">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide mb-1">Brand voice</p>
            {brand?.isEmpty ? (
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground/60 italic">Not yet authored</p>
                {onEdit && (
                  <button type="button" onClick={() => onEdit(BRAND_PROMPT)}
                    className="text-xs text-primary hover:text-primary/80 transition-colors">
                    Set up →
                  </button>
                )}
              </div>
            ) : (
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs text-muted-foreground line-clamp-2">{brand?.excerpt}</p>
                {onEdit && (
                  <button type="button" onClick={() => onEdit(BRAND_PROMPT)}
                    className="shrink-0 text-xs text-primary hover:text-primary/80 transition-colors">
                    Refine →
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
