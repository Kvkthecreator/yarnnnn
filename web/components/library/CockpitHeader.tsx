'use client';

/**
 * CockpitHeader — Layer 1 (common) of the cockpit, always present.
 *
 * ADR-243 Phase A. Implements the "common - page header" block from
 * the operator's design sketch: mandate-based title + summary on the
 * left, autonomy mode indicator + toggle on the right.
 *
 * Design reference: docs/design/COCKPIT-COMPONENT-DESIGN.md §"Layer 1"
 *
 * NOT a card — full-width, prose-weight header that frames what the
 * operation is trying to achieve and what permissions it carries.
 * Present for every workspace regardless of active bundle.
 *
 * Substrate reads:
 *   /workspace/context/_shared/MANDATE.md  → title + summary
 *   /workspace/context/_shared/AUTONOMY.md → level + ceiling (via useAutonomy)
 *
 * Autonomy posture links to /agents?agent=reviewer&tab=autonomy
 * (ADR-251: Autonomy tab moved to Reviewer surface).
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { MessageSquare, ShieldCheck, ShieldAlert, Info } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useAutonomy } from '@/lib/content-shapes/autonomy';
import { useCockpit } from './CockpitContext';
import { cn } from '@/lib/utils';

const MANDATE_PATH = '/workspace/context/_shared/MANDATE.md';
// ADR-251: Autonomy lives under the Reviewer surface.
const AUTONOMY_EDIT_HREF = '/agents?agent=reviewer&tab=autonomy';

// ---------------------------------------------------------------------------
// Mandate parsing — extract operator-authored title + summary paragraph.
// The mandate file is a mix of scaffolded headings (## Primary Action,
// ## Success Criteria, ## Boundary Conditions) and operator prose. We
// extract: (1) the first operator-authored heading as the title, (2) the
// first prose paragraph as the summary.
// ---------------------------------------------------------------------------

function stripLine(raw: string): string | null {
  let line = raw.replace(/^\s*>+\s?/, '').trim();
  if (!line) return null;
  if (line.startsWith('<!--') && line.endsWith('-->')) return null;
  if (/^[-*_]{3,}$/.test(line)) return null;
  return line;
}

function deriveTitle(content: string): string | null {
  for (const raw of content.split('\n')) {
    const stripped = raw.trim();
    // Look for a # heading that isn't the default "# Mandate" scaffold
    if (stripped.startsWith('# ') && !stripped.toLowerCase().startsWith('# mandate')) {
      return stripped.slice(2).trim();
    }
  }
  return null;
}

function deriveSummary(content: string): string[] {
  const lines = content.split('\n');
  const intentLines: string[] = [];
  let inBlock = false;
  for (const raw of lines) {
    const t = raw.trim();
    if (!t) {
      if (inBlock) break;
      continue;
    }
    if (t.startsWith('#')) {
      if (inBlock) break;
      continue;
    }
    if (t.startsWith('---')) continue;
    const stripped = stripLine(raw);
    if (!stripped) {
      if (inBlock) break;
      continue;
    }
    // Skip skeleton placeholder lines
    if (stripped.includes('_<not yet declared') || stripped.includes('Author here:')) continue;
    intentLines.push(stripped);
    inBlock = true;
  }
  return intentLines;
}

function isSkeleton(content: string): boolean {
  const trimmed = content.trim();
  if (!trimmed) return true;
  if (/^#\s*Mandate\s*$/im.test(trimmed) && trimmed.length < 400) return true;
  if (trimmed.includes('_<not yet declared')) return true;
  if (trimmed.includes('(template)') && trimmed.toLowerCase().includes('mandate')) return true;
  if (trimmed.includes('Author here:') || trimmed.includes('_<not yet')) return true;
  return false;
}

// ---------------------------------------------------------------------------
// Autonomy display
// ---------------------------------------------------------------------------

type AutonomyLevel = 'manual' | 'assisted' | 'bounded_autonomous' | 'autonomous';

function AutonomyBadge({ level, summary }: { level: AutonomyLevel | null; summary: string }) {
  const Icon =
    level === 'autonomous' ? ShieldCheck :
    level === 'bounded_autonomous' ? ShieldAlert :
    level === 'assisted' ? Info :
    null;

  const colorClass =
    level === 'autonomous' ? 'text-primary' :
    level === 'bounded_autonomous' ? 'text-amber-600' :
    level === 'assisted' ? 'text-blue-600' :
    'text-muted-foreground/50';

  return (
    <Link
      href={AUTONOMY_EDIT_HREF}
      className={cn(
        'flex items-center gap-1.5 text-[11px] font-medium hover:opacity-80 transition-opacity',
        colorClass,
      )}
      title={`${summary} — click to view and edit autonomy declaration`}
    >
      {Icon && <Icon className="h-3 w-3 shrink-0" />}
      <span className="capitalize">{(level ?? 'manual').replace(/_/g, ' ')}</span>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// CockpitHeader
// ---------------------------------------------------------------------------

export function CockpitHeader() {
  const { onOpenChatDraft } = useCockpit();
  const { effectiveLevel, summary: autonomySummary, loading: autonomyLoading } = useAutonomy();

  const [mandate, setMandate] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const file = await api.workspace.getFile(MANDATE_PATH);
        if (!cancelled) setMandate(file?.content ?? '');
      } catch {
        if (!cancelled) setMandate('');
      } finally {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (!loaded || autonomyLoading) return null;

  const skeleton = isSkeleton(mandate ?? '');
  const title = skeleton ? null : deriveTitle(mandate ?? '');
  const summaryLines = skeleton ? [] : deriveSummary(mandate ?? '');

  if (skeleton) {
    return (
      <header className="w-full px-6 py-5 border-b border-border/60">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="rounded-md border border-dashed border-amber-300 bg-amber-50/50 px-4 py-3 text-sm text-amber-900">
              <span className="font-medium">Mandate not yet declared.</span>{' '}
              Your mandate is the Primary Action and guardrails YARNNN operates within.{' '}
              <button
                type="button"
                onClick={() => onOpenChatDraft('Help me author my mandate — the Primary Action this workspace is running, success criteria, and boundary conditions.')}
                className="font-medium underline underline-offset-4 hover:no-underline"
              >
                Author in chat
              </button>
            </div>
          </div>
          <AutonomyBadge
            level={effectiveLevel as AutonomyLevel | null}
            summary={autonomySummary}
          />
        </div>
      </header>
    );
  }

  return (
    <header className="w-full px-6 py-5 border-b border-border/60">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Title derived from mandate content */}
          <h1 className="text-xl font-semibold text-foreground truncate">
            {title ?? 'Operation'}
          </h1>
          {/* Summary paragraph */}
          {summaryLines.length > 0 && (
            <p className="mt-1.5 text-sm text-muted-foreground line-clamp-3">
              {summaryLines.join(' ')}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0 mt-0.5">
          {/* Autonomy posture — links to TP Autonomy tab for editing */}
          <AutonomyBadge
            level={effectiveLevel as AutonomyLevel | null}
            summary={autonomySummary}
          />
          {/* Edit mandate shortcut */}
          <button
            type="button"
            onClick={() => onOpenChatDraft('I want to revise my mandate — show me the current declaration and help me sharpen it.')}
            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/50 hover:text-muted-foreground transition-colors"
            title="Edit mandate in chat"
          >
            <MessageSquare className="h-3 w-3" />
          </button>
        </div>
      </div>
    </header>
  );
}
