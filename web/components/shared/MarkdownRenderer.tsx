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
  /**
   * ADR-572 D1 — who owns the type SCALE.
   *
   * Default `'chat'` keeps this component's historical face (`prose-sm` plus
   * `text-xs` tables), which every existing mount was written against.
   *
   * `'inherit'` emits NO scale class at all, handing the decision to the
   * caller's `className`. Text's reading face needs this: passing
   * `prose-base` alongside `prose-sm` puts two font-size rules on one element,
   * and CSS resolves that by STYLESHEET ORDER, not by the order of names in
   * the class attribute. Measured 2026-08-16 — `prose-base` happened to be
   * emitted later and won, but nothing pinned it there, so a document could
   * silently drop to chat size the next time an unrelated file changed which
   * utilities Tailwind emits. An override that works by luck is a defect that
   * has not fired yet.
   */
  scale?: 'chat' | 'inherit';
}

// ── ADR-398 D3: OS-owned substrate linkification ──────────────────────────
// A bare substrate path in chat prose becomes an internal link the `a`
// override below routes through SurfaceLink → Files at that path. Code
// spans/fences are left untouched (a path inside backticks is quoted
// substrate, and rewriting inside code would corrupt it).
//
// TWO detection rules, because the namespace has two shapes (ADR-570 D6):
// the kernel roots are enumerable (the allowlist below), but MEANING-NAMED
// folders are unenumerable by design (DP33 — `marketing/video/…` is a path
// someone chose, not a root we know). A file under a meaning folder is
// recognized by its EXTENSION instead: a slash-bearing token ending in a
// substrate extension. Both rules stay OS-owned — the model never authors
// URLs; a miss lands on Files' honest "isn't here" state.
const SUBSTRATE_PATH_RE =
  /(^|[\s(])((?:\/workspace\/)?(?:operation|constitution|persona|governance|contract|system|inbound|uploads)\/[A-Za-z0-9_\-./]*[A-Za-z0-9_\-/])/g;
const SUBSTRATE_FILE_RE =
  /(^|[\s(])((?:\/workspace\/)?[A-Za-z0-9_\-][A-Za-z0-9_\-./]*\/[A-Za-z0-9_\-.]+\.(?:md|markdown|txt|csv|json|ya?ml|html|pdf|png|jpe?g|svg|webp))\b/g;
const PROPOSAL_ID_RE = /proposal_id=([0-9a-f]{6,36})(\.{0,3})/g;
const YARNNN_FILES_PREFIX = '#yarnnn-files:';
const YARNNN_QUEUE_PREFIX = '#yarnnn-queue:';

function linkifySegment(text: string): string {
  const toLink = (_m: string, lead: string, path: string) => {
    const abs = path.startsWith('/workspace/') ? path : `/workspace/${path}`;
    return `${lead}[${path}](${YARNNN_FILES_PREFIX}${encodeURIComponent(abs)})`;
  };
  // Root rule first; the file rule then only sees what the roots didn't
  // claim (a linkified path sits behind `[`, which neither lead accepts).
  let out = text.replace(SUBSTRATE_PATH_RE, toLink);
  out = out.replace(SUBSTRATE_FILE_RE, toLink);
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
/**
 * An `<img>` whose `src` may be a workspace path (ADR-572 D17).
 *
 * Markdown's own image syntax with a substrate path — `![alt](notes/x.png)` —
 * is the only image form that keeps the file portable: the path is text a
 * connector reads, rewrites and round-trips. What it is NOT is fetchable, so
 * the viewer resolves it here.
 *
 * The URL is minted, never stored: `GET /workspace/file` returns a CAS serving
 * URL with a 1-hour TTL (ADR-427 D4), so baking one into the document would
 * write a capability that expires — a file that renders today and 404s
 * tomorrow. Resolution belongs to the reader, per read.
 */
function MarkdownImage({ src, alt, ...props }: { src: string; alt: string }) {
  const [resolved, setResolved] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  // Anything with a scheme (https:, data:, blob:) is already fetchable.
  const isExternal = /^[a-z][a-z0-9+.-]*:/i.test(src) || src.startsWith('//');

  useEffect(() => {
    if (isExternal || !src) return;
    let cancelled = false;
    setFailed(false);
    const path = src.startsWith('/workspace/') ? src : `/workspace/${src.replace(/^\/+/, '')}`;
    import('@/lib/api/client')
      .then(({ api }) => api.workspace.getFile(path))
      .then(async (f) => {
        const url = (f as { content_url?: string | null }).content_url;
        if (!url) throw new Error('no content_url');
        // An already-minted CAS URL is usable as-is; the legacy
        // `?storage_path=` shape needs the authenticated exchange.
        if (!/[?&]storage_path=/.test(url)) return url;
        const { api } = await import('@/lib/api/client');
        return (await api.documents.blobUrl(url)).url;
      })
      .then((url) => { if (!cancelled) setResolved(url); })
      .catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; };
  }, [src, isExternal]);

  if (isExternal) return <img src={src} alt={alt} {...props} />;
  if (failed) {
    // Name the path rather than showing a broken glyph — the member can see
    // WHICH file is missing, and the source is still valid markdown.
    return (
      <span className="inline-block rounded border border-dashed border-border px-2 py-1 text-xs text-muted-foreground">
        Image not found: <span className="font-mono">{src}</span>
      </span>
    );
  }
  if (!resolved) {
    return <span className="inline-block h-4 w-24 animate-pulse rounded bg-muted align-middle" aria-hidden />;
  }
  return <img src={resolved} alt={alt} {...props} />;
}

function MermaidBlock({ code }: { code: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string | null>(null);

  // DEBOUNCED + KEEP-LAST-GOOD (2026-08-18). This block mounts the moment a
  // ```mermaid fence OPENS in a streaming reply, so `code` grows delta by
  // delta and almost every intermediate form fails to parse — rendered
  // naively, the block flickered placeholder → source-as-error → placeholder
  // until the fence closed. Two rules calm it: attempt a render only after
  // the source has been stable for a beat, and never discard a rendered
  // diagram because a later (partial) form failed — the last good SVG stands
  // until a newer form succeeds. Until the FIRST success, the source itself
  // is the one quiet face (it is what the file honestly contains).
  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
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
      } catch {
        /* invalid (often just incomplete) source — keep the current face */
      }
    }, 250);
    return () => { cancelled = true; clearTimeout(t); };
  }, [code]);

  if (!svg) {
    return (
      <pre className="overflow-auto rounded-lg border border-border bg-muted/20 p-4 text-sm whitespace-pre-wrap text-muted-foreground">
        {code}
      </pre>
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

export function MarkdownRenderer({
  content,
  className,
  compact,
  linkifySubstrate,
  scale = 'chat',
}: MarkdownRendererProps) {
  const rendered = linkifySubstrate ? linkifySubstrateRefs(content) : content;
  const chatScale = scale === 'chat';
  return (
    <div
      className={cn(
        'prose dark:prose-invert max-w-none',
        // The scale classes are WITHHELD under `scale="inherit"` so the caller
        // owns font-size outright — see the prop's docstring for why sharing
        // the decision across two classes is unsafe.
        chatScale && (compact ? 'prose-sm prose-p:my-0.5' : 'prose-sm'),
        compact && !chatScale && 'prose-p:my-0.5',
        // Table styling
        'prose-table:border-collapse prose-table:w-full',
        'prose-th:border prose-th:border-border prose-th:px-3 prose-th:py-1.5 prose-th:bg-muted/50 prose-th:text-left prose-th:font-medium',
        chatScale && 'prose-th:text-xs',
        'prose-td:border prose-td:border-border prose-td:px-3 prose-td:py-1.5',
        chatScale && 'prose-td:text-xs',
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          // ADR-572 D17 — an image whose `src` is a WORKSPACE PATH.
          //
          // `![alt](notes/diagram.png)` is native markdown, and the bytes are a
          // real substrate file — but a workspace path is not a URL a browser
          // can fetch, and the CAS serving URL is minted per request with a
          // 1-hour TTL (ADR-427 D4), so it cannot be baked into the file
          // either. Resolving here keeps the SOURCE portable: the `.md` holds
          // a path a connector can read and rewrite, and the viewer mints its
          // own access. An absolute URL is left alone.
          img({ src, alt, ...props }) {
            return <MarkdownImage src={typeof src === 'string' ? src : ''} alt={alt ?? ''} {...props} />;
          },
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
