'use client';

/**
 * MandateCard — L3 component for /workspace/constitution/MANDATE.md.
 *
 * Surface-agnostic. Renders parsed MandateData at three densities:
 *   full    — /workspace page
 *   compact — context overlay
 *   headline — cockpit face
 *
 * ADR-266 D4: schema-met vs schema-absent rendering paths. When the parser
 * extracts a one-sentence Primary Action (per the D3 schema), the card
 * shows a structured callout. When the section is absent or runs longer
 * than one sentence, the card degrades gracefully — first-sentence
 * excerpt + hint + "View full ▾" — never dumps the full file content.
 *
 * ADR-266 D5: extracted prose is cleaned through stripInlineMarkdown +
 * stripWorkspacePaths so `**bold**` and `/workspace/...` paths never
 * leak as literal characters in the rendered card.
 *
 * ADR-266 D7: most-recent revision metadata (ADR-209 Phase 4) surfaced
 * as a single muted line below the card title.
 *
 * ADR-266 D8: when the parent passes `data` + `lastRevision` props (from
 * the bundled /workspace/setup-bundle endpoint), the card skips its own
 * fetch. When neither is provided (legacy reuse on /agents), the card
 * self-fetches as before.
 *
 * See docs/design/WORKSPACE-COMPONENTS.md for the full catalog.
 */

import { useEffect, useMemo, useState } from 'react';
import { Compass, ArrowRight, ChevronDown, ChevronRight } from 'lucide-react';
import { api } from '@/lib/api/client';
import { parse, type MandateData } from '@/lib/content-shapes/mandate';
import { cleanProse, firstSentence } from '@/lib/content-shapes/_render';
import { cn } from '@/lib/utils';
import type { WorkspaceRevisionSummary } from '@/types';
import { RevisionFootnote } from './RevisionFootnote';

export type MandateVariant = 'full' | 'compact' | 'headline';

interface MandateCardProps {
  variant?: MandateVariant;
  /** Called when the operator clicks an edit CTA. Receives a seeded prompt. */
  onEdit?: (prompt: string) => void;
  /** ADR-266 D8: pre-fetched data path. When provided, the card does not
   *  self-fetch. Pass {data, lastRevision, rawContent} together. */
  data?: MandateData;
  /** ADR-266 D7: revision metadata for the "Updated X by Y" footnote. */
  lastRevision?: WorkspaceRevisionSummary | null;
  /** Raw file content — required when `data` is provided so the
   *  "View full" expand can show the source without a second fetch. */
  rawContent?: string | null;
  /** ADR-419: the mandate file to read on self-fetch. Post ADR-414 D6 the
   *  mandate is a per-agent concept — when a program is hired the caller passes
   *  `/workspace/agents/{slug}/MANDATE.md`; a bare workspace reads the
   *  steward-era root (empty — the workspace has no mandate of its own).
   *  Defaults to the workspace-root path so existing callers are unchanged. */
  path?: string;
  className?: string;
}

const DEFAULT_MANDATE_PATH = '/workspace/constitution/MANDATE.md';

const EDIT_PROMPT = "I want to revise my mandate. Show me the current Primary Action declaration and help me sharpen it — success criteria and boundary conditions too.";
const SETUP_PROMPT = "Help me author my mandate — the Primary Action I'm running, my success criteria, and the boundary conditions I want to enforce.";

/** A Primary Action that runs over one sentence triggers the schema-absent
 *  fallback. The schema (ADR-266 D3) is "one declarative sentence" — when
 *  the source goes longer, we degrade rather than dump. */
function isSchemaMet(data: MandateData | null | undefined): boolean {
  if (!data || data.isEmpty || !data.primaryAction) return false;
  const cleaned = cleanProse(data.primaryAction);
  const first = firstSentence(cleaned);
  // Tolerance: the extracted prose is treated as schema-met if the first
  // sentence accounts for ≥80% of the cleaned content. This accommodates
  // the occasional trailing parenthetical without forcing the fallback.
  return first.length / Math.max(cleaned.length, 1) >= 0.8;
}

export function MandateCard({
  variant = 'full',
  onEdit,
  data: dataProp,
  lastRevision: lastRevisionProp,
  rawContent: rawContentProp,
  path = DEFAULT_MANDATE_PATH,
  className,
}: MandateCardProps) {
  const [data, setData] = useState<MandateData | null>(dataProp ?? null);
  const [rawContent, setRawContent] = useState<string | null>(rawContentProp ?? null);
  const [loading, setLoading] = useState(dataProp === undefined);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    // Pre-fetched path: parent supplied data — skip self-fetch.
    if (dataProp !== undefined) {
      setData(dataProp);
      setRawContent(rawContentProp ?? null);
      setLoading(false);
      return;
    }
    // Self-fetch fallback (e.g. /agents reuse surface).
    let cancelled = false;
    void (async () => {
      try {
        const file = await api.workspace.getFile(path);
        if (!cancelled) {
          setRawContent(file.content ?? '');
          setData(parse(file.content ?? ''));
        }
      } catch {
        if (!cancelled) {
          setRawContent('');
          setData({ primaryAction: null, successCriteria: [], boundaryCount: 0, isEmpty: true });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [dataProp, rawContentProp, path]);

  const schemaMet = useMemo(() => isSchemaMet(data), [data]);
  const cleanedPrimary = useMemo(
    () => (data?.primaryAction ? cleanProse(data.primaryAction) : ''),
    [data?.primaryAction],
  );
  const headline = useMemo(
    () => (schemaMet ? cleanedPrimary : firstSentence(cleanedPrimary)),
    [schemaMet, cleanedPrimary],
  );

  if (variant === 'headline') {
    if (loading) return <span className="text-xs text-muted-foreground/40">Loading…</span>;
    return (
      <p className={cn('text-sm truncate', className)}>
        {headline || <span className="text-muted-foreground/50 italic">Mandate not set</span>}
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
          <p className="text-sm leading-snug line-clamp-2">{headline}</p>
        )}
      </div>
    );
  }

  // full
  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold">Mandate</p>
          <p className="text-xs text-muted-foreground mt-0.5">What this workspace is running toward.</p>
        </div>
        <RevisionFootnote revision={lastRevisionProp ?? null} className="shrink-0 pt-1" />
      </div>

      {loading ? (
        <div className="h-10 rounded-md bg-muted/30 animate-pulse" />
      ) : data?.isEmpty ? (
        <div className="rounded-lg border border-dashed border-border/60 px-4 py-4 text-center space-y-2">
          {/* ADR-419: altitude-honest empty state. A workspace has no mandate of
              its own — a mandate is a hired agent's declared intent. */}
          <p className="text-sm text-muted-foreground">No mandate yet.</p>
          <p className="text-xs text-muted-foreground/60">
            A mandate is the goal a hired agent runs toward — its declared intent, success criteria, and guardrails. The workspace itself holds files and members, not a mandate; hire an agent to give it one.
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
          {/* Primary Action — callout treatment */}
          <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
            <p className="text-[10px] font-medium text-primary/80 uppercase tracking-wide mb-1">Primary Action</p>
            <p className="text-sm leading-relaxed">{headline}</p>
            {!schemaMet && (
              <p className="text-[11px] text-muted-foreground/70 mt-2 italic">
                Mandate is set but not in canonical structure — refine in chat to sharpen the Primary Action to one sentence.
              </p>
            )}
          </div>

          {/* Success criteria — top 3, with rest expandable */}
          {(data?.successCriteria.length ?? 0) > 0 && (
            <div className="space-y-1">
              <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Success criteria</p>
              <ul className="space-y-1">
                {data!.successCriteria.slice(0, 3).map((c, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className="mt-1.5 h-1 w-1 rounded-full bg-muted-foreground/40 shrink-0" />
                    <span>{cleanProse(c)}</span>
                  </li>
                ))}
              </ul>
              {data!.successCriteria.length > 3 && (
                <p className="text-[11px] text-muted-foreground/50 pl-3">
                  · and {data!.successCriteria.length - 3} more
                </p>
              )}
            </div>
          )}

          {(data?.boundaryCount ?? 0) > 0 && (
            <p className="text-[11px] text-muted-foreground/60">
              {data!.boundaryCount} boundary condition{data!.boundaryCount !== 1 ? 's' : ''} declared
            </p>
          )}

          <div className="flex items-center justify-between gap-3 pt-1">
            {onEdit && (
              <button type="button" onClick={() => onEdit(EDIT_PROMPT)}
                className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors">
                Refine in chat <ArrowRight className="w-3 h-3" />
              </button>
            )}
            {rawContent && (
              <button type="button" onClick={() => setExpanded(e => !e)}
                className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
                {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                {expanded ? 'Hide full mandate' : 'View full mandate'}
              </button>
            )}
          </div>

          {expanded && rawContent && (
            <div className="rounded-md border border-border/40 bg-muted/10 px-3 py-2.5 max-h-96 overflow-y-auto">
              <pre className="text-[11px] text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed">
                {rawContent}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
