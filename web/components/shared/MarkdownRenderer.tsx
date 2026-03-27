'use client';

/**
 * Shared Markdown Renderer — GFM-enabled, used across all surfaces.
 *
 * Supports: tables, strikethrough, autolinks, task lists (via remark-gfm).
 * Wraps ReactMarkdown with consistent styling and plugins.
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  /** Compact mode: tighter spacing for chat bubbles */
  compact?: boolean;
}

export function MarkdownRenderer({ content, className, compact }: MarkdownRendererProps) {
  return (
    <div
      className={cn(
        'prose dark:prose-invert max-w-none',
        compact ? 'prose-sm prose-p:my-0.5' : 'prose-sm',
        // Table styling
        'prose-table:border-collapse prose-table:w-full',
        'prose-th:border prose-th:border-border prose-th:px-3 prose-th:py-1.5 prose-th:bg-muted/50 prose-th:text-left prose-th:text-xs prose-th:font-medium',
        'prose-td:border prose-td:border-border prose-td:px-3 prose-td:py-1.5 prose-td:text-xs',
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
