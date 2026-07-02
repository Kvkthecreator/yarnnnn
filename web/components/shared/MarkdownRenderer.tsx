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
import { SurfaceLink } from '@/components/shell/SurfaceLink';
import { cn } from '@/lib/utils';

interface MarkdownRendererProps {
  content: string;
  className?: string;
  /** Compact mode: tighter spacing for chat bubbles */
  compact?: boolean;
  /** ADR-398 D3: render substrate paths + proposal ids in the text as
   *  SurfaceLinks (OS-owned linkification — the model never authors URLs).
   *  Opt-in: chat bubbles only, never file-viewer content. */
  linkifySubstrate?: boolean;
}

// ── ADR-398 D3: OS-owned substrate linkification ──────────────────────────
// A bare substrate path in chat prose becomes an internal link the `a`
// override below routes through SurfaceLink → Files at that path. Code
// spans/fences are left untouched (a path inside backticks is quoted
// substrate, and rewriting inside code would corrupt it).
const SUBSTRATE_PATH_RE =
  /(^|[\s(])((?:\/workspace\/)?(?:operation|constitution|persona|governance|contract|system|inbound|uploads)\/[A-Za-z0-9_\-./]*[A-Za-z0-9_\-/])/g;
const PROPOSAL_ID_RE = /proposal_id=([0-9a-f]{6,36})(\.{0,3})/g;
const YARNNN_FILES_PREFIX = '#yarnnn-files:';
const YARNNN_QUEUE_PREFIX = '#yarnnn-queue:';

function linkifySegment(text: string): string {
  let out = text.replace(SUBSTRATE_PATH_RE, (_m, lead: string, path: string) => {
    const abs = path.startsWith('/workspace/') ? path : `/workspace/${path}`;
    return `${lead}[${path}](${YARNNN_FILES_PREFIX}${encodeURIComponent(abs)})`;
  });
  out = out.replace(PROPOSAL_ID_RE, (_m, id: string) =>
    `[proposal ${id.slice(0, 8)}](${YARNNN_QUEUE_PREFIX}${id})`
  );
  return out;
}

/** Apply linkification outside code spans/fences only. */
function linkifySubstrateRefs(content: string): string {
  // Split on fenced blocks first, then inline code spans within prose parts.
  return content
    .split(/(```[\s\S]*?```)/g)
    .map((part) =>
      part.startsWith('```')
        ? part
        : part
            .split(/(`[^`\n]*`)/g)
            .map((seg) => (seg.startsWith('`') ? seg : linkifySegment(seg)))
            .join('')
    )
    .join('');
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

export function MarkdownRenderer({ content, className, compact, linkifySubstrate }: MarkdownRendererProps) {
  const rendered = linkifySubstrate ? linkifySubstrateRefs(content) : content;
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
          a({ href, children, ...props }) {
            // ADR-398 D3: internal substrate links route through SurfaceLink
            // (window-manager navigation, ADR-297) — never a hard navigation.
            if (href?.startsWith(YARNNN_FILES_PREFIX)) {
              const path = decodeURIComponent(href.slice(YARNNN_FILES_PREFIX.length));
              return (
                <SurfaceLink to="files" params={{ path }} className="underline decoration-dotted underline-offset-2">
                  {children}
                </SurfaceLink>
              );
            }
            if (href?.startsWith(YARNNN_QUEUE_PREFIX)) {
              return (
                <SurfaceLink to="notifications" className="underline decoration-dotted underline-offset-2">
                  {children}
                </SurfaceLink>
              );
            }
            return (
              <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
            );
          },
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
        {rendered}
      </ReactMarkdown>
    </div>
  );
}
