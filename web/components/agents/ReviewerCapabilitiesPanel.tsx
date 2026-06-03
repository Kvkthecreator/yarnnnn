'use client';

/**
 * ReviewerCapabilitiesPanel — operator-facing view of /workspace/specs/.
 *
 * Authored 2026-05-14. Surfaces the Reviewer's capability library as
 * first-class cockpit content. Each spec is a quality contract: schema,
 * sections, anti-patterns — read by the Reviewer when producing recurring
 * outputs. Operator-facing analog of Claude Code's skills.md.
 *
 * Single operator question this surface answers:
 *   "What kinds of outputs can my Reviewer produce, and what does each
 *    one promise?"
 *
 * One card per spec file under /workspace/specs/*.md. Each card carries:
 *   - Title (extracted from the spec's # heading)
 *   - Short description (extracted from the spec's intro prose)
 *   - Sections (## headings, shown as chips)
 *   - "Used by" — list of recurrence slugs whose prompt text references
 *     this spec (computed server-side by parsing _recurrences.yaml)
 *   - Last-updated relative timestamp
 *   - Deep-link to source file on /files for the full read
 *   - "Edit in chat" affordance routing through ADR-235 D1
 *
 * Read-only by design. Substrate edits go via chat per ADR-235 D1 +
 * ADR-245. The spec library is operator-owned; chat is the canonical
 * authoring path.
 *
 * Empty state when /workspace/specs/ is empty (newly-activated workspace
 * with no specs forked yet) — points the operator at chat to start
 * authoring.
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, BookOpen, FileText, Link2 } from 'lucide-react';
import { api } from '@/lib/api/client';
import { useNarrative } from '@/contexts/NarrativeContext';

interface SpecRow {
  slug: string;
  path: string;
  title: string;
  description: string | null;
  sections: string[];
  used_by: string[];
  updated_at: string | null;
  size_bytes: number;
}

interface CapabilitiesData {
  specs: SpecRow[];
}

function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const diffMs = Date.now() - new Date(iso).getTime();
  const m = Math.floor(Math.abs(diffMs) / 60_000);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);
  if (m < 60) return `${m}m ago`;
  if (h < 24) return `${h}h ago`;
  return `${d}d ago`;
}

export function ReviewerCapabilitiesPanel() {
  const { sendMessage } = useNarrative();
  const [data, setData] = useState<CapabilitiesData | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.agents.reviewerCapabilities()
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => { if (!cancelled) setData({ specs: [] }); });
    return () => { cancelled = true; };
  }, []);

  if (data === null) return null;

  const editPromptFor = (spec: SpecRow) =>
    `I want to evolve the capability spec at ${spec.path} (${spec.title}). Walk me through the current declaration and help me sharpen it.`;

  const newSpecPrompt =
    'I want to author a new capability spec for my Reviewer — a recurring output it can produce (schema, sections, quality bar). Walk me through declaring it.';

  // Empty state
  if (data.specs.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-muted/10 px-6 py-8">
        <BookOpen className="h-6 w-6 text-muted-foreground/30 mx-auto mb-3" />
        <p className="text-sm font-medium text-center text-foreground mb-1.5">
          No capability specs declared yet
        </p>
        <p className="text-xs text-muted-foreground/70 text-center max-w-md mx-auto mb-4">
          Capability specs live at <code className="text-[11px] bg-muted px-1 rounded">/workspace/specs/*.md</code>.
          Each spec is a quality contract describing one kind of output your Reviewer
          can produce — schema, sections, anti-patterns. The Reviewer reads them when
          producing recurring work.
        </p>
        <div className="flex justify-center">
          <button
            type="button"
            onClick={() => sendMessage(newSpecPrompt)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border bg-background text-xs hover:bg-muted transition-colors"
          >
            Author a capability via chat <ArrowRight className="h-3 w-3" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header strip */}
      <div className="flex items-center gap-2">
        <BookOpen className="h-3.5 w-3.5 text-muted-foreground" />
        <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
          Capability library
        </h3>
        <span className="ml-auto text-[10px] text-muted-foreground/60">
          {data.specs.length} spec{data.specs.length === 1 ? '' : 's'}
        </span>
      </div>

      {/* Spec cards */}
      <ul className="space-y-3">
        {data.specs.map((s) => (
          <li
            key={s.slug}
            className="rounded-lg border border-border bg-card p-4 hover:border-border/80 transition-colors"
          >
            <div className="flex items-start justify-between gap-3 mb-1.5">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-foreground truncate">
                  {s.title}
                </h4>
                <code className="text-[10px] text-muted-foreground/50 font-mono">
                  {s.slug}.md
                </code>
              </div>
              <span className="shrink-0 text-[10px] text-muted-foreground/50 tabular-nums">
                {relativeTime(s.updated_at)}
              </span>
            </div>

            {s.description && (
              <p className="text-xs text-muted-foreground mt-1 mb-3 line-clamp-3">
                {s.description}
              </p>
            )}

            {s.sections.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-3">
                {s.sections.map((section) => (
                  <span
                    key={section}
                    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-muted/40 text-[10px] text-muted-foreground"
                  >
                    {section}
                  </span>
                ))}
              </div>
            )}

            {s.used_by.length > 0 && (
              <div className="flex items-start gap-1.5 mb-3 text-[11px] text-muted-foreground/70">
                <Link2 className="h-3 w-3 mt-0.5 shrink-0" />
                <div className="flex-1">
                  <span className="text-muted-foreground/50 mr-1">Used by:</span>
                  {s.used_by.map((rslug, idx) => (
                    <span key={rslug}>
                      {idx > 0 && <span className="text-muted-foreground/30 mx-1">·</span>}
                      <Link
                        href={`/recurrence?task=${encodeURIComponent(rslug)}`}
                        className="font-mono hover:text-foreground hover:underline underline-offset-4"
                      >
                        {rslug}
                      </Link>
                    </span>
                  ))}
                </div>
              </div>
            )}

            {s.used_by.length === 0 && (
              <p className="text-[11px] text-muted-foreground/50 mb-3 italic">
                Not referenced by any current recurrence — capability available
                but not scheduled.
              </p>
            )}

            <div className="flex items-center gap-3 pt-1 border-t border-border/40">
              <Link
                href={`/files?path=${encodeURIComponent(s.path)}`}
                className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/60 hover:text-foreground hover:underline underline-offset-4 transition-colors"
              >
                <FileText className="h-3 w-3" />
                View source
              </Link>
              <span className="text-muted-foreground/30">·</span>
              <button
                type="button"
                onClick={() => sendMessage(editPromptFor(s))}
                className="inline-flex items-center gap-1 text-[11px] text-primary/70 hover:text-primary hover:underline underline-offset-4 transition-colors"
              >
                Edit in chat <ArrowRight className="h-3 w-3" />
              </button>
              <span className="ml-auto text-[10px] text-muted-foreground/40">
                {(s.size_bytes / 1024).toFixed(1)}KB
              </span>
            </div>
          </li>
        ))}
      </ul>

      {/* New-spec affordance */}
      <div className="pt-1">
        <button
          type="button"
          onClick={() => sendMessage(newSpecPrompt)}
          className="inline-flex items-center gap-1 text-[11px] text-muted-foreground/60 hover:text-foreground hover:underline underline-offset-4 transition-colors"
        >
          Author a new capability via chat <ArrowRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}
