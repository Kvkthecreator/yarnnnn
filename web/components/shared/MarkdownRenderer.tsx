'use client';

/**
 * Shared Markdown Renderer — GFM + inline HTML + Mermaid diagrams.
 *
 * Supports: tables, strikethrough, autolinks, task lists (via remark-gfm),
 * inline HTML (via rehype-raw), and mermaid code blocks (client-side render).
 */

import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  /** Compact mode: tighter spacing for chat bubbles */
  compact?: boolean;
}

/** Renders mermaid code blocks as SVG diagrams */
function MermaidBlock({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function render() {
      try {
        const mermaid = (await import('mermaid')).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: 'neutral',
          securityLevel: 'loose',
        });
        const id = `mermaid-${Math.random().toString(36).slice(2, 9)}`;
        const { svg: rendered } = await mermaid.render(id, code);
        if (!cancelled) setSvg(rendered);
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Mermaid render failed');
      }
    }

    render();
    return () => { cancelled = true; };
  }, [code]);

  if (error) {
    return (
      <pre className="overflow-auto rounded-lg border border-border bg-muted/20 p-4 text-sm whitespace-pre-wrap text-muted-foreground">
        {code}
      </pre>
    );
  }

  if (!svg) {
    return (
      <div className="flex items-center justify-center py-6 text-sm text-muted-foreground/50">
        Rendering diagram...
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="my-4 flex justify-center [&_svg]:max-w-full"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
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
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          code({ className: codeClassName, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClassName || '');
            const lang = match?.[1];
            const codeStr = String(children).replace(/\n$/, '');

            if (lang === 'mermaid') {
              return <MermaidBlock code={codeStr} />;
            }

            // Inline code (no language class)
            if (!lang) {
              return <code className={codeClassName} {...props}>{children}</code>;
            }

            // Fenced code block (non-mermaid)
            return (
              <code className={codeClassName} {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
