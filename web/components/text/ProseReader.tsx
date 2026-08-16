'use client';

/**
 * ProseReader — a STATIC render of a markdown document (ADR-572).
 *
 * ## What this is for, after D8
 *
 * It was the canvas's Read mode until ADR-572 D8 collapsed Text to one
 * CodeMirror-grade canvas. It survives for the two places that need a rendered
 * document with **no editor attached**:
 *
 *   - the landing thumbnail (`TextSurface::ProseThumb`), and
 *   - Print/PDF (`printProse`), which needs an HTML string.
 *
 * It is deliberately NOT mounted beside the canvas — that would be the dual
 * implementation D8 removed.
 *
 * ## Why this exists
 *
 * `MarkdownRenderer` is the workspace's ONE markdown pipeline (react-markdown
 * + remark-gfm + rehype-raw + mermaid) and it stays that — this file adds no
 * second parser. What it adds is a SKIN: the renderer's resting face is
 * `prose-sm`, tuned for chat bubbles and file previews, and a 1,000-word brief
 * set in it reads as a transcript, not a document. Docs' documents get their
 * typography from the artifact's own HTML plus a design system; a `.md` has
 * neither, so the reading face is the app's to define (ADR-571's handoff named
 * exactly this gap).
 *
 * ## Why a VIEW is not a block model
 *
 * ADR-456 D1 holds Text to textarea/CodeMirror grade: never block-grade, no
 * block ids, no `data-*` annotations, no Studio machinery. Rendering is not a
 * violation of that and the distinction is load-bearing: **nothing here ever
 * writes.** The source string goes in, HTML comes out, and the file on disk is
 * untouched — byte-for-byte the same `.md` a connector reads and writes back.
 * There is no node→offset map, no editable region, no id minted anywhere. Take
 * this component away and the document is unchanged; that is the test a view
 * passes and a block model fails.
 *
 * ## The scale rule
 *
 * `zoom` is a VIEW control, exactly as it is on Docs (`StudioSurface` clamps
 * 0.25–2). It rides CSS `zoom` on the wrapper rather than `transform: scale`
 * so the reading column re-flows at its scaled measure instead of overflowing
 * a fixed box — a scaled document that needs horizontal scrolling to read one
 * line is not a zoom, it is a crop.
 */

import { MarkdownRenderer } from '@/components/shared/MarkdownRenderer';
import { cn } from '@/lib/utils';

/**
 * The document reading skin.
 *
 * Serif headings + serif body at a real reading size, a measure near 68ch, and
 * table/quote/rule treatments that read as a document rather than as chat
 * output. Every rule is a `prose-*` variant on the shared renderer's own
 * Tailwind-typography root — this overrides the face, never the pipeline.
 *
 * Kept as a module constant (not inlined) so the gate can assert the skin is
 * REACHED, and so the thumbnail and the print sheet wear the same face as the
 * canvas.
 */
export const PROSE_READING_SKIN = cn(
  // Base: serif, document-sized, generous leading. `prose-base` replaces the
  // renderer's `prose-sm` default; `max-w-none` lets the parent own the measure.
  'prose-base max-w-none font-serif text-foreground',
  '[&_p]:leading-[1.75] [&_li]:leading-[1.75]',
  // Headings — the single loudest signal that this is a document. Serif,
  // tight leading, real hierarchy, generous space above and little below (a
  // heading belongs to what FOLLOWS it).
  'prose-headings:font-serif prose-headings:font-semibold prose-headings:tracking-[-0.01em]',
  'prose-h1:text-[2rem] prose-h1:leading-[1.2] prose-h1:mt-0 prose-h1:mb-4',
  'prose-h2:text-[1.5rem] prose-h2:leading-[1.3] prose-h2:mt-10 prose-h2:mb-3',
  'prose-h3:text-[1.2rem] prose-h3:leading-[1.35] prose-h3:mt-8 prose-h3:mb-2',
  'prose-h4:text-[1.05rem] prose-h4:mt-6 prose-h4:mb-2',
  // Body rhythm.
  'prose-p:my-4 prose-ul:my-4 prose-ol:my-4 prose-li:my-1',
  // GFM task lists. `remark-gfm` emits a real `<input type="checkbox">` inside
  // the `<li>`, and Tailwind's prose leaves it sitting on the list marker. Drop
  // the marker, pull the box into the gutter, and align it to the first line —
  // the treatment Docs gets from its kernel `☐` pseudo-element rule.
  '[&_li:has(>input[type=checkbox])]:list-none',
  '[&_li>input[type=checkbox]]:mr-2 [&_li>input[type=checkbox]]:-ml-5',
  '[&_li>input[type=checkbox]]:align-middle [&_li>input[type=checkbox]]:accent-foreground',
  // Quote — a rule and a lift, not a grey box.
  'prose-blockquote:border-l-2 prose-blockquote:border-foreground/25',
  'prose-blockquote:pl-4 prose-blockquote:not-italic prose-blockquote:text-foreground/75',
  // Thematic break — `---` is a section boundary in prose; give it air.
  'prose-hr:my-10 prose-hr:border-border',
  // Tables read at body size in a document. Under `scale="inherit"` the
  // renderer withholds its `text-xs` chat-table rules entirely, so this SETS
  // the size rather than out-specifying a competing rule.
  '[&_th]:text-[0.9rem] [&_td]:text-[0.9rem] [&_thead_th]:font-semibold',
  // Code stays MONO inside a serif document — it is the one thing whose glyph
  // width carries meaning.
  'prose-code:font-mono prose-code:text-[0.85em] prose-code:before:content-none prose-code:after:content-none',
  'prose-pre:font-mono prose-pre:text-[0.8rem] prose-pre:bg-muted/40 prose-pre:text-foreground',
  // Links — underlined in a document, never a bare colour.
  'prose-a:underline prose-a:underline-offset-2 prose-a:decoration-foreground/30',
  'prose-strong:font-semibold',
);

export function ProseReader({
  text,
  zoom = 1,
  className,
}: {
  text: string;
  /** View-only scale (Docs' 0.25–2 clamp). Never touches the file. */
  zoom?: number;
  className?: string;
}) {
  if (!text.trim()) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-muted-foreground">
        This document is empty — switch to Write and start typing.
      </div>
    );
  }
  return (
    // `zoom` (not `transform`) so the column re-flows at its scaled measure.
    <div style={zoom === 1 ? undefined : { zoom }} className={className}>
      {/* `scale="inherit"` — the skin owns font-size outright. Passing
          `prose-base` while the renderer also emits `prose-sm` would leave the
          winner to stylesheet order (ADR-572 D1). */}
      <MarkdownRenderer content={text} scale="inherit" className={PROSE_READING_SKIN} />
    </div>
  );
}
