'use client';

/**
 * InferenceContentView — Renders inferred content (IDENTITY.md, BRAND.md)
 * with source provenance and gap markers.
 *
 * ADR-162 Sub-phase D + ADR-163 + ADR-209 Phase 4: Parses the
 * `<!-- inference-meta: ... -->` comment embedded in inference output by
 * `_append_inference_meta()` on the backend. The parsed body (without the
 * comment) is rendered via the normal markdown renderer. The parsed meta
 * drives two inline signals:
 *
 *   1. Source caption — "Last updated from: pitch-deck.pdf" above the body
 *   2. Gap banner — "Missing: company name" below the body, with an action
 *      to drop a pre-filled message into TP chat
 *
 * ADR-209 Phase 4 removed the "Inferred Nh ago" timestamp from this view.
 * Timestamp authority now lives in the Authored Substrate revision chain —
 * callers that want age alongside this view mount the RevisionHistoryPanel
 * adjacent (see BrandSection in MemorySection.tsx). Duplicating timestamp
 * here would conflict with substrate-as-source-of-truth per FOUNDATIONS
 * v6.1 Axiom 1.
 *
 * If no meta comment is present (e.g., a manually-edited file), the component
 * falls back to just rendering the body. No captions, no banners.
 */

import Link from 'next/link';
import { Info, AlertCircle, MessageSquare } from 'lucide-react';
import { cn } from '@/lib/utils';
import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import {
  parseInferenceMeta,
  formatSourceCaption,
  getPrimaryGap,
} from '@/lib/inference-meta';
import { CHAT_ROUTE } from '@/lib/routes';

interface InferenceContentViewProps {
  content: string | null;
  target: 'identity' | 'brand';
  className?: string;
}

export function InferenceContentView({ content, target, className }: InferenceContentViewProps) {
  const { body, meta } = parseInferenceMeta(content);
  const sourceCaption = formatSourceCaption(meta);
  const primaryGap = getPrimaryGap(meta);

  const gapChatPrompt = primaryGap
    ? encodeURIComponent(
        `I want to ${target === 'identity' ? 'update my identity' : 'update my brand'} to fill in ${primaryGap.field.replace(/_/g, ' ')}.`
      )
    : null;

  if (!body) {
    return (
      <div className={cn('text-sm text-muted-foreground italic', className)}>
        No content yet.
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      {/* Source caption (no longer carries "inferred ago" — revision chain is authoritative). */}
      {sourceCaption && (
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground/60">
          <Info className="w-3 h-3" />
          <span>{sourceCaption}</span>
        </div>
      )}

      {/* Rendered markdown body */}
      <div className="border border-border rounded-lg p-4">
        <div className="prose prose-sm max-w-none dark:prose-invert">
          <MarkdownRenderer content={body} />
        </div>
      </div>

      {/* Gap banner */}
      {primaryGap && (
        <div className="border border-amber-500/30 bg-amber-500/5 rounded-lg p-3 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="flex-1 text-xs">
            <div className="font-medium text-amber-700 mb-0.5">
              Missing: {primaryGap.field.replace(/_/g, ' ')}
            </div>
            <div className="text-amber-700/80 mb-2">{primaryGap.suggested_question}</div>
            <Link
              href={`${CHAT_ROUTE}?prompt=${gapChatPrompt}`}
              className="inline-flex items-center gap-1 text-amber-700 font-medium hover:underline"
            >
              <MessageSquare className="w-3 h-3" />
              Chat to fill this in
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
